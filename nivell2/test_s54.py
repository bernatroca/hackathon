"""Només dades inventades: integració del grau nou i certificats limitats."""
import copy
import datetime as dt

import pytest

from nivell2.base import Proposta, avalua_rapid
from nivell2.s54 import comprova_proposta, referencia_completa, resol_congelat
from nivell2.test_franges import base_petita, sessio
from horaris.model import Aula, Tancament


def nova(sid='inventada-nova', **kw):
    args = dict(torn='mati', ini=540, alumnes=40, cohorts=('INVENTAT:1r',),
                docents=frozenset({'docent-inventat-nou'}))
    args.update(kw)
    return sessio(sid, **args)


def referencia(base, *noves):
    p = Proposta.de_base(base)
    for s in noves:
        del p.files[s.id]
    return p


def test_colloca_amb_rutina_sense_tocar_referencia():
    first = nova(activitat='inventada-activitat')
    second = nova('inventada-setmana-2', activitat=first.activitat,
                  data=first.data+dt.timedelta(days=7))
    host = sessio('inventada-base', ini=900, aula='0')
    base = base_petita(first, second, host)
    ref = referencia(base, first, second)
    original = copy.deepcopy(ref)
    result, stats = resol_congelat(base, ref, temps_s=5)
    assert stats['estat'] in ('OPTIMAL', 'FEASIBLE')
    assert result.files[host.id] == ref.files[host.id]
    assert result.files[first.id] == result.files[second.id]
    assert (result.files[first.id].dia, result.files[first.id].h_ini) == ('L', '09:00')
    assert stats['sessions_noves_fora_franja'] == 0
    assert not any(comprova_proposta(base, result, ref).values())
    assert avalua_rapid(base, result).veredicte == 'VALIDA'
    assert ref == original and not first.aula


def test_reconstrueix_rutina_si_escenari_no_porta_activitat_id():
    first = nova('inventada-primera', activitat='', codi='inventat-codi')
    second = nova('inventada-segona', activitat='', codi=first.codi,
                  data=first.data+dt.timedelta(days=7))
    other = nova('inventada-altra-classe', activitat='', codi=first.codi,
                 data=first.data+dt.timedelta(days=1), dia='M')
    base = base_petita(first, second, other)
    ref = referencia(base, first, second, other)
    result, stats = resol_congelat(base, ref, temps_s=5)
    assert result is not None
    assert stats['activitats_noves'] == 2
    assert stats['sessions_noves_amb_activitat_id'] == 0
    assert result.files[first.id] == result.files[second.id]
    assert not any(comprova_proposta(base, result, ref).values())


def test_obstacle_es_el_52_i_no_la_partida():
    new = nova(durada=360)
    old = sessio('inventada-vella', torn='mati', ini=540, durada=360,
                 aula='0', docents=new.docents, cohorts=('ALTRE:1r',))
    base = base_petita(new, old)
    ref = referencia(base, new)
    ref.files[old.id].dia = 'M'
    result, _ = resol_congelat(base, ref, temps_s=5)
    assert result is not None
    assert result.files[new.id].dia != 'M'
    assert result.files[old.id] == ref.files[old.id]


def test_calendari_per_totes_les_setmanes_i_aula_tancada():
    first = nova(activitat='inventada-activitat')
    second = nova('inventada-setmana-2', activitat=first.activitat,
                  data=first.data+dt.timedelta(days=7))
    # Només un dia comú viable; totes les altres dates estan aturades.
    stops = {_set: [(0, 1440)] for s in (first, second) for day in range(5)
             if day != 2 for _set in [s.data+dt.timedelta(days=day)]}
    base = base_petita(first, second, aturades=stops)
    # No s'hereta una aturada de partida en aquest test.
    first.data += dt.timedelta(days=2)
    second.data += dt.timedelta(days=2)
    first.dia = second.dia = 'X'
    base.tancaments = [Tancament('0', first.data, second.data)]
    result, _ = resol_congelat(base, referencia(base, first, second), temps_s=5)
    assert result.files[first.id].dia == 'X'
    assert result.files[first.id].aula != '0'
    assert result.files[first.id] == result.files[second.id]


