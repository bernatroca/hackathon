"""Casos inventats amb demanda i canvis coneguts."""
import json
from copy import deepcopy
from datetime import date, timedelta

import pytest

from nivell2.base import Base, CONTINGENCIES, GRAU_NOU, Proposta, Sessio
from nivell2.junta import (RESERVA, aulari, calcula, carrega_proposta, documents,
                          escenari_proposta, main, pics_i_mides)
from horaris.check import Informe, _col_loca
from horaris.model import Aula


def petita():
    sessions = {}
    for i in range(3):
        s = Sessio(str(i), '1', 'TE', '81', date(2027, 2, 1) + timedelta(weeks=i),
                   'L', 510, 60, 40, 'A', ('GXX:1r',), 'mati', '', frozenset())
        sessions[s.id] = s
    aules = {'A': Aula('A', '', 'Aules docents', 50)}
    aules.update({f'Reserva{i}': Aula(f'Reserva{i}', '', 'Aules docents', 30)
                  for i in range(RESERVA)})
    return Base(sessions, aules, list(sessions))


def colloca(b, p):
    return _col_loca(b, p.a_files(), Informe())


def test_percentatges_unio_i_pitjor_cohort(tmp_path):
    b = petita()
    s = deepcopy(b.sessions['0'])
    s.id, s.cohorts = 'extra', ('GYY:1r',)
    b.sessions[s.id] = s
    b.ordre.append(s.id)
    p = Proposta.de_base(b)
    p.files['0'].h_ini, p.files['0'].aula = '15:00', 'B'
    p.files['extra'].aula = 'B'
    relax = tmp_path / 'relaxacions.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-TORN,0,Prova explicada\n')
    d = calcula(p, b, b, colloca(b, p), relax)
    rows = {r['cohort']: r for r in d['sessions_mogudes']}
    assert rows['GXX:1r']['mogudes'] == 1
    assert rows['GXX:1r']['mogudes_pct'] == pytest.approx(100 / 3)
    assert rows['GYY:1r']['mogudes_pct'] == 0
    assert rows['GYY:1r']['aula'] == 1
    assert d['pitjor_cohort'] == ['GXX:1r']
    assert d['excepcions'][0]['motiu'] == 'Prova explicada'
    assert d['excepcions_resum'][0]['percentatge'] == pytest.approx(100 / 3)


def test_compartida_suma_alumnes_i_no_duplica_classes():
    b = petita()
    s = deepcopy(b.sessions['0'])
    s.id, s.cohorts, s.alumnes = 'extra', ('GYY:1r',), 30
    s.compartida = b.sessions['0'].compartida = 'compartida'
    s.aula = b.sessions['0'].aula = ''
    b.sessions[s.id] = s
    b.ordre.append(s.id)
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['pitjor']['classes'] == 1
    assert r['mides'][3]['demanda_acumulada'] == 1
    assert r['mides'][3]['falten'] == 1


def test_tipica_mediana_i_franja_interseccio():
    b = petita()
    s = deepcopy(b.sessions['0'])
    s.id, s.ini, s.durada = 'extra', 555, 30
    b.sessions[s.id] = s
    b.ordre.append(s.id)
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['pitjor']['classes'] == 1
    assert r['tipica']['classes'] == 1
    assert r['tipica']['setmana'] == '2027-W06'


def test_sense_excepcions_i_html_segura():
    b = petita()
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    md, html = documents(d)
    assert 'No hi ha excepcions noves als torns.' in md
    assert '@page{size:A4' in html and '@media print' in html
    d['excepcions'] = [{}]
    d['excepcions_resum'] = [{'motiu': '<script>alert(1)</script>', 'nom': 'Grup',
                             'percentatge': 1, 'sessions': 1}]
    assert '<script>alert(1)</script>' not in documents(d)[1]
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in documents(d)[1]


def test_rebutja_duplicades_i_absents(tmp_path):
    b = petita()
    p = Proposta.de_base(b)
    path = p.escriu(tmp_path / 'p.csv')
    path.write_text(path.read_text() + '0,L,08:30,A\n')
    with pytest.raises(ValueError, match='format incorrecte'):
        carrega_proposta(path, b)
    del p.files['0']
    p.escriu(path)
    with pytest.raises(ValueError, match='incompleta'):
        carrega_proposta(path, b)


def test_cli_tres_fitxers(tmp_path, monkeypatch):
    b = petita()
    monkeypatch.setattr('nivell2.junta.carrega_oficial', lambda escenari=None: b)
    monkeypatch.setattr('nivell2.junta.carrega_model', lambda escenari=None: b)
    proposta = Proposta.de_base(b).escriu(tmp_path / 'inventada.csv')
    assert main([str(proposta), '--sortida', str(tmp_path)]) == 0
    d = json.loads((tmp_path / 'junta.json').read_text())
    assert {'pics', 'sessions_mogudes', 'excepcions', 'excepcions_resum'} <= d.keys()
    assert all((tmp_path / f'junta.{ext}').stat().st_size for ext in ('json', 'md', 'html'))


