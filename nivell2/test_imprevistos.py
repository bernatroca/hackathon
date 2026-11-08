"""Contracte de dades de la pàgina, amb bases i propostes inventades."""
from copy import deepcopy
from datetime import date, timedelta
import json
from types import SimpleNamespace as NS

import pytest

from nivell2.imprevistos import calcula, motiu_planer, MOTIU_DESCONEGUT, MOTIU_FIXADA, MOTIUS_PLANERS


def escenari():
    dilluns = date(2027, 2, 15)

    def sessio(sid, dies=0, aula='Q9/1003', inici=510, tipus='TE', grup='TE/81'):
        return NS(id=sid, codi='codi-inventat-' + sid, tipus=tipus, grup=grup,
                  data=dilluns + timedelta(days=dies), ini=inici, durada=60,
                  alumnes=20, aula=aula, sense_espai=False)

    sessions = [sessio('reserva-inventada'), sessio('creix-inventada', 1),
                sessio('creix-seguent-inventada', 8), sessio('avaria-inventada', 2),
                sessio('cancel-inventada', 3, tipus='PAUL', grup='PAUL/811'),
                sessio('suport-inventada', 1, aula='Q9/0002'),
                sessio('igual-inventada', 4)]
    sessions[2].codi = sessions[1].codi
    base = NS(sessions={s.id: s for s in sessions}, tancaments=[], cancellades={})
    cont = deepcopy(base)
    cont.tancaments = [
        NS(aula='Q9/0001', data_ini=dilluns, data_fi=dilluns + timedelta(days=4), ini=0, fi=1440),
        NS(aula='Q9/0003', data_ini=dilluns + timedelta(days=2),
           data_fi=dilluns + timedelta(days=2), ini=510, fi=570)]
    for sid in ('creix-inventada', 'creix-seguent-inventada'):
        cont.sessions[sid].alumnes = 70
    cont.cancellades = {'cancel-inventada': dilluns + timedelta(days=4)}
    ref = NS(files={s.id: NS(dia='LMXJV'[s.data.weekday()],
                            h_ini=f'{s.ini//60:02}:{s.ini%60:02}', aula=s.aula, data='') for s in sessions})
    # Les aules de la proposta differeixen de les aules de partida.
    ref.files['reserva-inventada'].aula = 'Q9/0001'
    ref.files['avaria-inventada'].aula = 'Q9/0003'
    final = deepcopy(ref)
    for sid in ('reserva-inventada', 'creix-inventada', 'creix-seguent-inventada', 'avaria-inventada', 'suport-inventada'):
        final.files[sid].aula = 'Q9/0002'
    final.files['avaria-inventada'].h_ini = '10:30'
    final.files['suport-inventada'].aula = 'Q9/0004'
    final.files['cancel-inventada'].dia = 'V'
    final.files['cancel-inventada'].data = (dilluns + timedelta(days=4)).isoformat()
    noms = {s.codi: 'Assignatura Inventada ' + str(i) for i, s in enumerate(sessions)}
    return base, cont, ref, final, noms


def resultat(entrades=None, relaxacions=(), **kwargs):
    b, c, p, q, noms = entrades or escenari()
    return calcula(b, c, p, q, relaxacions, noms=noms, **kwargs)


def test_quatre_imprevistos_sobre_52_i_no_sobre_partida():
    d = resultat()
    assert [t['clau'] for t in d['imprevistos']] == ['aula_reservada', 'grup_creix', 'aula_avariada', 'recuperacio']
    assert [t['sessions_afectades'] for t in d['imprevistos']] == [1, 2, 1, 1]
    assert [t['canvis_aula'] for t in d['imprevistos']] == [1, 2, 1, 0]
    assert [t['canvis_franja'] for t in d['imprevistos']] == [0, 0, 1, 1]
    assert d['resum']['canvis_aula_vs_referencia'] == 5
    assert d['resum']['canvis_franja_vs_referencia'] == 2
    assert d['resum']['classes_de_suport'] == 1
    assert len(d['files']) == 6
    assert not any('codi-inventat' in r['assignatura'] for r in d['files'])