def test_domini_buit_es_prova_només_amb_rutina_i_52_congelat():
    new = nova(alumnes=101)
    base = base_petita(new)
    result, stats = resol_congelat(base, referencia(base, new), temps_s=5)
    assert result is None and stats['estat'] == 'INFEASIBLE'
    assert stats['causa'] == 'domini_buit'
    assert stats['diagnostic_activitats'][0]['aules_compatibles'] == 0
    assert '5.2 congelat' in stats['condicions']


def test_reserva_compta_unio_aules_dins_hora():
    new = nova(durada=30)
    old = sessio('inventada-vella', torn='mati', ini=510, durada=30,
                 aula='0', cohorts=('ALTRE:1r',), docents=frozenset())
    base = base_petita(new, old)
    base.aules = {str(i): Aula(str(i), 'INVENTAT', 'Aules docents', 100) for i in range(3)}
    # Només hi ha el dilluns 09:00. La classe anterior ja ocupa el cubell:
    # es pot reutilitzar la seva aula, però no ocupar-ne una segona.
    base.aturades = {new.data: [(0, 540), (570, 1440)]}
    base.dies_sense_classe = frozenset(new.data+dt.timedelta(days=d) for d in range(1, 5))
    new.ini = 540
    ref = referencia(base, new)
    result, _ = resol_congelat(base, ref, temps_s=5)
    assert result.files[new.id].h_ini == '09:00'
    assert result.files[new.id].aula == '0'
    assert avalua_rapid(base, result).veredicte == 'VALIDA'


def test_persones_i_aules_entre_activitats_noves():
    a = nova('inventada-a', durada=180)
    b = nova('inventada-b', durada=180)
    base = base_petita(a, b)
    result, _ = resol_congelat(base, referencia(base, a, b), temps_s=5)
    assert result is not None
    assert avalua_rapid(base, result).veredicte == 'VALIDA'
    assert result.files[a.id].dia != result.files[b.id].dia or result.files[a.id].h_ini != result.files[b.id].h_ini


def test_compartides_sumen_aforament_i_comparteixen_rutina():
    a = nova('inventada-a', compartida='inventada-compartida', alumnes=60)
    b = nova('inventada-b', compartida=a.compartida, alumnes=60,
             cohorts=('ALTRE:1r',))
    base = base_petita(a, b)
    result, stats = resol_congelat(base, referencia(base, a, b), temps_s=5)
    assert result is None and stats['estat'] == 'INFEASIBLE'
    assert stats['activitats_noves'] == 1


def test_dobles_conserven_vincle_i_cap_aula_propia():
    new = nova()
    host = sessio('inventada-host', codi='inventat-codi', ini=900, aula='0')
    double = sessio('inventada-doble', codi=host.codi, ini=host.ini,
                    sense_espai=True, grup='TE/91', docents=host.docents)
    base = base_petita(new, host, double)
    ref = referencia(base, new)
    result, _ = resol_congelat(base, ref, temps_s=5)
    assert not any(comprova_proposta(base, result, ref).values())
    assert result.files[double.id] == ref.files[double.id]
    assert not result.files[double.id].aula


def test_unknown_no_es_infeasible(monkeypatch):
    from ortools.sat.python import cp_model
    new = nova()
    base = base_petita(new)
    monkeypatch.setattr(cp_model.CpSolver, 'solve', lambda *a: cp_model.UNKNOWN)
    monkeypatch.setattr(cp_model.CpSolver, 'num_branches', property(lambda s: 0))
    monkeypatch.setattr(cp_model.CpSolver, 'num_conflicts', property(lambda s: 0))
    result, stats = resol_congelat(base, referencia(base, new), temps_s=5)
    assert result is None and stats['estat'] == 'UNKNOWN'