def test_assignar_aula_no_es_moure():
    b = petita()
    b.sessions['0'].aula = ''
    b.sessions['1'].aula = 'J/001'
    b.sessions['2'].sense_espai = True
    p = Proposta.de_base(b)
    for a in p.files.values():
        a.aula = 'A'
    d = calcula(p, b, b, colloca(b, p))
    r, = d['sessions_mogudes']
    assert r['mogudes'] == r['aula'] == 0
    assert r['aules_assignades'] == 1


def test_pic_exclou_seminaris_i_externes_i_compta_aules_diferents():
    b = petita()
    b.aules['S'] = Aula('S', '', 'Seminaris', 30)
    for i, aula in enumerate(('S', 'B3/0021', '')):
        s = deepcopy(b.sessions['0'])
        s.id, s.aula = f'extra{i}', aula
        b.sessions[s.id] = s
        b.ordre.append(s.id)
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']['pitjor']
    assert r['classes'] == 2 and r['estimacio']


def test_mides_aula_assignada_i_classes_successives():
    b = petita()
    b.aules['A'] = Aula('A', '', 'Aules docents', 90)
    b.aules['S'] = Aula('S', '', 'Seminaris', 30)
    for i, (aula, ini, durada) in enumerate((('A', 540, 30), ('S', 510, 60))):
        sessio = deepcopy(b.sessions['0'])
        sessio.id, sessio.aula = f'extra{i}', aula
        sessio.ini, sessio.durada = ini, durada
        b.sessions[sessio.id] = sessio
        b.ordre.append(sessio.id)
    b.sessions['0'].durada = 30
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['pitjor']['classes'] == r['total_mides'] == 1
    assert not r['pitjor']['estimacio']
    assert r['mides'][3]['pic_categoria'] == 1
    assert r['mides'][1]['pic_categoria'] == 0
    assert all(m['marge'] >= 0 for m in r['mides'])


def test_estimacio_mides_mateix_filtre_que_pic():
    b = petita()
    b.sessions['0'].aula = ''
    b.aules['S'] = Aula('S', '', 'Seminaris', 30)
    for i, aula in enumerate(('S', 'B3/0021')):
        sessio = deepcopy(b.sessions['0'])
        sessio.id, sessio.aula = f'extra{i}', aula
        b.sessions[sessio.id] = sessio
        b.ordre.append(sessio.id)
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    r = d['pics']['mati']
    assert r['pitjor']['estimacio']
    assert r['mides'][0]['demanda_acumulada'] == r['total_mides'] == 1
    assert r['mides'][1]['pic_categoria'] == 1
    md, html = documents(d)
    assert 'Matí (estimació)' in md and 'Matí (estimació)' in html


def test_textos_principals_planers_i_detall_separat():
    b = petita()
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    # També comprovem que resums antics i justificacions internes no es mostren al resum.
    d['com_ho_hem_calculat'] = 'R8 PLAB llindar cota'
    d['excepcions'] = [{}]
    d['excepcions_resum'] = [{'motiu': 'R1-TORN PLAB TE/ PAUL SEM J R8',
                             'nom': 'Grau inventat', 'percentatge': 1, 'sessions': 1}]
    md, html = documents(d)
    principals = (md.split('## Detall tècnic')[0],
                  html.split('<section class="detall-tecnic">')[0])
    for text in principals:
        for cadena in ('R8', 'R1-', 'PLAB', ' J ', 'TE/', 'PAUL', 'SEM', 'llindar', 'cota'):
            assert cadena not in text
    assert '<small>' in md and '<small>' in html
    assert 'regla de torn' in md.split('## Detall tècnic')[1]
    metode = md.split('## Com ho hem calculat')[1].split('## Detall tècnic')[0]
    assert 3 <= metode.count('.') <= 4


def test_fora_torn_heretades_i_noves(tmp_path):
    b = petita()
    for s in b.sessions.values():
        s.torn = 'tarda'
    p = Proposta.de_base(b)
    # Canviar només l'aula conserva l'horari; canviar dia o hora crea excepció.
    p.files['0'].aula = 'Inventada'
    p.files['1'].h_ini = '09:30'
    p.files['2'].dia = 'M'
    relax = tmp_path / 'relaxacions.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-TORN,1|2,Motiu inventat\n')
    d = calcula(p, b, b, colloca(b, p), relax, '5.2')
    assert d['fora_torn_ja_avui'] == 1
    assert len(d['excepcions']) == 2
    for text in documents(d):
        assert 'Excepcions noves als torns' in text
        assert '1 classe ja es fa avui fora del seu torn i no es toca.' in text


