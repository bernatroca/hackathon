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