def test_rebutja_referencia_aliena_i_noves_fixades():
    new = nova(fixada='inventada-fixada')
    base = base_petita(new)
    with pytest.raises(ValueError):
        resol_congelat(base, referencia(base, new))
    foreign = Proposta.de_base(base_petita(nova('inventada-aliena')))
    with pytest.raises(ValueError):
        referencia_completa(base, foreign)


def test_model_te91_no_solapa_paul92_i_no_eximeix_conflictes_originals_nous():
    te = nova('te', grup='TE/91', docents=frozenset({'D1'}))
    paul = nova('paul', tipus='PAUL', grup='PAUL/92', alumnes=20,
                codi='inventada-paul', docents=frozenset({'D2'}))
    base = base_petita(te, paul)
    ref = referencia(base, te, paul)
    result, stats = resol_congelat(base, ref, temps_s=5)
    assert result is not None
    assert stats['sessions_noves_fora_franja'] == 1
    assert not any(comprova_proposta(base, result, ref).values())
    original = Proposta.de_base(base)
    assert comprova_proposta(base, original, ref)['conflictes_persones_nous'] == 1


def test_objectiu_prioritza_franja_davant_hores_mortes_i_aula_base():
    a = nova('a', ini=540)
    b = nova('b', ini=720)
    base = base_petita(a, b)
    result, stats = resol_congelat(base, referencia(base, a, b), temps_s=5)
    assert stats['estat'] == 'OPTIMAL'
    assert stats['sessions_noves_fora_franja'] == 0
    assert stats['objectiu_hores_mortes_min'] == 120
    assert result.files[a.id].aula == result.files[b.id].aula


def test_objectiu_enganxa_classe_que_cal_moure():
    a = nova('a', ini=540, docents=frozenset({'docent-a'}))
    b = nova('b', ini=660, docents=frozenset({'docent-b'}))
    host = sessio('host', torn='mati', ini=540, aula='0',
                  cohorts=('ALTRE:1r',), docents=a.docents)
    base = base_petita(a, b, host)
    base.dies_sense_classe = frozenset(a.data+dt.timedelta(days=d) for d in range(1, 5))
    result, stats = resol_congelat(base, referencia(base, a, b), temps_s=5)
    assert stats['estat'] == 'OPTIMAL'
    assert stats['sessions_noves_fora_franja'] == 1
    assert stats['objectiu_hores_mortes_min'] == 0
    assert result.files[host.id].h_ini == '09:00'
    assert result.files[b.id].h_ini == '11:00'


def test_comprova_proposta_tambe_mira_docents():
    new = nova(docents=frozenset({'D-inventat'}))
    host = sessio('host', torn='mati', ini=new.ini, aula='0',
                  cohorts=('ALTRE:1r',), docents=new.docents)
    base = base_petita(new, host)
    ref = referencia(base, new)
    assert comprova_proposta(base, Proposta.de_base(base), ref)['conflictes_docents_nous'] == 1
    result, _ = resol_congelat(base, ref, temps_s=5)
    assert not any(comprova_proposta(base, result, ref).values())


def prepara_main(tmp_path, monkeypatch):
    import nivell2.s54 as s54
    new = nova()
    host = sessio('host', ini=900, aula='0')
    base = base_petita(new, host)
    ref = referencia(base, new)
    ref.escriu(tmp_path/'5.2'/'proposta.csv')
    out = tmp_path/'5.4'
    out.mkdir()
    for name in ('proposta.csv', 'informe.json', 'resum.json', 'relaxacions.csv',
                 'violacions.csv', 'xifres.csv', 'execucio.json', 'README.md', 'antic.txt'):
        (out/name).write_text('lliurament anterior: '+name)
    snapshot = {p.name: p.read_bytes() for p in out.iterdir()}
    monkeypatch.setattr(s54, 'RESULTATS', tmp_path)
    monkeypatch.setattr(s54, 'carrega_model', lambda *args: base)
    monkeypatch.setattr(s54, 'carrega_oficial', lambda scenario=None: base if scenario else base_petita(host))
    return s54, base, ref, out, snapshot