def test_dates_explicites_recuperacio_i_ordre_per_data_i_hora():
    d = resultat()
    recuperacio = next(r for r in d['files'] if 'recuperacio' in r['imprevistos'])
    assert 'Dijous 18/02/2027' in recuperacio['abans']
    assert 'Divendres 19/02/2027' in recuperacio['despres']
    assert recuperacio['grup'] == 'Subgrup 811 · problemes'
    assert [(r['data'], r['hora']) for r in d['files']] == sorted((r['data'], r['hora']) for r in d['files'])
    assert 'fins al 19/02/2027' in d['imprevistos'][3]['descripcio']
    assert 'passa de 20 a 70 alumnes' in d['imprevistos'][1]['descripcio']
    assert 'Q9/0001' in d['imprevistos'][0]['descripcio']


def test_excepcions_noves_per_sessio_sense_confondre_heretades():
    antiga = {'restriccio': 'R1-FIXADA', 'sessions': 'reserva-inventada', 'justificacio': 'Motiu inventat.'}
    ampliada = dict(antiga, sessions='reserva-inventada|avaria-inventada')
    d = resultat(relaxacions=[ampliada, ampliada], relaxacions_referencia=[antiga])
    assert [t['excepcio'] for t in d['imprevistos']] == [False, False, True, False]
    assert d['imprevistos'][2]['motius'] == [MOTIU_DESCONEGUT]
    assert d['resum']['relaxacions_per_motiu'] == [{'motiu': 'Motiu inventat.', 'sessions': 2}]
    # Una justificació nova de la mateixa regla també és una excepció nova.
    d = resultat(relaxacions=[dict(antiga, justificacio='Un altre motiu inventat.')], relaxacions_referencia=[antiga])
    assert d['imprevistos'][0]['excepcio']


def test_solapament_dimprevistos_no_duplica_fila_ni_total():
    entrades = escenari()
    entrades[1].sessions['reserva-inventada'].alumnes = 90
    d = resultat(entrades)
    fila = next(r for r in d['files'] if 'aula_reservada' in r['imprevistos'])
    assert fila['imprevistos'] == ['aula_reservada', 'grup_creix']
    assert len(d['files']) == 6
    assert d['resum']['canvis_aula_vs_referencia'] == 5
    assert d['imprevistos'][1]['sessions_afectades'] == 3


def test_limit_de_tancament_sense_espai_i_dia_proposat():
    b, c, p, q, noms = escenari()
    # Acaba just quan comença l'avaria: no hi ha solapament.
    c.tancaments[1].ini = 570
    assert resultat((b, c, p, q, noms))['imprevistos'][2]['sessions_afectades'] == 0
    c.sessions['reserva-inventada'].sense_espai = True
    assert resultat((b, c, p, q, noms))['imprevistos'][0]['sessions_afectades'] == 0
    c.sessions['reserva-inventada'].sense_espai = False
    # La classe de dimecres s'ha mogut a dilluns al 5.2.
    c.tancaments[1].ini = 0
    p.files['avaria-inventada'].dia = 'L'
    assert resultat((b, c, p, q, noms))['imprevistos'][2]['sessions_afectades'] == 0


def test_funcio_pura_serialitzable_i_veredicte_no_inferit():
    entrades = escenari()
    copia = deepcopy(entrades)
    d = resultat(entrades)
    assert entrades == copia
    assert json.loads(json.dumps(d)) == d
    assert d['resum']['veredicte'] == ''
    assert d['resum']['temps_s'] is None
    d = resultat(resum={'veredicte': 'VALIDA', 'temps_s': 2.5})
    assert d['resum']['veredicte'] == ''  # Un resum antic no acredita el CSV.
    d = resultat(informe={'veredicte': 'VALIDA'}, resum={'temps_s': 2.5})
    assert d['resum']['veredicte'] == 'VALIDA'
    assert d['resum']['temps_s'] == 2.5


def test_sense_canvis_i_aula_no_indicada():
    b, c, p, _, noms = escenari()
    d = resultat((b, c, p, deepcopy(p), noms))
    assert d['files'] == []
    assert d['resum']['canvis_aula_vs_referencia'] == 0
    q = deepcopy(p)
    p.files['cancel-inventada'].aula = ''
    d = resultat((b, c, p, q, noms))
    assert 'Aula no indicada a les dades' in d['files'][0]['abans']