def test_tarda_i_percentatges_catalans():
    from nivell2.junta import percentatge
    assert percentatge(12) == '12 %'
    assert percentatge(12.5) == '12,5 %'
    b = petita()
    p = Proposta.de_base(b)
    p.files['0'].h_ini = '15:30'
    d = calcula(p, b, b, colloca(b, p), nom_proposta='5.2')
    assert d['pics']['tarda']['pitjor']['classes'] == 1
    assert d['pics']['tarda']['total_mides'] == 1
    d['sessions_mogudes'][0]['mogudes_pct'] = 12.5
    for text in documents(d):
        assert '12,5 %' in text
        assert '.0%' not in text


def test_documents_cap_curs():
    b = petita()
    p = Proposta.de_base(b)
    for text in documents(calcula(p, b, b, colloca(b, p), nom_proposta='5.2')):
        assert "Cap curs canvia de dia ni d" in text


@pytest.mark.parametrize('total', [3, 9, 21])
def test_aulari_i_documents_amb_reserva_calculada(total):
    b = petita()
    for i in range(total - len(b.aules)):
        b.aules[f'Extra{i}'] = Aula(f'Extra{i}', '', 'Aules docents', 30)
    b.aules['Seminari'] = Aula('Seminari', '', 'Seminaris', 30)
    assert aulari(b) == {'ordinaries': total, 'reserva': RESERVA,
                         'disponibles': total - RESERVA}
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    maxim = total - RESERVA
    for torn in d['pics'].values():
        assert torn['pitjor']['aules_disponibles'] == maxim
        assert torn['tipica']['aules_disponibles'] == maxim
        assert torn['mides'][0]['oferta_acumulada'] == maxim
    md, html = documents(d)
    assert f"L'aulari té {total} aules ordinàries; en guardem {RESERVA} de reserva per a imprevistos." in md
    for text in (md, html):
        assert (f'Al matí queden {maxim - 1} aules lliures' in text if maxim > 2
                else 'Al matí no queda cap aula lliure' in text)
        assert ('Aquest marge permet absorbir imprevistos' in text) == (maxim > 1)
        assert 'aules de reserva' in text
        paragraf = text.split('## Detall tècnic')[0].split('<section class="detall-tecnic">')[0]
        assert 'R8' not in paragraf and 'PLAB' not in paragraf
    assert f'1/{maxim}' in md and f'1/{maxim}' in html


@pytest.mark.parametrize('nom,escenari', [('5.1', None), ('5.2', None),
                                         ('5.3', CONTINGENCIES), ('5.4', GRAU_NOU)])
def test_cli_escenari_de_cada_proposta(tmp_path, monkeypatch, nom, escenari):
    b = petita()
    crides = []
    def carrega(e):
        crides.append(e)
        return b
    monkeypatch.setattr('nivell2.junta.carrega_oficial', carrega)
    monkeypatch.setattr('nivell2.junta.carrega_model', carrega)
    proposta = Proposta.de_base(b).escriu(tmp_path / nom / 'proposta.csv')
    assert escenari_proposta(nom) == escenari
    assert main([str(proposta), '--sortida', str(tmp_path / 'resum')]) == 0
    assert crides == [escenari, escenari]


def test_files_daltres_semestres_del_mateix_escenari(tmp_path, monkeypatch):
    b = petita()
    completa = deepcopy(b)
    s = deepcopy(b.sessions['0'])
    s.id = 'altre-semestre-inventat'
    completa.sessions[s.id] = s
    p = Proposta.de_base(completa)
    path = p.escriu(tmp_path / 'inventada.csv')
    crides = []
    def carrega(escenari, semestre):
        crides.append((escenari, semestre))
        return completa
    monkeypatch.setattr('nivell2.junta.carrega_oficial', carrega)
    _, col = carrega_proposta(path, b, GRAU_NOU)
    assert set(col) == set(b.sessions)
    assert crides == [(GRAU_NOU, None)]


def test_declarada_sense_canvi_horari_i_heretada_exclosa(tmp_path):
    b = petita()
    for s in b.sessions.values():
        s.torn = 'tarda'
        s.fixada = 'R1: GXX 1r'
    p = Proposta.de_base(b)
    b.sessions['0'].fixada = ''
    p.files['0'].aula = 'Reserva0'
    relax = tmp_path / 'relaxacions.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-TORN,0|1|2,Motiu inventat\n')
    d = calcula(p, b, b, colloca(b, p), relax)
    assert [e['id_sessio'] for e in d['excepcions']] == ['0']
    assert d['fora_torn_ja_avui'] == 0
    assert d['fixades_tarda'] == 2
    r, = d['sessions_mogudes']
    assert r['afectades'] == r['aula'] == 1
    assert r['franja'] == 0