@pytest.mark.parametrize('status', ['UNKNOWN', 'INFEASIBLE'])
def test_main_no_toca_cap_fitxer_del_lliurament_si_no_hi_ha_solucio(tmp_path, monkeypatch, status):
    s54, _, _, out, snapshot = prepara_main(tmp_path, monkeypatch)
    monkeypatch.setattr(s54, 'resol_congelat', lambda *a, **kw: (None, {'estat': status}))
    assert s54.main(['--temps', '1']) == 1
    assert {p.name: p.read_bytes() for p in out.iterdir()} == snapshot


@pytest.mark.parametrize('failure', ['exception', 'invalid'])
def test_main_no_publica_si_falla_verificador(tmp_path, monkeypatch, failure):
    from types import SimpleNamespace
    s54, _, _, out, snapshot = prepara_main(tmp_path, monkeypatch)
    def verify(*args, **kw):
        assert kw['referencia'] == tmp_path/'5.2'/'proposta.csv'
        assert kw['json_path'].parent != out
        if failure == 'exception':
            raise RuntimeError('fallada inventada')
        return SimpleNamespace(veredicte='NO VALIDA', compten=lambda: {'R4': 1})
    monkeypatch.setattr(s54, 'verifica', verify)
    with pytest.raises((RuntimeError, ValueError)):
        s54.main(['--temps', '2'])
    assert {p.name: p.read_bytes() for p in out.iterdir()} == snapshot
    assert not list(tmp_path.glob('.s54-*'))


def test_relaxacions_nomes_per_violacions_que_compten(monkeypatch):
    from types import SimpleNamespace as Obj
    import nivell2.s54 as s54
    new = nova()
    base = base_petita(new)
    raw = Obj(violacions=[Obj(regla='R1-TORN', sessions=('necessaria',), compta=True),
                          Obj(regla='R1-TORN', sessions=('doble-heretada',), compta=False)])
    monkeypatch.setattr(s54, 'avalua', lambda *a: raw)
    relax = [Obj(restriccio='R1-TORN', sessions=('necessaria',), justificacio='torn'),
             Obj(restriccio='R1-TORN', sessions=('doble-heretada',), justificacio='dobles')]
    assert s54.relaxacions_necessaries(base, Proposta.de_base(base), relax) == [
        {'restriccio': 'R1-TORN', 'sessions': 'necessaria', 'justificacio': 'torn'}]


def test_publicacio_fallida_restaura_directori(tmp_path, monkeypatch):
    from pathlib import Path
    from nivell2.s54 import publica
    out = tmp_path/'5.4'
    out.mkdir()
    (out/'anterior.txt').write_text('inventat')
    stage = tmp_path/'execucio'/'nou'
    stage.mkdir(parents=True)
    original = Path.rename
    def rename(self, dest):
        if self == stage:
            raise OSError('fallada inventada')
        return original(self, dest)
    monkeypatch.setattr(Path, 'rename', rename)
    with pytest.raises(OSError):
        publica(stage, out)
    assert (out/'anterior.txt').read_text() == 'inventat'


def test_publicacio_no_barreja_fitxers_d_execucions(tmp_path):
    from nivell2.s54 import publica
    out = tmp_path/'5.4'
    out.mkdir()
    (out/'proposta.csv').write_text('proposta inventada anterior')
    (out/'antic.txt').write_text('fitxer antic')
    stage = tmp_path/'execucio'/'nou'
    stage.mkdir(parents=True)
    expected = {'proposta.csv': 'proposta inventada nova', 'informe.json': 'informe inventat nou'}
    for name, content in expected.items():
        (stage/name).write_text(content)
    publica(stage, out)
    assert {p.name: p.read_text() for p in out.iterdir()} == expected
    assert not (stage.parent/'anterior').exists()