def test_bases_incompatibles_i_motius_planers():
    b, c, p, q, noms = escenari()
    del q.files['igual-inventada']
    with pytest.raises(ValueError, match='mateixes classes'):
        resultat((b, c, p, q, noms))
    assert motiu_planer('R1-FIXADA: TE, PAUL, SEM i PLAB.') == MOTIU_DESCONEGUT


def test_recompte_csv_inclou_recuperada_i_ignora_resum_antic():
    b, c, p, q, noms = escenari()
    q.files['cancel-inventada'].aula = 'Q8/0001'
    d = resultat((b, c, p, q, noms), resum={'canvis_aula_vs_referencia': 500,
                  'canvis_franja_vs_referencia': 500, 'veredicte': 'VALIDA'},
                 informe={'veredicte': 'NO VALIDA',
                          'objectius': {'canvis_aula_vs_referencia': 5}})
    assert d['resum']['canvis_aula_vs_referencia'] == 6
    assert d['resum']['canvis_franja_vs_referencia'] == 2
    assert d['resum']['canvis_aula_oficials'] == 5
    assert d['resum']['canvis_aula_recuperades'] == 1
    assert d['resum']['veredicte'] == 'NO VALIDA'
    assert motiu_planer('R2-FRANJA') == MOTIU_DESCONEGUT
    assert motiu_planer('R4-DOCENT') == MOTIU_DESCONEGUT


@pytest.mark.parametrize('original,planer', MOTIUS_PLANERS.items())
def test_traduccions_conegudes_i_original_al_detall(original, planer):
    assert motiu_planer(original) == planer
    assert motiu_planer(original.replace('’', "'").replace('diagnostic.md', '../5.2/diagnostic.md')) == planer
    entrades = escenari()
    if planer == MOTIU_FIXADA:
        entrades[1].sessions['reserva-inventada'].fixada = 'R1: GXX 1r'
    d = resultat(entrades, relaxacions=[{'restriccio': 'R1-FIXADA',
                 'sessions': 'reserva-inventada', 'justificacio': original}])
    assert d['imprevistos'][0]['motius'] == [planer]
    assert d['resum']['relaxacions_per_motiu'] == [{'motiu': original, 'sessions': 1}]


@pytest.mark.parametrize('text', ['', 'R9 nova regla: diagnostic.md', 'Motiu encara desconegut.'])
def test_motiu_desconegut_prudent(text):
    assert motiu_planer(text) == MOTIU_DESCONEGUT


@pytest.mark.parametrize('conegut', [True, False])
@pytest.mark.parametrize('n', [1, 2])
def test_motius_compten_classes_uniques_per_targeta(conegut, n):
    from nivell2.imprevistos import MOTIU_FIXADA
    b, c, p, q, noms = escenari()
    # La reserva afecta tres classes; només una o dues tenen aquesta excepció.
    p.files['creix-inventada'].aula = 'Q9/0001'
    p.files['suport-inventada'].aula = 'Q9/0001'
    original = next(iter(MOTIUS_PLANERS)) if conegut else 'Motiu nou inventat.'
    ids = ['reserva-inventada', 'creix-inventada'][:n]
    if conegut:
        for sid in ids + ['avaria-inventada']:
            c.sessions[sid].fixada = 'R1: GXX 1r'
        q.files['avaria-inventada'].h_ini = p.files['avaria-inventada'].h_ini
    rows = [{'restriccio': rule, 'sessions': '|'.join(ids + ['avaria-inventada']),
             'justificacio': original} for rule in ('R1-FIXADA', 'R7-PLAB')]
    # La tercera classe ja tenia l’excepció: no és una excepció nova.
    antiga = {'restriccio': 'R1-FIXADA', 'sessions': 'suport-inventada', 'justificacio': original}
    d = calcula(b, c, p, q, rows + rows + [antiga],
                relaxacions_referencia=[antiga], noms=noms)
    reserva, _, avaria, _ = d['imprevistos']
    assert reserva['sessions_afectades'] == 3
    assert reserva['motius'] == [motiu_planer(original, n)]
    assert reserva['motius'][0].startswith(f'{n} d’aquestes classes ')
    assert avaria['motius'] == [motiu_planer(original, 1)]
    if conegut:
        assert ('estava fixada;' if n == 1 else 'estaven fixades;') in reserva['motius'][0]
        assert ('li canviem' if n == 1 else 'els canviem') in reserva['motius'][0]
        assert ('es fa el mateix dia' if n == 1 else 'es fan el mateix dia') in reserva['motius'][0]
    else:
        assert ('necessita una excepció' if n == 1 else 'necessiten una excepció') in reserva['motius'][0]