def test_pic_instantani_successives_en_aules_diferents():
    b = petita()
    b.sessions['0'].durada = 30
    s = deepcopy(b.sessions['0'])
    s.id, s.ini, s.aula = 'extra', 540, 'Reserva0'
    b.sessions[s.id] = s
    b.ordre.append(s.id)
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['simultani']['classes'] == 1
    assert r['pitjor']['classes'] == 2


def test_escriptura_atomica(tmp_path, monkeypatch):
    from nivell2 import junta
    path = tmp_path / 'junta.json'
    path.write_text('{"anterior": true}')
    replace = junta.os.replace
    def comprova(origen, desti):
        assert origen.parent == path.parent
        assert json.loads(path.read_text()) == {'anterior': True}
        assert json.loads(origen.read_text()) == {'nou': True}
        replace(origen, desti)
    monkeypatch.setattr(junta.os, 'replace', comprova)
    junta.escriu_atomic(path, '{"nou": true}')
    assert json.loads(path.read_text()) == {'nou': True}
    assert list(tmp_path.iterdir()) == [path]


def test_textos_planers():
    from nivell2 import junta
    assert junta.classe(1) == 'classe'
    assert junta.classe(2) == 'classes'
    assert 'sense curs a les dades' in junta.nom('GXX:?')
    assert junta.motiu_planer('vegeu diagnostic.md') != junta.MOTIU_S04526


def test_laboratori_en_aula_ordinaria_es_classe_simultania():
    b = petita()
    for sessio in b.sessions.values():
        sessio.tipus = 'PLAB'
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['pitjor']['classes'] == 1
    assert r['simultani']['classes'] == 1


def test_export_sense_fitxers_interns_ni_ajust_javascript():
    b = petita()
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    d['excepcions_resum'] = [dict(motiu='vegeu diagnostic.md', nom='Inventat', percentatge=1, sessions=1)]
    md, html = documents(d)
    assert 'diagnostic.md' not in md + html
    assert 'beforeprint' not in html
    assert '@page{size:A4;margin:10mm}' in html
    assert '.detall-tecnic{display:none}' in html


def test_publicacio_fitxers_reals_i_neteja(tmp_path):
    from nivell2 import junta
    b = petita()
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    vell = tmp_path / '.generacio-antiga'
    vell.mkdir()
    for ext in ('json', 'md', 'html'):
        (vell / f'junta.{ext}').write_text('antic')
        (tmp_path / f'junta.{ext}').symlink_to(f'.actual/junta.{ext}')
    (tmp_path / '.actual').symlink_to(vell.name, target_is_directory=True)
    junta.publica(tmp_path, d)
    guardat = json.loads((tmp_path / 'junta.json').read_text())
    for ext, document in zip(('md', 'html'), documents(guardat)):
        path = tmp_path / f'junta.{ext}'
        assert not path.is_symlink()
        assert path.read_text() == document
        assert d['empremta'] in document
    assert not (tmp_path / 'junta.json').is_symlink()
    assert {p.name for p in tmp_path.iterdir()} == {'junta.json', 'junta.md', 'junta.html'}
    junta.publica(tmp_path, dict(d, data='2027-01-01'))
    assert json.loads((tmp_path / 'junta.json').read_text())['data'] == '2027-01-01'


def test_fixades_gei_separades(tmp_path):
    b = petita()
    for s in b.sessions.values():
        s.cohorts, s.fixada, s.ini = ('GXX:?' if s.id == '0' else 'GYY:1r',), 'R1: GEI 1r', 900
    p = Proposta.de_base(b)
    relax = tmp_path / 'relaxacions.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-TORN,0|1|2,Regla 1\n')
    d = calcula(p, b, b, colloca(b, p), relax)
    assert d['fixades_tarda'] == 3 and not d['excepcions']
    assert '3 classes fixades que ja són a la tarda (regla 1)' in documents(d)[0]


def test_marge_real_i_motiu_del_cas(tmp_path):
    from nivell2 import junta
    b = petita()
    s = b.sessions.pop('0')
    s.id, s.data, s.torn, s.dia = 'inventada-avaluacio', date(2027, 2, 1), 'tarda', 'L'
    b.sessions[s.id] = s
    b.ordre[0] = s.id
    p = Proposta.de_base(b)
    relax = tmp_path / 'relaxacions.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-TORN,inventada-avaluacio,Setmana d’avaluació: impossibilitat demostrada amb R1 dura; vegeu ../5.2/diagnostic.md.\n')
    d = calcula(p, b, b, colloca(b, p), relax)
    assert d['excepcions'][0]['motiu'] == junta.MOTIU_S04526
    assert '1 excepció nova, demostrada' in junta.resum_excepcions(d)
    d['pics']['tarda']['pitjor']['classes'] = 1
    assert junta.titol_marge(d) == 'Al matí no queda cap aula lliure a l’hora punta'
    d['aulari']['disponibles'] = 2
    assert 'queda 1 aula lliure' in junta.titol_marge(d)


