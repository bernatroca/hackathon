"""Reparacions petites amb dades completament inventades."""
import copy
import datetime as dt

import pytest

from nivell2.base import Base, Proposta, Sessio
from nivell2.reparacio import Canvi, afectades, repara
from nivell2.franges import _referencia
from nivell2.comprova_persones import conflictes, comprova_dobles, parelles_dobles
from horaris.check import avalua, _col_loca, Informe
from horaris.model import Aula, Tancament, Relaxacio

DATE = dt.date(2027, 2, 8)


def sessio(sid, **kwargs):
    fields = dict(id=sid, codi='900001', tipus='TE', grup='TE/81', data=DATE,
                  dia='L', ini=900, durada=60, alumnes=20, aula='Q9/0001',
                  cohorts=(f'G{sid}:3r',), torn='tarda', fixada='',
                  docents=frozenset({f'doc-inventat-{sid}'}), activitat=sid)
    fields.update(kwargs)
    return Sessio(**fields)


def base(*rows):
    # Seminaris per no imposar una reserva de dues aules en fixtures de tres espais.
    rooms = {r: Aula(r, r.split('/')[0], 'Seminaris', n) for r, n in
             [('Q9/0001', 30), ('Q9/0002', 30), ('Q8/1001', 80)]}
    return Base({s.id: s for s in rows}, rooms, [s.id for s in rows])


def resolve(before, after, ref=None):
    ref = ref or Proposta.de_base(before)
    saved = copy.deepcopy(ref)
    result = repara(ref, Canvi(after, before, temps_s=5))
    assert ref == saved
    return result


def validate(b, p):
    assert avalua(b, p.a_files()).veredicte == 'VALIDA'
    col = _col_loca(b, p.a_files(), Informe())
    assert not conflictes(col)
    assert comprova_dobles(b, col, parelles_dobles(b)[0]) == {'separades': [], 'duplicades': []}


def test_mateix_passadis_i_referencia_congelada():
    b = base(sessio('afectada'), sessio('fixa', ini=1020))
    new = copy.deepcopy(b)
    ref = Proposta.de_base(b)
    # L'afectació segueix el 5.2, no l'aula de partida de la base.
    ref.files['afectada'].aula = 'Q9/0002'
    new.tancaments = [Tancament('Q9/0002', DATE, DATE+dt.timedelta(days=4))]
    result = resolve(b, new, ref)
    p = result.proposta
    assert p.files['afectada'].aula == 'Q9/0001'
    assert p.files['fixa'] == ref.files['fixa']
    assert result.estadistiques['canvis_franja_vs_referencia'] == 0
    assert result.estadistiques['sessions_afectades_per_imprevist']['aula_reservada'] == 1
    validate(new, p)


def test_una_altra_aula_abans_de_moure_hora():
    b = base(sessio('a'), sessio('b', aula='Q9/0002'))
    new = copy.deepcopy(b)
    new.tancaments = [Tancament('Q9/0001', DATE, DATE)]
    result = resolve(b, new)
    assert result.proposta.files['a'].aula == 'Q8/1001'
    assert result.estadistiques['canvis_franja_vs_referencia'] == 0
    assert result.estadistiques['sessions_obertes'] == 1
    validate(new, result.proposta)


def test_aula_tancada_obliga_relaxar_només_aula_fixada():
    b = base(sessio('fixada', fixada='R1: inventada'))
    new = copy.deepcopy(b)
    new.tancaments = [Tancament('Q9/0001', DATE, DATE)]
    result = resolve(b, new)
    assert _referencia(b.sessions['fixada'], result.proposta) == (DATE, 900)
    assert result.relaxacions[0]['restriccio'] == 'R1-FIXADA'
    assert result.relaxacions[0]['sessions'] == 'fixada'
    relax = [Relaxacio(r['restriccio'], frozenset(r['sessions'].split('|')), r['justificacio'])
             for r in result.relaxacions]
    assert avalua(new, result.proposta.a_files(), relaxacions=relax).veredicte == 'VALIDA AMB RELAXACIONS DECLARADES'


def test_plab_amb_aula_tancada_conserva_hora_i_equipament_i_declara_canvi():
    b = base(sessio('lab', tipus='PLAB', grup='PLAB/811', fixada='R7: inventada'))
    b.aules = {r: Aula(r, a.edifici, 'Laboratoris docents', a.capacitat) for r, a in b.aules.items()}
    new = copy.deepcopy(b)
    new.tancaments = [Tancament('Q9/0001', DATE, DATE)]
    result = resolve(b, new)
    assert _referencia(b.sessions['lab'], result.proposta) == (DATE, 900)
    assert result.relaxacions[0]['restriccio'] == 'R7-PLAB'
    relax = [Relaxacio(r['restriccio'], frozenset(r['sessions'].split('|')), r['justificacio'])
             for r in result.relaxacions]
    assert avalua(new, result.proposta.a_files(), relaxacions=relax).veredicte == 'VALIDA AMB RELAXACIONS DECLARADES'


def test_compartides_preserven_solapaments_heretats_deduplicats_del_verificador():
    rows = [sessio(sid, compartida=unit, aula=room, alumnes=10,
                   docents=frozenset({'docent-inventat-compartit'}))
            for sid, unit, room in [('a1', 'compartida-a', 'Q9/0001'), ('a2', 'compartida-a', 'Q9/0001'),
                                    ('b1', 'compartida-b', 'Q9/0002'), ('b2', 'compartida-b', 'Q9/0002')]]
    b = base(*rows)
    new = copy.deepcopy(b)
    new.tancaments = [Tancament('Q9/0001', DATE, DATE)]
    result = resolve(b, new)
    assert result.proposta.files['a1'].aula == 'Q8/1001'
    assert result.proposta.files['a2'].aula == 'Q8/1001'
    validate(new, result.proposta)