def test_avaluacio_reutilitza_text_junta_sense_afirmar_que_es_fixada():
    from nivell2.junta import MOTIU_S04526
    original = next(m for m in MOTIUS_PLANERS if m.startswith('Setmana'))
    d = resultat(relaxacions=[{'restriccio': 'R1-TORN',
                 'sessions': 'reserva-inventada', 'justificacio': original}])
    assert d['imprevistos'][0]['motius'] == [MOTIU_S04526]
    assert 'fixada' not in motiu_planer(original)


def test_recuperacio_del_grup_que_creix_no_es_compta_com_canvi_de_franja_del_grup():
    b, c, p, q, noms = escenari()
    c.sessions['cancel-inventada'].alumnes = 70
    q.files['cancel-inventada'].aula = 'Q9/0002'
    d = resultat((b, c, p, q, noms))
    creix, recuperacio = d['imprevistos'][1], d['imprevistos'][3]
    assert creix['sessions_afectades'] == 3
    assert creix['canvis_aula'] == 3
    assert creix['canvis_franja'] == 0
    assert recuperacio['canvis_franja'] == 1
    fila = next(r for r in d['files'] if 'recuperacio' in r['imprevistos'])
    assert fila['abans'].endswith(' (cancel·lada)')
    assert fila['cancellada']
    assert fila['aula_abans'] == 'Q9/1003'
    assert fila['aula_despres'] == 'Q9/0002'
    assert '19/02/2027' in fila['dia_hora_nous']
    assert d['resum']['canvis_franja_vs_referencia'] == 2


def test_capacitats_i_diferencia_entre_horari_davui_i_proposat_son_dinamiques():
    b, c, p, q, noms = escenari()
    c.aules = {'Q9/1003': NS(capacitat=24), 'Q9/0002': NS(capacitat=80)}
    b.sessions['reserva-inventada'].aula = 'Q9/0001'
    p.files['creix-inventada'].aula = 'Q9/0001'
    d = resultat((b, c, p, q, noms))
    reserva, creix = d['imprevistos'][:2]
    assert 'Aquella setmana, l’aula tenia 1 classe a l’horari d’avui i 2 a l’horari proposat.' in reserva['descripcio']
    assert 'Q9/1003 (24 places)' in creix['descripcio']
    assert 'Aules de destinació: dimarts: Q9/0002 (80 places)' in creix['descripcio']
    assert 'passa de 20 a 70 alumnes' in creix['descripcio']


def test_detall_associa_les_regles_amb_el_motiu_sense_canviar_els_recomptes():
    rows = [{'restriccio': regla, 'sessions': 'reserva-inventada',
             'justificacio': 'Motiu inventat.'} for regla in ('R7-PLAB', 'R1-FIXADA')]
    d = resultat(relaxacions=rows)
    assert d['resum']['regles_per_motiu'] == {'Motiu inventat.': ['R1-FIXADA', 'R7-PLAB']}
    assert d['resum']['relaxacions_per_motiu'] == [{'motiu': 'Motiu inventat.', 'sessions': 1}]


def test_fixades_es_compten_a_les_sessions_no_a_les_relaxacions():
    b, c, p, q, noms = escenari()
    for sid in ('reserva-inventada', 'creix-inventada', 'creix-seguent-inventada', 'suport-inventada'):
        c.sessions[sid].fixada = 'R1: GXX 1r'
        p.files[sid].aula = 'Q9/0001'
        p.files[sid].dia = 'L'
        p.files[sid].data = c.tancaments[0].data_ini.isoformat()
        q.files[sid].dia = 'L'
        q.files[sid].data = p.files[sid].data
    original = next(m for m, planer in MOTIUS_PLANERS.items() if planer == MOTIU_FIXADA)
    rows = [{'restriccio': 'R1-FIXADA', 'sessions': 'reserva-inventada|creix-inventada',
             'justificacio': original}]
    d = resultat((b, c, p, q, noms), relaxacions=rows)
    assert d['imprevistos'][0]['motius'] == [motiu_planer(original, 4)]
    assert d['imprevistos'][0]['excepcio']
    # Les dades de fixació continuen sent certes sense una excepció nova.
    d = resultat((b, c, p, q, noms), relaxacions=rows, relaxacions_referencia=rows)
    assert d['imprevistos'][0]['motius'] == [motiu_planer(original, 4)]
    assert not d['imprevistos'][0]['excepcio']