@pytest.mark.parametrize('aula', ['', 'LAB'])
def test_plab_sense_aula_ordinaria_no_es_demanda(aula):
    b = petita()
    b.aules['LAB'] = Aula('LAB', '', 'Laboratoris docents', 30)
    s = deepcopy(b.sessions['0'])
    s.id, s.tipus, s.aula = 'laboratori-inventat', 'PLAB', aula
    b.sessions[s.id] = s
    b.ordre.append(s.id)
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['simultani']['classes'] == 1
    assert r['pitjor']['classes'] == 1


def test_motiu_avaluacio_reconeix_nomes_relaxacio_coneguda():
    from nivell2 import junta
    assert junta.es_motiu_avaluacio("Setmana d'avaluació: impossibilitat demostrada amb R1 dura; vegeu diagnostic.md.")
    assert not junta.es_motiu_avaluacio('Un altre motiu: diagnostic.md')


@pytest.mark.parametrize('mati,tarda,titol', [
    (21, 20, 'Al matí calen 21 aules de 19: ja cal fer servir la reserva'),
    (19, 13, 'Al matí no queda cap aula lliure a l’hora punta'),
    (15, 18, 'A la tarda queda 1 aula lliure a l’hora punta'),
    (15, 13, 'Al matí queden 4 aules lliures a l’hora punta'),
])
def test_marge_del_torn_mes_ple(mati, tarda, titol):
    from nivell2 import junta
    b = petita()
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    d['aulari']['disponibles'] = 19
    for torn, n in [('mati', mati), ('tarda', tarda)]:
        d['pics'][torn]['pitjor']['classes'] = n
    assert junta.titol_marge(d) == titol
    assert ('ja se superen' in junta.explicacio_marge(d)) == (max(mati, tarda) > 19)
    assert ('Aquest marge permet' in junta.explicacio_marge(d)) == (max(mati, tarda) < 19)
    assert titol in documents(d)[0]


@pytest.mark.parametrize('proposta', ['Avui', '5.1', '5.2', '5.3', '5.4'])
def test_a4_identificat_i_dates_planeres(proposta):
    from nivell2 import junta
    b = petita()
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p), nom_proposta=proposta)
    d['data'] = '2026-11-08T02:07:02+01:00'
    md, html = documents(d)
    titol = 'Resum per a la Junta · ' + junta.NOMS_PROPOSTES[proposta]
    assert md.startswith('# ' + titol)
    assert '<title>' + titol + '</title>' in html
    assert '<h1>' + titol + '</h1>' in html
    assert '08/11/2026 02:07' in md
    assert 'setmana del 01/02' in md
    assert '2027-W' not in md + html
    assert '(aules per a classes)' not in md + html
    assert 'Empremta:' not in md.split('## Detall tècnic')[0]
    assert junta.empremta_resum(d) in md.split('## Detall tècnic')[1]
    if proposta != 'Avui':
        assert 'comparat amb l’horari d’avui' in md
    if proposta in ('Avui', '5.1'):
        assert '0 classes fixades' not in md
    if proposta == '5.1':
        assert 'Aquesta proposta no mou cap hora.' in md


def test_grau_nou_es_compara_amb_52_i_no_es_un_curs_mogut(tmp_path, monkeypatch):
    from nivell2 import junta
    b = petita()
    ref = Proposta.de_base(b)
    ref.files['0'].h_ini = '09:30'
    ref.escriu(tmp_path / '5.2' / 'proposta.csv')
    nou = deepcopy(b)
    s = deepcopy(b.sessions['0'])
    s.id, s.cohorts, s.aula, s.ini = 'grau-inventat', ('GNOU:1r',), 'Reserva0', 570
    nou.sessions[s.id] = s
    nou.ordre.append(s.id)
    proposta = deepcopy(ref)
    proposta.files[s.id] = Proposta.de_base(nou).files[s.id]
    proposta.files[s.id].h_ini = '10:30'  # Una classe nova mai és un canvi respecte d’avui.
    proposta.escriu(tmp_path / '5.4' / 'proposta.csv')
    monkeypatch.setattr(junta, 'carrega_oficial', lambda e=None: nou if e == GRAU_NOU else b)
    monkeypatch.setattr(junta, 'carrega_model', lambda e=None: nou if e == GRAU_NOU else b)
    d = junta.genera('5.4', resultats=tmp_path)
    assert all(r['cohort'] != 'GNOU:1r' for r in d['sessions_mogudes'])
    assert 'GNOU:1r' not in d['pitjor_cohort']
    assert junta.nom('GNOU:1r') == 'Grau nou (40 places), 1r'
    assert d['grau_nou'] == {'hi_cap': True, 'sessions_collocades': 1,
                            'sessions_52_mogudes': 0, 'pic_mati_52': 1, 'pic_mati': 1}
    for text in junta.documents(d):
        assert 'Hi cap el grau nou de 40 places: 1 classe col·locada' in text
        assert 'Cap classe de la resta es mou' in text
    # També detectem un canvi d’aula de la resta: no fixem el resultat a zero.
    proposta.files['0'].aula = 'Reserva1'
    proposta.escriu(tmp_path / '5.4' / 'proposta.csv')
    assert junta.genera('5.4', resultats=tmp_path)['grau_nou']['sessions_52_mogudes'] == 1