def test_creixement_totes_les_setmanes_i_aforament_compartit():
    a = sessio('a', compartida='compartida-inventada', alumnes=20)
    shared = sessio('b', compartida='compartida-inventada', alumnes=5)
    later = sessio('c', data=DATE+dt.timedelta(days=7), activitat='a')
    b = base(a, shared, later)
    new = copy.deepcopy(b)
    new.sessions['a'].alumnes = 40
    new.sessions['c'].alumnes = 40
    result = resolve(b, new)
    assert {result.proposta.files[sid].aula for sid in ('a', 'b', 'c')} == {'Q8/1001'}
    assert result.estadistiques['sessions_afectades_per_imprevist']['grup_creix'] == 2
    assert not result.relaxacions
    validate(new, result.proposta)


def test_recuperacio_comprova_docent_alumnat_calendari_i_torn():
    recovered = sessio('cancel', fixada='R1: inventada', cohorts=('GXX:3r',))
    tomorrow = DATE+dt.timedelta(days=1)
    student = sessio('alumne', data=tomorrow, dia='M', ini=870, durada=180,
                     aula='Q9/0002', cohorts=('GXX:3r',), codi='900002')
    teacher = sessio('docent', data=tomorrow, dia='M', ini=1050, durada=210,
                    aula='Q9/0002', docents=recovered.docents)
    b = base(recovered, student, teacher)
    new = copy.deepcopy(b)
    new.cancellades = {'cancel': DATE+dt.timedelta(days=3)}
    new.dies_sense_classe = frozenset({DATE+dt.timedelta(days=2)})
    new.aturades = {DATE+dt.timedelta(days=3): [(870, 1050)]}
    result = resolve(b, new)
    p = result.proposta
    d, ini = _referencia(recovered, p)
    assert d == DATE+dt.timedelta(days=3) and 1050 <= ini <= 1200
    assert p.files['cancel'].data == d.isoformat()
    assert p.files['alumne'] == Proposta.de_base(b).files['alumne']
    validate(new, p)


def test_dobles_segueixen_host_sense_aula_propia():
    host = sessio('host')
    double = sessio('doble', sense_espai=True, aula='', docents=host.docents)
    b = base(host, double)
    new = copy.deepcopy(b)
    new.cancellades = {'host': DATE+dt.timedelta(days=4)}
    # La sessió sense espai conserva setmana i segueix el host recuperat.
    result = resolve(b, new)
    assert result.proposta.files['doble'].aula == ''
    assert _referencia(double, result.proposta) == _referencia(host, result.proposta)
    validate(new, result.proposta)


def test_amplia_veinat_per_intercanviar_aules_sense_moure_franges():
    a = sessio('a', alumnes=60, aula='Q8/1001')
    b = base(a, sessio('b', aula='Q9/0002'))
    b.aules['Q9/0002'] = Aula('Q9/0002', 'Q9', 'Seminaris', 80)
    new = copy.deepcopy(b)
    new.tancaments = [Tancament('Q8/1001', DATE, DATE)]
    result = resolve(b, new)
    assert len(result.estadistiques['intents']) == 2
    assert result.proposta.files['a'].aula == 'Q9/0002'
    assert result.proposta.files['b'].aula == 'Q9/0001'
    assert result.estadistiques['canvis_franja_vs_referencia'] == 0
    validate(new, result.proposta)


def test_no_solucio_no_declara_relaxacio_ni_canvia_torn():
    b = base(sessio('a'))
    new = copy.deepcopy(b)
    new.cancellades = {'a': DATE+dt.timedelta(days=1)}
    new.aturades = {DATE+dt.timedelta(days=1): [(870, 1260)]}
    result = resolve(b, new)
    assert result.proposta is None and result.estat == 'INFEASIBLE'
    assert result.relaxacions == []


def test_cap_canvi_es_idempotent_i_valida_entrades():
    b = base(sessio('a'))
    ref = Proposta.de_base(b)
    assert resolve(b, b).proposta == ref
    with pytest.raises(ValueError):
        repara(ref, Canvi(b, b, temps_s=0))
    with pytest.raises(ValueError):
        repara(Proposta(), Canvi(b, b))


def test_quatre_imprevistos_simultanis():
    rows = [sessio(str(i), data=DATE+dt.timedelta(days=i), dia='LMXJV'[i]) for i in range(4)]
    b = base(*rows)
    new = copy.deepcopy(b)
    new.tancaments = [Tancament('Q9/0001', DATE, DATE+dt.timedelta(days=1)),
                      Tancament('Q9/0001', DATE+dt.timedelta(days=2), DATE+dt.timedelta(days=2))]
    new.sessions['1'].alumnes = 60
    new.cancellades = {'3': DATE+dt.timedelta(days=4)}
    result = resolve(b, new)
    assert result.estadistiques['sessions_afectades'] == 4
    assert all(n for n in result.estadistiques['sessions_afectades_per_imprevist'].values())
    validate(new, result.proposta)


def test_reserva_es_compta_per_aules_diferents_durant_tota_hora():
    b = base(sessio('a', ini=900, durada=30), sessio('b', ini=930, durada=30, aula='Q9/0002'))
    b.aules = {r: Aula(r, a.edifici, 'Aules docents', a.capacitat) for r, a in b.aules.items()}
    new = copy.deepcopy(b)
    new.tancaments = [Tancament('Q9/0001', DATE, DATE)]
    result = resolve(b, new)
    # Tres aules i dues de reserva: totes dues classes successives comparteixen aula.
    assert result.proposta.files['a'].aula == 'Q9/0002'
    validate(new, result.proposta)