def test_fixada_que_canvia_hora_no_afirma_que_nomes_canvia_aula():
    b, c, p, q, noms = escenari()
    c.sessions['avaria-inventada'].fixada = 'R1: GXX 1r'
    d = resultat((b, c, p, q, noms))
    assert not d['imprevistos'][2]['motius']


def test_aules_de_destinacio_indiquen_dies_de_la_proposta():
    b, c, p, q, noms = escenari()
    c.aules = {'Q9/0002': NS(capacitat=80), 'Q9/0005': NS(capacitat=90)}
    q.files['creix-inventada'].dia = 'L'
    q.files['creix-seguent-inventada'].dia = 'J'
    q.files['creix-seguent-inventada'].aula = 'Q9/0005'
    d = resultat((b, c, p, q, noms))
    assert 'Aules de destinació: dilluns: Q9/0002 (80 places); dijous: Q9/0005 (90 places).' in d['imprevistos'][1]['descripcio']


def test_motius_de_totes_les_mogudes_i_suport_amb_destinatari():
    b, c, p, q, noms = escenari()
    c.aules = {'Q9/1003': NS(capacitat=24)}
    d = resultat((b, c, p, q, noms))
    assert set(d['motius_per_sessio']) == {r['id_sessio'] for r in d['files']}
    assert all(r['motiu'] == d['motius_per_sessio'][r['id_sessio']] for r in d['files'])
    assert 'passa de 20 a 70 alumnes i no cap a Q9/1003' in d['motius_per_sessio']['creix-inventada']
    assert 'tot el semestre' in d['motius_per_sessio']['creix-inventada']
    suport = next(r for r in d['files'] if r['id_sessio'] == 'suport-inventada')
    assert suport['imprevistos'] == []  # Conserva el filtre de classes de suport.
    assert suport['imprevistos_causants'] == ['grup_creix']
    assert 'Es mou per deixar l’aula a ' + noms[c.sessions['creix-inventada'].codi] in suport['motiu']
    assert 'passa de 20 a 70' in suport['motiu']
    assert '1 classe més es mou per deixar-li l’aula.' in d['imprevistos'][1]['descripcio']
    assert 'Q9/0003 avariada el 17/02/2027' in d['motius_per_sessio']['avaria-inventada']
    assert 'reservada per a un acte' in d['motius_per_sessio']['reserva-inventada']
    assert 'classe cancel·lada del 18/02/2027' in d['motius_per_sessio']['cancel-inventada']


@pytest.mark.parametrize('data,inici', [('2027-02-16', '09:30'), ('2027-02-17', '08:30')])
def test_suport_sense_solapament_no_inventa_destinatari(data, inici):
    b, c, p, q, noms = escenari()
    q.files['creix-inventada'].data = data
    q.files['creix-inventada'].h_ini = inici
    d = resultat((b, c, p, q, noms))
    assert d['imprevistos_per_sessio']['suport-inventada'] == []
    assert 'no s’ha identificat una classe destinatària directa' in d['motius_per_sessio']['suport-inventada']


def test_cadena_de_suport_propaga_limprevist():
    b, c, p, q, noms = escenari()
    # Una segona classe deixa l'aula on va la primera classe de suport.
    p.files['igual-inventada'].dia = 'M'
    p.files['igual-inventada'].aula = 'Q9/0004'
    q.files['igual-inventada'].dia = 'M'
    q.files['igual-inventada'].aula = 'Q9/0005'
    d = resultat((b, c, p, q, noms))
    assert d['imprevistos_per_sessio']['igual-inventada'] == ['grup_creix']
    assert 'Es mou per deixar l’aula' in d['motius_per_sessio']['igual-inventada']