def test_imprevistos_usa_recompte_compartit_i_dates_explicites(tmp_path, monkeypatch):
    from nivell2 import junta
    b = petita()
    ref = Proposta.de_base(b)
    ref.escriu(tmp_path / '5.2' / 'proposta.csv')
    cont = deepcopy(b)
    cont.cancellades = {'0': date(2027, 2, 3)}
    proposta = deepcopy(ref)
    proposta.files['0'].data, proposta.files['0'].dia = '2027-02-03', 'X'
    proposta.files['0'].aula = proposta.files['1'].aula = 'Reserva0'
    proposta.escriu(tmp_path / '5.3' / 'proposta.csv')
    monkeypatch.setattr(junta, 'carrega_oficial', lambda e=None: cont if e == CONTINGENCIES else b)
    monkeypatch.setattr(junta, 'carrega_model', lambda e=None: cont if e == CONTINGENCIES else b)
    d = junta.genera('5.3', resultats=tmp_path)
    assert d['vs_52'] == {'canvis_aula_vs_referencia': 2,
                          'canvis_franja_vs_referencia': 1, 'imprevistos': 1,
                          'canvis_aula_recuperades': 1, 'canvis_aula_oficials': 1}
    for text in junta.documents(d):
        assert 'La classe cancel·lada es recupera un altre dia (canvia de dia i d’aula)' in text
        assert '1 classe més canvia d’aula' in text
        assert 'vegeu Imprevistos' not in text
        assert 'A més, 1 classe cancel·lada' not in text


def test_motiu_demostrat_un_cop_al_document(tmp_path):
    from nivell2 import junta
    b = petita()
    b.sessions['0'].torn = 'tarda'
    p = Proposta.de_base(b)
    relax = tmp_path / 'relaxacions.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-TORN,0,Setmana d’avaluació: impossibilitat demostrada amb R1 dura; vegeu diagnostic.md.\n')
    d = calcula(p, b, b, colloca(b, p), relax, '5.2')
    for text in junta.documents(d):
        assert text.count('ho demostra el càlcul') == 1
        assert 'càlcul.:' not in text
        assert 'S04526' not in text


@pytest.mark.parametrize('tecnic,planer', [
    ('R2-CALENDARI', 'dia no lectiu'),
    ('R4-ALUMNAT', 'coincideix amb una altra classe del grup'),
    ('R4-AULA', 'l’aula està ocupada'),
    ('R4-DOCENT', 'el professor té una altra classe'),
    ('supera el límit de qualitat de la variant de referència', 'empitjorava massa la resta de l’horari'),
])
def test_motius_de_rutina_planers(tecnic, planer):
    from nivell2 import junta
    text = junta.motiu_planer('Restauració al patró rebutjada: restriccions oficials: ' + tecnic)
    assert text == planer


def test_motiu_fixades_neutre():
    from nivell2 import junta
    assert junta.motiu_planer(junta.MOTIU_FIXADES) == 'Classe fixada de 1r/2n: no es mou (regla 1)'


def test_cli_totes_regenera_cinc_propostes(tmp_path, monkeypatch):
    from nivell2 import junta
    b = petita()
    p = Proposta.de_base(b)
    for nom in ('5.1', '5.2', '5.3', '5.4'):
        p.escriu(tmp_path / nom / 'proposta.csv')
    monkeypatch.setattr(junta, 'RESULTATS', tmp_path)
    monkeypatch.setattr(junta, 'carrega_oficial', lambda e=None: b)
    monkeypatch.setattr(junta, 'carrega_model', lambda e=None: b)
    assert junta.main(['--totes']) == 0
    for nom in ('Avui', '5.1', '5.2', '5.3', '5.4'):
        carpeta = tmp_path / 'junta' / ('' if nom == 'Avui' else nom)
        d = json.loads((carpeta / 'junta.json').read_text())
        assert d['proposta'] == nom
        for ext, text in zip(('md', 'html'), junta.documents(d)):
            assert (carpeta / f'junta.{ext}').read_text() == text


