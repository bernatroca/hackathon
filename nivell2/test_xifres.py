"""Contrast amb el verificador real i casos petits amb resultat conegut."""
import csv
from copy import deepcopy
from datetime import date, timedelta

import contextlib
import io
import tempfile
import unittest
from functools import lru_cache
from pathlib import Path

from nivell2.base import Base, Informe, PAQUET, Proposta, Sessio, carrega_oficial
from nivell2.comprova import main
from nivell2.xifres import calcula, compara


@lru_cache(maxsize=1)
def partida():
    base = carrega_oficial()
    return compara(Proposta.de_base(base), base)


def test_abans_igual_despres():
    resultat = partida()
    assert all(r['abans'] == r['despres'] for r in resultat.files)
    a = [{k: v for k, v in r.items() if k != 'horari'}
         for r in resultat.titulacions if r['horari'] == 'abans']
    d = [{k: v for k, v in r.items() if k != 'horari'}
         for r in resultat.titulacions if r['horari'] == 'despres']
    assert a == d
    assert all(r[f'{c}_pct'] == 0 for r in d for c in ('franja', 'aula', 'torn'))


def test_json_oficial():
    resultat = partida()
    x = {r['xifra']: r['despres'] for r in resultat.files}
    assert x['veredicte'] == resultat.despres.json['veredicte'] == 'NO VALIDA'
    for k, v in resultat.despres.objectius.items():
        assert x[k] == v
    for k, v in resultat.despres.json['restriccions'].items():
        assert x[f'incompliments:{k}'] == v['compten']
    assert resultat.despres.compten() == {
        'R1-TORN': 2008, 'R2-FINESTRA': 13, 'R3-AFORAMENT': 43,
        'R3-TIPUS': 54, 'R5-SENSE-AULA': 4541,
    }
    assert x['canvis_torn_sense_regla1'] == 0


def base_petita():
    sessions = {}
    for i in range(3):
        s = Sessio(str(i), '1', 'TE', '81', date(2027, 2, 1) + timedelta(weeks=i),
                   'L', 510, 60, 20, 'A', ('G:1r', 'H:1r'), 'mati', '', frozenset(),
                   activitat='ACT')
        sessions[s.id] = s
    return Base(sessions, {}, list(sessions))


INFORME = Informe({'veredicte': 'NO VALIDA', 'restriccions': {}, 'objectius': {}}, '')


def test_rutina_torn_i_cohorts_compartides():
    b = base_petita()
    p = Proposta.de_base(b)
    p.files['0'].h_ini = '15:00'
    p.files['0'].aula = 'B'
    x, cohorts = calcula(p, b, INFORME)
    assert x['activitats_rutinaries_pct'] == 0
    assert x['excepcions_rutina'] == 1
    assert x['canvis_torn'] == x['canvis_torn_sense_regla1'] == 1
    for r in cohorts:
        assert r['sessions'] == 3
        for c in ('franja', 'aula', 'torn'):
            assert r[c] == 1
            assert abs(r[f'{c}_pct'] - 100 / 3) < 1e-9
    b.sessions['0'].torn = 'tarda'
    assert calcula(p, b, INFORME)[0]['canvis_torn_sense_regla1'] == 0


def test_grup_es_cohort_mes_linia_i_setmana():
    b = base_petita()
    s = deepcopy(b.sessions['0'])
    s.id, s.tipus, s.grup, s.aula = '3', 'PAUL', '811', 'B'
    b.sessions[s.id] = s
    b.ordre.append(s.id)
    x, _ = calcula(Proposta.de_base(b), b, INFORME)
    assert x['aules_grup_setmana_maxim'] == 2
    assert abs(x['aules_grup_setmana_mitjana'] - 4 / 3) < 1e-9


def test_absents_no_falsegen_percentatges():
    b = base_petita()
    p = Proposta.de_base(b)
    del p.files['0']
    x, cohorts = calcula(p, b, INFORME)
    assert x['sessions_no_avaluables'] == 1
    assert all(r['franja_pct'] is None and r['sessions'] == 3 for r in cohorts)


def comprova_cli(tmp_path):
    relax = tmp_path / 'relax.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-TORN,,Prova declarada\n', encoding='utf-8')
    sortida, titulacions = tmp_path / 'x.csv', tmp_path / 't.csv'
    assert main([str(PAQUET / 'proposta_partida.csv'), '--nomes-aules',
                 '--referencia', str(PAQUET / 'proposta_partida.csv'),
                 '--relaxacions', str(relax), '--sortida', str(sortida),
                 '--per-titulacio', str(titulacions)]) == 0
    with sortida.open() as f:
        rows = {r['xifra']: r for r in csv.DictReader(f)}
    assert rows['canvis_franja_vs_referencia']['despres'] == '0'
    assert rows['canvis_aula_vs_referencia']['despres'] == '0'
    assert rows['relaxacio:R1-TORN: Prova declarada']['despres'] == '1'
    assert rows['relaxacions_declarades']['abans'] == '0'
    with titulacions.open() as f:
        assert all(float(r['torn_pct']) == 0 for r in csv.DictReader(f))


def test_cli_csv_referencia_relaxacions_i_nomes_aules():
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()) as out:
        comprova_cli(Path(tmp))
    assert 'Veredicte oficial' in out.getvalue()


def test_assignacions_i_exclusions_com_verificador():
    from horaris.check import _objectius, _col_loca, Informe as InformeIntern
    b = base_petita()
    b.sessions['0'].aula = ''
    b.sessions['1'].aula = 'J/001'
    b.sessions['2'].sense_espai = True
    p = Proposta.de_base(b)
    for a in p.files.values():
        a.aula = 'B'
    x, cohorts = calcula(p, b, INFORME)
    oficial = _objectius(b, _col_loca(b, p.a_files(), InformeIntern()))
    assert oficial['canvis_aula'] == 0
    assert x['aules_assignades'] == 1
    assert all(r['aula'] == r['aula_pct'] == 0 for r in cohorts)
    assert all(r['aules_assignades'] == 1 for r in cohorts)


class TestXifres(unittest.TestCase):
    """Adaptador perquè les mateixes proves funcionin sense dependències."""


for _nom, _func in list(globals().items()):
    if _nom.startswith('test_') and callable(_func):
        setattr(TestXifres, _nom, staticmethod(_func))
        del globals()[_nom]

del _nom, _func

if __name__ == '__main__':
    unittest.main()