def test_demanda_per_alumnes_amb_aula_gran_i_falten_amb_aula_petita():
    b = petita()
    b.aules['A'] = Aula('A', '', 'Aules docents', 160)
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['mides'][4]['ocupades_al_pic'] == 1
    assert r['mides'][4]['demanda_acumulada'] == 0  # 40 alumnes, encara que l'aula sigui gran.
    assert r['mides'][1]['demanda_acumulada'] == 1
    b.aules['A'] = Aula('A', '', 'Aules docents', 30)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['mides'][1]['falten'] == 1  # La demanda pot superar l'oferta, amb aula assignada.


def test_estimacio_sense_aula_no_suma_classes_successives():
    b = petita()
    b.sessions['0'].aula = ''
    b.sessions['0'].durada = 30
    extra = deepcopy(b.sessions['0'])
    extra.id, extra.ini = 'successiva-inventada', 540
    b.sessions[extra.id] = extra
    b.ordre.append(extra.id)
    p = Proposta.de_base(b)
    r = pics_i_mides(b, b, colloca(b, p))['mati']
    assert r['pitjor']['estimacio']
    assert r['pitjor']['classes'] == r['simultani']['classes'] == 1
    assert r['mides'][1]['demanda_acumulada'] == 1


def test_avui_pics_51_nomes_si_conserva_hores(tmp_path, monkeypatch):
    from nivell2 import junta
    b = petita()
    b.sessions['0'].aula = ''
    p = Proposta.de_base(b)
    p.files['0'].aula = 'A'
    p.escriu(tmp_path / '5.1' / 'proposta.csv')
    monkeypatch.setattr(junta, 'carrega_oficial', lambda e=None: b)
    monkeypatch.setattr(junta, 'carrega_model', lambda e=None: b)
    d = junta.genera('Avui', resultats=tmp_path)
    assert 'assignació d’aules de la 5.1' in d['nota_pics']
    assert d['empremtes_assignacio_aules'] == junta.empremtes(tmp_path / '5.1' / 'proposta.csv')
    assert d['pics']['mati']['pitjor']['classes'] == 1
    assert d['pics']['mati']['pitjor']['estimacio']
    for text in junta.documents(d):
        assert 'Classes que canvien' not in text
        assert 'amb aquesta proposta' not in text
        assert 'i no es toquen' not in text
    p.files['0'].h_ini = '10:30'
    p.escriu(tmp_path / '5.1' / 'proposta.csv')
    d = junta.genera('Avui', resultats=tmp_path)
    assert 'empremtes_assignacio_aules' not in d
    assert 'per instant' in d['nota_pics']


def test_conclusio_i_costos_oficials_abans_de_taules(tmp_path):
    from nivell2 import junta
    b = petita()
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p), nom_proposta='5.2')
    path = tmp_path / 'xifres.csv'
    path.write_text('xifra,abans,despres\nveredicte,NO VALIDA,VALIDA\n'
                    'canvis_franja,0,2\ncanvis_aula,0,1\naules_assignades,0,3\n'
                    'incompliments:R3-AFORAMENT,4,0\nincompliments:R3-TIPUS,2,0\n'
                    'incompliments:R2-FINESTRA,1,0\n'
                    'hores_mortes_min,100,150\ndesplacaments_aula,2,5\n'
                    'desplacaments_edifici,0,1\n')
    junta.completa_xifres(d, path)
    assert d['veredicte'] == 'VALIDA'
    assert d['canvis_franja'] == 2
    md, html = documents(d)
    for text in (md, html):
        assert text.index('Conclusió') < text.index('VALIDA') < text.index('Aules ocupades')
        assert text.index('Què empitjora') < text.index('Aules ocupades')
        assert 'Canvien de dia o hora: 2 classes' in text
        assert 'Canvien d’aula: 1 classe' in text
        assert '3 classes reben aula' in text
        assert 'aforament: 4 → 0' in text
        assert '100 a 150 min (+50 %)' in text
        assert '2 a 5' in text and '0 a 1' in text
        assert 'Màxim de classes alhora' not in text
        assert text.index(junta.titol_marge(d)) < text.index('Aules ocupades')


def test_desglossament_torns_ve_del_verificador():
    from nivell2 import junta
    b = petita()
    for s in b.sessions.values():
        s.torn = 'tarda'
    b.sessions['0'].fixada = 'R1: GXX 1r'
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    report = junta.avalua(b, p.a_files())
    assert d['fora_torn_avui_compten'] == len({sid for v in report.violacions
        if v.regla == 'R1-TORN' and not v.heretada for sid in v.sessions})
    assert d['fora_torn_avui_heretades'] == len({sid for v in report.violacions
        if v.regla == 'R1-TORN' and v.heretada for sid in v.sessions})
    d.update(fora_torn_avui=3210, fora_torn_avui_compten=2000, fora_torn_avui_heretades=1210)
    text = junta.resum_guany_torn(d)
    assert '3.210' in text and '2.000 compten al verificador' in text
    assert '1.210 són fixades heretades' in text
    assert 'amb aquesta proposta' not in text
    d['proposta'] = '5.1'
    assert 'no aplica els torns nous' in junta.resum_guany_torn(d)


def test_excepcions_aula_i_marge_real_tancament(tmp_path):
    from horaris.model import Tancament
    from nivell2 import junta
    b = petita()
    b.sessions['0'].fixada = 'R1: GXX 1r'
    b.sessions['1'].tipus, b.sessions['1'].fixada = 'PLAB', 'R7: PLAB'
    b.tancaments = [Tancament('A', s.data, s.data) for s in list(b.sessions.values())[:2]]
    p = Proposta.de_base(b)
    p.files['0'].aula = p.files['1'].aula = 'Reserva0'
    relax = tmp_path / 'relaxacions.csv'
    relax.write_text('restriccio,sessions,justificacio\nR1-FIXADA,0,Aula tancada\n'
                     'R7-PLAB,1,Aula tancada\n')
    d = calcula(p, b, b, colloca(b, p), relax, '5.3')
    files = {r['restriccio']: r for r in d['excepcions_aula']}
    assert files['R1-FIXADA']['sessions'] == ['0']
    assert files['R7-PLAB']['nombre'] == 1
    assert files['R1-FIXADA']['cohorts'] == ['GXX:1r']
    assert '1 classe fixada i 1 laboratori' in junta.resum_excepcions(d)
    m = d['marge_imprevistos']
    assert m['utilitzables'] == 2 and m['ocupades'] == 1
    assert m['marge'] == -1
    assert 'cal 1 aula de la reserva' in junta.titol_marge(d)
    assert '2 aules utilitzables, 1 ocupada' in junta.explicacio_marge(d)
    b.aules['Extra'] = Aula('Extra', '', 'Aules docents', 30)
    d = calcula(p, b, b, colloca(b, p), relax, '5.3')
    assert d['marge_imprevistos']['marge'] == 0
    assert 'no queda cap aula lliure fora de la reserva' in junta.titol_marge(d)
    assert 'Aquest marge permet absorbir' not in junta.explicacio_marge(d)


def test_curs_mes_afectat_51_parla_aules():
    from nivell2 import junta
    b = petita()
    p = Proposta.de_base(b)
    p.files['0'].aula = 'Reserva0'
    d = calcula(p, b, b, colloca(b, p), nom_proposta='5.1')
    assert '33,3 % de les classes canvien d’aula' in junta.resum_curs_afectat(d)
    assert 'Cap curs' not in junta.resum_curs_afectat(d)


def test_noms_propostes_i_master():
    from nivell2 import junta
    assert junta.NOMS_PROPOSTES == {'Avui': 'Avui', '5.1': 'Aules assignades (5.1)',
        '5.2': 'Torns nous (5.2)', '5.3': 'Resoldre els imprevistos (5.3)',
        '5.4': 'Incorporar el grau nou (5.4)'}
    assert junta.nom('MRICSE:M') == 'Màster RICSE'


def test_canvis_grau_nou_separats_del_total_oficial(tmp_path):
    from nivell2 import junta
    b = petita()
    extra = deepcopy(b.sessions['0'])
    extra.id, extra.cohorts = 'nova-inventada', ('GNOU:1r',)
    b.sessions[extra.id] = extra
    b.ordre.append(extra.id)
    p = Proposta.de_base(b)
    p.files['0'].h_ini = p.files[extra.id].h_ini = '09:30'
    d = calcula(p, b, b, colloca(b, p), nom_proposta='5.4')
    assert d['canvis_franja'] == 1  # Només cursos existents.
    path = tmp_path / 'xifres.csv'
    path.write_text('xifra,abans,despres\ncanvis_franja,0,2\nveredicte,NO VALIDA,VALIDA\n')
    junta.completa_xifres(d, path)
    assert d['canvis_franja'] == 2  # Total amb la mateixa definició que el verificador.
    assert d['canvis_franja_existents'] == d['canvis_franja_grau_nou'] == 1
    assert '1 són de cursos existents i 1 del grau nou' in ' '.join(junta.conclusio(d))


def test_estimacio_no_afirma_que_falten_aules():
    from nivell2 import junta
    b = petita()
    b.sessions['0'].aula = ''
    p = Proposta.de_base(b)
    d = calcula(p, b, b, colloca(b, p))
    d['pics']['mati']['pitjor']['classes'] = d['aulari']['disponibles'] + 1
    assert 's’estimen' in junta.titol_marge(d)
    assert 'cal confirmar' in junta.titol_marge(d)
    assert 'cal fer servir la reserva' not in junta.titol_marge(d)
