"""Dades inventades sota tmp_path i regressió oficial sense exposar files."""
import copy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import datetime as dt
import json

import duckdb
import pytest

from xat import eines as e
from nivell2.base import Base, Sessio, Proposta
from horaris.model import Aula


@pytest.fixture
def paquet(tmp_path, monkeypatch):
    date = dt.date(2027, 2, 8)
    rows = [Sessio(id=sid, codi='900001', tipus=tipus, grup=grup, data=date,
                  dia='L', ini=ini, durada=60, alumnes=20, aula=aula,
                  cohorts=('GXX:3r',), torn='tarda', fixada='',
                  docents=frozenset({sid}), activitat='A1' if sid != 'S3' else 'A2')
            for sid, tipus, grup, ini, aula in [('S1', 'TE', 'TE/81', 900, 'Q9/0001'),
                                              ('S2', 'PAUL', 'PAUL/811', 960, 'Q9/0001'),
                                              ('S3', 'TE', 'TE/82', 900, 'Q9/0002')]]
    rooms = {r: Aula(r, 'Q9', 'Seminaris', 60) for r in ('Q9/0001', 'Q9/0002', 'Q9/0003')}
    b = Base({s.id: s for s in rows}, rooms, [s.id for s in rows])
    p = Proposta.de_base(b)
    for a in e.APARTATS:
        p.escriu(tmp_path/a/'proposta.csv')
        (tmp_path/a/'informe.json').write_text(json.dumps({'veredicte': 'VALIDA', 'restriccions': {}}))
        (tmp_path/a/'resum.json').write_text('{"incompliments_no_declarats": 0}')
    (tmp_path/'activitats.csv').write_text('activitat_id,grup\nA1,TE/81\n')
    con = duckdb.connect()
    con.execute("CREATE TABLE sessions AS SELECT 'S'||i AS id_sessio, DATE '2027-02-08' AS data, 900 AS ini_min, 960 AS fi_min, '' AS aules_addicionals_partida, '900001' AS codi, 'Assignatura inventada' AS assignatura FROM range(65) t(i)")
    con.execute("CREATE TABLE aules AS SELECT 'Q9/0001' AS aula, 60 AS capacitat")
    monkeypatch.setattr(e.dades, 'connexio', lambda: con)
    monkeypatch.setattr(e.nb, 'carrega_oficial', lambda *args, **kwargs: copy.deepcopy(b))
    monkeypatch.setattr(e.nb, 'RESULTATS_PRINCIPAL', tmp_path)
    monkeypatch.setattr(e.nb, 'PAQUET', tmp_path)
    servei = e._modul('servei')
    monkeypatch.setattr(servei, 'RESULTATS_PART2', tmp_path)
    yield b, p
    con.close()


def test_contracte_i_errors(paquet):
    assert len(e.EINES) == 8
    json.dumps(e.EINES)
    for nom, args in [('?', {}), ('horari_grup', {}), ('xifra', {'id': 'inexistent'}), ('consulta_sql', None), ('prova_canvi', {'apartat': '5.2', 'canvi': {'tipus': 'desconegut'}})]:
        r = e.executa(nom, args)
        assert r['ok'] is False and r['error']
    assert 'IDs disponibles' in e.executa('xifra', {'id': 'inexistent'})['error']


def test_horari_i_ocupacio(paquet):
    r = e.executa('horari_grup', dict(titulacio='GXX', curs='3r', grup='81'))
    assert r['ok'], r
    assert set(r['id_sessio']) == {'S1', 'S2'}
    r = e.executa('ocupacio_aula', dict(aula='Q9/0001', dia='dilluns'))
    assert r['ok'] and r['resultat']['total'] == 2
    assert e.executa('ocupacio_aula', dict(aula='Q9/0001', setmana='2027-W07'))['resultat']['total'] == 0


def test_aules_solapament_i_proposta(paquet):
    args = dict(data='2027-02-08', hora_ini='15:30', durada_min=60, places_min=30, tipus='Seminaris')
    r = e.executa('aules_lliures', args)
    assert r['ok'], r
    assert [a['aula'] for a in r['resultat']['files']] == ['Q9/0003']
    _, p = paquet
    p.files['S3'].aula = 'Q9/0003'
    p.escriu(e.nb.RESULTATS_PRINCIPAL/'5.2'/'proposta.csv')
    r = e.executa('aules_lliures', dict(args, proposta='5.2'))
    assert [a['aula'] for a in r['resultat']['files']] == ['Q9/0002']
    r = e.executa('aules_lliures', dict(args, hora_ini='17:00'))
    assert r['resultat']['total'] == 3  # tocar l'extrem no és solapament
    assert not e.executa('aules_lliures', dict(args, durada_min=-1))['ok']


@pytest.mark.parametrize('sql', ['DELETE FROM sessions', 'SELECT 1; SELECT 2', "SELECT * FROM read_csv('/etc/passwd')", "SELECT * FROM '/etc/passwd'", 'COPY sessions TO \'/tmp/fuita\'', 'SELECT * FROM duckdb_settings()', 'PRAGMA version', 'WITH a AS (SELECT 1) DELETE FROM sessions'])
def test_sql_rebutja(paquet, sql):
    assert not e.executa('consulta_sql', {'sql': sql})['ok']


def test_sql_select_i_limit(paquet):
    for sql in ['SELECT * FROM sessions', 'WITH a AS (SELECT * FROM sessions) SELECT * FROM a', 'SELECT * FROM activitats', 'SELECT * FROM proposta_5_2', "SELECT ';' AS text;"]:
        r = e.executa('consulta_sql', {'sql': sql})
        assert r['ok'], r
        assert len(r['resultat']['files']) <= 50
        json.dumps(r, allow_nan=False)


def test_timeout(paquet, monkeypatch):
    monkeypatch.setattr(e, 'TEMPS_SQL', .02)
    r = e.executa('consulta_sql', {'sql': 'SELECT sum(a.i*b.i) FROM range(1000000) a(i), range(1000000) b(i)'})
    assert not r['ok']


def test_moviment_conflicte_i_no_desa(paquet):
    path = e.nb.RESULTATS_PRINCIPAL/'5.2'/'proposta.csv'
    original = path.read_bytes()
    r = e.executa('prova_canvi', dict(apartat='5.2', canvi={'tipus': 'moure', 'id_sessio': 'S1', 'aula': 'Q9/0002'}))
    assert r['ok'], r
    assert r['resultat']['total'] == 1
    assert r['resultat']['total_incompliments_nous'] > 0
    assert r['resultat']['canvis'][0]['despres']['aula'] == 'Q9/0002'
    assert path.read_bytes() == original
    r = e.executa('prova_canvi', dict(apartat='5.2', canvi={'tipus': 'moure', 'activitat_id': 'A1', 'aula': 'Q9/0003'}))
    assert r['ok'], r
    assert set(r['id_sessio']) == {'S1', 'S2'}


def test_imprevist_real_i_veredicte(paquet):
    r = e.executa('prova_canvi', dict(apartat='5.2', canvi={'tipus': 'imprevist', 'aules_tancades': [{'aula': 'Q9/0001', 'data_ini': '2027-02-08', 'data_fi': '2027-02-08'}]}))
    assert r['ok'], r
    assert r['resultat']['total'] == 2
    assert r['resultat']['veredicte'] == 'VALIDA'


def test_resultat(paquet):
    r = e.executa('resultat_proposta', {'apartat': '5.2'})
    assert r['ok'] and r['resultat']['veredicte'] == 'VALIDA'


def test_xifra_serialitzable(paquet, monkeypatch):
    import numpy as np
    import pandas as pd
    from nivell1 import troballes
    t = troballes.Troballa('inventada', 'Prova', '1', 'Una classe', 'Recompte', 'SELECT id_sessio FROM sessions',
                           pd.DataFrame([{'id_sessio': 'S1', 'ids': np.array(['S1', 'S2'])}]))
    monkeypatch.setattr(troballes, 'moduls', lambda: [type('Modul', (), {'ID': 'inventada'})])
    monkeypatch.setattr(troballes, 'una', lambda *a: t)
    r = e.executa('xifra', {'id': 'inventada'})
    assert r['ok'], r
    assert r['id_sessio'] == ['S1']
    json.dumps(r, allow_nan=False)


@pytest.mark.parametrize('canvi', [
    {'tipus': 'imprevist', 'grups_creixen': [{'codi': '900001', 'grup': 'TE/81', 'alumnes': 30}]},
    {'tipus': 'imprevist', 'sessions_cancel_lades': [{'id_sessio': 'S3', 'recuperar_fins': '2027-02-10'}]},
])
def test_altres_imprevistos(paquet, canvi):
    r = e.executa('prova_canvi', {'apartat': '5.2', 'canvi': canvi})
    assert r['ok'], r
    assert r['resultat']['veredicte'] == 'VALIDA'


@pytest.mark.parametrize('apartat', e.APARTATS)
def test_resultat_sense_resum_conserva_informe(paquet, apartat):
    carpeta = e.nb.RESULTATS_PRINCIPAL / apartat
    (carpeta / 'resum.json').unlink()
    informe = {'veredicte': 'VALIDA', 'restriccions': {'R4': {'compten': 0}},
               'nomes_aules': apartat == '5.1', 'objectius': {'canvis_aula': 2}}
    (carpeta / 'informe.json').write_text(json.dumps(informe))
    r = e.executa('resultat_proposta', {'apartat': apartat})
    assert r['ok'], r
    esperat = dict(informe)
    if apartat == '5.4':
        from nivell2.readmes import NOTA_GRAU_NOU
        esperat['motius'] = {'sessions_grau_nou_fora_franja': NOTA_GRAU_NOU}
    if apartat == '5.3':
        esperat['imprevistos'] = e.imprevistos_53()['resultat']
    assert r['resultat'] == esperat
    assert 'resum.json' not in r['consulta']
    assert r['id_sessio'] == []


def test_resultat_amb_resum_opcional(paquet):
    carpeta = e.nb.RESULTATS_PRINCIPAL / '5.2'
    resum = {'incompliments_no_declarats': 0, 'resposta': 1}
    (carpeta / 'resum.json').write_text(json.dumps(resum))
    r = e.executa('resultat_proposta', {'apartat': '5.2'})
    assert r['ok'], r
    assert r['resultat']['resum'] == resum
    assert 'resum.json' in r['consulta']


@pytest.mark.parametrize('grup', ['81', 'TE/81', '811'])
def test_horari_sense_titulacio_ni_curs(paquet, monkeypatch, grup):
    b, _ = paquet
    b = copy.deepcopy(b)
    for sid in ('S1', 'S2'):
        s = copy.deepcopy(b.sessions[sid])
        s.id = 'ALT' + sid
        s.cohorts = ('GYY:2n',)
        b.sessions[s.id] = s
    monkeypatch.setattr(e.nb, 'carrega_oficial', lambda *a, **kw: copy.deepcopy(b))
    r = e.executa('horari_grup', {'grup': grup, 'dia': 'lunes'})
    assert r['ok'], r
    assert r['resultat']['total'] == 4
    assert [(h['titulacio'], h['curs']) for h in r['resultat']['horaris']] == [('GXX', '3r'), ('GYY', '2n')]
    assert set(r['id_sessio']) == {'S1', 'S2', 'ALTS1', 'ALTS2'}
    r = e.executa('horari_grup', {'grup': grup, 'titulacio': 'GYY'})
    assert r['resultat']['total'] == 2
    r = e.executa('horari_grup', {'grup': grup, 'curs': '3r'})
    assert r['resultat']['total'] == 2
    definition = next(d['function'] for d in e.EINES if d['function']['name'] == 'horari_grup')
    assert definition['parameters']['required'] == ['grup']


@pytest.mark.parametrize('noms,codi', [
    (['L', 'dilluns', 'lunes', 'monday'], 'L'),
    (['M', 'dimarts', 'martes', 'tuesday'], 'M'),
    (['X', 'dimecres', 'miércoles', 'miercoles', 'wednesday'], 'X'),
    (['J', 'dijous', 'jueves', 'thursday'], 'J'),
    (['V', 'divendres', 'viernes', 'friday'], 'V'),
])
def test_dies_multilingues(paquet, noms, codi):
    for nom in noms:
        for variant in (nom.lower(), nom.upper()):
            assert e._dia(variant) == codi
            r = e.executa('aules_lliures', dict(dia=variant, hora_ini='16', durada_min=60, places_min=20, tipus='Seminaris'))
            assert r['ok'], r
            r = e.executa('ocupacio_aula', dict(aula='Q9/0001', dia=variant))
            assert r['ok'], r
            r = e.executa('horari_grup', dict(grup='81', dia=variant))
            assert r['ok'], r


@pytest.mark.parametrize('hora', ['16', '16:00', '16.00', '16h'])
def test_formats_hora(paquet, hora):
    r = e.executa('aules_lliures', dict(dia='monday', hora_ini=hora, durada_min=60, places_min=20, tipus='Seminaris'))
    assert r['ok'], r
    assert r['resultat']['total'] == 2
    assert all(a['h_ini'] == '16:00' for a in r['resultat']['files'])
    r = e.executa('prova_canvi', dict(apartat='5.2', canvi={'tipus': 'moure', 'id_sessio': 'S1', 'dia': 'MARTES', 'hora_ini': hora}))
    assert r['ok'], r
    assert r['resultat']['canvis'][0]['despres']['h_ini'] == '16:00'
    assert r['resultat']['canvis'][0]['despres']['dia'] == 'M'


def test_horaris_limit_global(paquet, monkeypatch):
    b, _ = paquet
    b = copy.deepcopy(b)
    for i in range(60):
        s = copy.deepcopy(b.sessions['S1'])
        s.id = f'EXTRA{i}'
        s.cohorts = ('GYY:2n',)
        b.sessions[s.id] = s
    monkeypatch.setattr(e.nb, 'carrega_oficial', lambda *a, **kw: copy.deepcopy(b))
    r = e.executa('horari_grup', {'grup': '81'})
    assert r['ok'], r
    assert r['resultat']['total'] == 62
    assert sum(len(h['files']) for h in r['resultat']['horaris']) == 50
    assert len(r['id_sessio']) == 50


@pytest.mark.parametrize('hora', ['24', '16:60', '16.99', '-1', 'demà'])
def test_hores_invalides(paquet, hora):
    r = e.executa('aules_lliures', dict(dia='L', hora_ini=hora, durada_min=60, places_min=20))
    assert not r['ok']


def test_metadades_xifres_sense_calcular(monkeypatch):
    from types import SimpleNamespace
    from nivell1 import troballes
    def prohibit(*a, **kw):
        pytest.fail('Les metadades no han de calcular ni llegir dades')
    moduls = [SimpleNamespace(ID='fora-torn', calcula=prohibit),
              SimpleNamespace(ID='inventada', TITOL='Pregunta inventada', calcula=prohibit)]
    monkeypatch.setattr(troballes, 'moduls', lambda: moduls)
    monkeypatch.setattr(e.dades, 'connexio', prohibit)
    ids, desc = e._metadades_xifres()
    assert ids == ['fora-torn', 'inventada']
    assert desc.startswith("Només l'horari d'avui (part 1), mai d'una proposta.")
    assert 'fora-torn: quantes sessions són al torn equivocat' in desc
    assert '\ninventada: Pregunta inventada' in desc


def test_definicions_xifra_i_sql():
    from nivell1 import troballes
    defs = {d['function']['name']: d['function'] for d in e.EINES}
    assert defs['xifra']['parameters']['properties']['id']['enum'] == [m.ID for m in troballes.moduls()]
    for m in troballes.moduls():
        assert f'\n{m.ID}:' in defs['xifra']['description']
    sql = defs['consulta_sql']['description']
    for vista, columnes in e._COLUMNES_SQL.items():
        assert f'{vista}: {columnes}' in sql
    assert "el torn d'una sessió es dedueix de h_ini (abans de 14.30 matí); torn_requerit és el que li toca" in sql


def test_error_duckdb_util_i_retallat(paquet):
    r = e.executa('consulta_sql', {'sql': 'SELECT columna_inventada FROM sessions'})
    assert not r['ok']
    assert 'Binder Error' in r['error']
    assert 'columna_inventada' in r['error']
    assert len(r['error']) <= 300
    r = e.executa('consulta_sql', {'sql': 'SELECT columna_' + 'x'*400 + ' FROM sessions'})
    assert not r['ok'] and len(r['error']) == 300


def test_error_conversio_no_exposa_valors(paquet):
    r = e.executa('consulta_sql', {'sql': 'SELECT CAST(id_sessio AS INTEGER) FROM sessions'})
    assert not r['ok']
    assert 'Conversion Error' in r['error']
    assert 'S0' not in r['error']


@pytest.mark.parametrize('dia', ['dimecres', 'DIMECRES', 'Miércoles', 'miercoles', 'wednesday', 'WEDNESDAY'])
def test_sql_normalitza_dia_i_retorn_consulta(paquet, dia):
    con = e.dades.connexio()
    con.execute("ALTER TABLE sessions ADD COLUMN dia VARCHAR DEFAULT 'X'")
    sql = "SELECT count(*) AS n FROM sessions WHERE dia = 'X'"
    esperat = e.executa('consulta_sql', {'sql': sql})
    r = e.executa('consulta_sql', {'sql': sql.replace("'X'", f"'{dia}'")})
    assert esperat['ok'] and r['ok'], r
    assert r['resultat'] == esperat['resultat']
    assert r['resultat']['files'][0]['n'] == 65
    assert r['consulta'] == sql


def test_normalitza_nomes_literals_exactes():
    sql = '''SELECT 'Miércoles', 'MONDAY', 'dimarts', 'jueves', 'divendres',
        ' dimecres', 'dimecres ', 'cada dimecres', 'dimecres''s', 'X', 'x',
        "dimecres", "'wednesday'", $$'monday'$$, $dia$'martes'$dia$
        /* 'lunes' /* 'martes' */ 'dilluns' */ -- 'friday'
    '''
    esperat = sql.replace("'Miércoles'", "'X'").replace("'MONDAY'", "'L'").replace("'dimarts'", "'M'").replace("'jueves'", "'J'").replace("'divendres'", "'V'")
    assert e._normalitza_dies_sql(sql) == esperat
    assert e._normalitza_dies_sql("SELECT 'dimarts', 'dimecres', 'viernes'") == "SELECT 'M', 'X', 'V'"


def test_descripcio_sql_format_dia_hora():
    desc = next(d['function']['description'] for d in e.EINES if d['function']['name'] == 'consulta_sql')
    assert "dia: L, M, X, J o V (X = dimecres); h_ini 'HH:MM'; ini_min = minuts des de mitjanit" in desc


@pytest.mark.parametrize('setmana', [None, '', ' ', 'típica', 'tipica', 'típica del semestre', 'typical', 'normal', 'TÍPICA'])
def test_setmana_tipica_formats(paquet, setmana):
    calls = [('horari_grup', {'grup': '81'}),
             ('ocupacio_aula', {'aula': 'Q9/0001'}),
             ('aules_lliures', {'dia': 'L', 'hora_ini': '16', 'durada_min': 60, 'places_min': 20, 'tipus': 'Seminaris'})]
    for nom, args in calls:
        esperat = e.executa(nom, args)
        r = e.executa(nom, dict(args, setmana=setmana))
        assert esperat['ok'] and r['ok'], r
        assert r['resultat'] == esperat['resultat']


@pytest.mark.parametrize('setmana', [7, '7', 'W07', 'setmana 7', '2027-W07', '2027-02-17'])
def test_setmana_numero_i_data(paquet, setmana):
    assert e._setmana(paquet[0], setmana) == dt.date(2027, 2, 15)
    for nom, args in [('horari_grup', {'grup': '81'}), ('ocupacio_aula', {'aula': 'Q9/0001'}),
                      ('aules_lliures', {'dia': 'L', 'hora_ini': '16', 'durada_min': 60, 'places_min': 20, 'tipus': 'Seminaris'})]:
        r = e.executa(nom, dict(args, setmana=setmana))
        esperat = e.executa(nom, dict(args, setmana='2027-W07'))
        assert r['ok'] and esperat['ok'], r
        assert r['resultat'] == esperat['resultat']


@pytest.mark.parametrize('setmana', ['xyz', 'W00', 'W54', '2027-W53', '2027-02-30', True, [], 7.5])
def test_setmana_error_especific(paquet, setmana):
    for nom, args in [('horari_grup', {'grup': '81'}), ('ocupacio_aula', {'aula': 'Q9/0001'}),
                      ('aules_lliures', {'dia': 'L', 'hora_ini': '16', 'durada_min': 60, 'places_min': 20})]:
        r = e.executa(nom, dict(args, setmana=setmana))
        assert not r['ok']
        assert 'setmana' in r['error'] and '2027-W07' in r['error']


@pytest.mark.parametrize('nom,args,parametre,acceptat', [
    ('horari_grup', {'grup': '81', 'dia': 'dissabte'}, 'dia', 'L, M, X, J o V'),
    ('ocupacio_aula', {'aula': 'Q9/0001', 'dia': 'xyz', 'setmana': '2027-W07'}, 'dia', 'L, M, X, J o V'),
    ('horari_grup', {'grup': 'xyz'}, 'grup', 'TE/81'),
    ('horari_grup', {'grup': '999'}, 'grup', 'existent'),
    ('horari_grup', {'grup': '81', 'proposta': 'xyz'}, 'proposta', 'avui'),
    ('horari_grup', {'grup': '81', 'titulacio': 'xyz'}, 'titulacio', 'codi'),
    ('horari_grup', {'grup': '81', 'curs': []}, 'curs', '1r'),
    ('ocupacio_aula', {'aula': 'xyz'}, 'aula', 'inventari'),
    ('aules_lliures', {'dia': 'L', 'hora_ini': 'xyz', 'durada_min': 60, 'places_min': 20}, 'hora_ini', '16:00'),
    ('aules_lliures', {'data': 'xyz', 'hora_ini': '16', 'durada_min': 60, 'places_min': 20}, 'data', 'AAAA-MM-DD'),
    ('aules_lliures', {'dia': 'L', 'hora_ini': '16', 'durada_min': -1, 'places_min': 20}, 'durada_min', 'enter positiu'),
    ('aules_lliures', {'dia': 'L', 'hora_ini': '16', 'durada_min': 60, 'places_min': -1}, 'places_min', 'enter'),
    ('aules_lliures', {'dia': 'L', 'hora_ini': '16', 'durada_min': 60, 'places_min': 20, 'tipus': []}, 'tipus', 'inventari'),
    ('horari_grup', {}, 'grup', 'paràmetres'),
])
def test_parametres_errors_especifics(paquet, nom, args, parametre, acceptat):
    r = e.executa(nom, args)
    assert not r['ok']
    assert parametre in r['error'] and acceptat in r['error']
    assert 'No s’ha pogut completar' not in r['error']


@pytest.mark.parametrize('canvi,camp', [
    ({'tipus': 'imprevist', 'aules_tancades': 'xyz'}, 'aules_tancades'),
    ({'tipus': 'imprevist', 'sessions_cancel_lades': [{}]}, 'id_sessio'),
    ({'tipus': 'moure', 'id_sessio': 'xyz', 'hora_ini': '16'}, 'id_sessio'),
])
def test_canvi_errors_parametres(paquet, canvi, camp):
    r = e.executa('prova_canvi', {'apartat': '5.2', 'canvi': canvi})
    assert not r['ok'] and camp in r['error']
    assert 'No s’ha pogut completar' not in r['error']


def test_descripcio_setmana_i_error_inesperat(monkeypatch):
    for definicio in e.EINES:
        setmana = definicio['function']['parameters']['properties'].get('setmana')
        if setmana:
            assert setmana['description'] == "buit o 'típica' = setmana típica; o 2027-W07; o una data"
            assert 'integer' in setmana['type']
    def falla(grup):
        raise RuntimeError('Error intern inventat')
    monkeypatch.setitem(e._HANDLERS, 'horari_grup', falla)
    r = e.executa('horari_grup', {'grup': '81'})
    assert not r['ok'] and 'No s’ha pogut completar' in r['error']


@pytest.mark.parametrize('literal', ['típica', 'tipica', 'typical', 'setmana típica', 'TÍPICA', 'TYPICAL', 'SETMANA TIPICA'])
def test_sql_setmana_tipica_literal(paquet, literal):
    con = e.dades.connexio()
    con.execute("ALTER TABLE sessions ADD COLUMN setmana VARCHAR DEFAULT '2027-W06'")
    con.execute("UPDATE sessions SET setmana = '2027-W07' WHERE id_sessio = 'S0'")
    sql = "SELECT count(*) AS n FROM sessions WHERE setmana = '2027-W06'"
    esperat = e.executa('consulta_sql', {'sql': sql})
    r = e.executa('consulta_sql', {'sql': sql.replace("'2027-W06'", f"'{literal}'")})
    assert r['ok'] and esperat['ok'], r
    assert r['resultat'] == esperat['resultat']
    assert r['resultat']['files'][0]['n'] == 64
    assert r['consulta'] == sql
    assert e._setmana(paquet[0], None).strftime('%G-W%V') in r['consulta']


def test_normalitzacio_setmana_mandrosa_i_exacta(paquet, monkeypatch):
    carrega = e.nb.carrega_oficial
    crides = []
    def compta():
        crides.append(True)
        return carrega()
    monkeypatch.setattr(e.nb, 'carrega_oficial', compta)
    sql = '''SELECT 'setmana típica extra', ' típica', 'típica ', "'típica'", $$'typical'$$
        /* 'típica' */ -- 'tipica'
    '''
    assert e._normalitza_dies_sql(sql) == sql
    assert crides == []
    assert e._normalitza_dies_sql("SELECT 'típica', 'setmana típica', 'dimecres'") == "SELECT '2027-W06', '2027-W06', 'X'"
    assert len(crides) == 1


def test_descripcio_sql_setmana_tipica():
    desc = next(d['function']['description'] for d in e.EINES if d['function']['name'] == 'consulta_sql')
    assert "per a la setmana típica, filtra setmana = 'típica' (es tradueix sol)" in desc
    assert 'Sense filtre de setmana ni semestre es compta tot el curs' in desc


def test_recomptes_abans_limit_i_per_cohort(paquet, monkeypatch):
    from dataclasses import replace
    graella = e._modul('components.graella')
    cella = graella.celles(paquet[0], paquet[1], dt.date(2027, 2, 8), cohort='GXX:3r', linia=paquet[0].sessions['S1'].linia)[0]
    rows = [replace(cella, id_sessio=f'I{i}', aula='Q9/0001' if i < 2 else '') for i in range(59)]
    for fila in rows:
        paquet[0].sessions[fila.id_sessio] = replace(paquet[0].sessions['S1'], id=fila.id_sessio)
    monkeypatch.setattr(graella, 'celles', lambda *a, **kw: rows)
    r = e.executa('horari_grup', {'grup': '81'})['resultat']
    assert len(r['horaris'][0]['files']) == 50
    assert r['recomptes'] == {'total_sessions': 59, 'amb_aula': 2, 'sense_aula': 57,
        'per_titulacio_curs': [{'titulacio': 'GXX', 'curs': '3r', 'total_sessions': 59, 'amb_aula': 2, 'sense_aula': 57}]}
    assert e._recomptes_sessions(e._json(rows[:9])) == {'total_sessions': 9, 'amb_aula': 2, 'sense_aula': 7}


def test_recomptes_ocupacio_i_aules(paquet):
    r = e.executa('ocupacio_aula', {'aula': 'Q9/0001'})['resultat']
    assert r['recomptes']['total_sessions'] == 2
    assert r['recomptes']['amb_aula'] == 2
    assert r['recomptes']['sense_aula'] == 0
    r = e.executa('aules_lliures', {'dia': 'L', 'hora_ini': '17', 'durada_min': 60,
                                  'places_min': 0, 'tipus': 'Seminaris'})['resultat']
    assert r['recomptes']['total_aules'] == 3


@pytest.mark.parametrize('alias,canonical', [
    ('SEMÁNA', 'setmana'), ('week', 'setmana'), ('DÍA', 'dia'), ('day', 'dia'),
    ('hora', 'hora_ini'), ('hour', 'hora_ini'), ('inici', 'hora_ini'),
    ('duracion', 'durada_min'), ('DURACIÓN', 'durada_min'), ('duration', 'durada_min'), ('minuts', 'durada_min'),
    ('plazas', 'places_min'), ('places', 'places_min'), ('capacitat', 'places_min'),
    ('capacity', 'places_min'), ('seats', 'places_min'), ('propuesta', 'proposta'), ('proposal', 'proposta'),
    ('titulación', 'titulacio'), ('titulacion', 'titulacio'), ('degree', 'titulacio'),
    ('group', 'grup'), ('grupo', 'grup'), ('AULA', 'aula'), ('room', 'aula'), ('sala', 'aula'),
])
def test_alias_parametres(alias, canonical):
    assert e._normalitza_parametres({alias: 'valor'}) == {canonical: 'valor'}


def test_alias_executa_i_desconeguts(paquet):
    r = e.executa('aules_lliures', {'día': 'lunes', 'hora': '9', 'duración': 60,
        'plazas': 0, 'semana': '2027-W06', 'propuesta': 'avui', 'extra': True})
    assert r['ok'], r
    assert e.executa('ocupacio_aula', {'ROOM': 'Q9/0001', 'DAY': 'Monday'})['ok']
    assert e.executa('horari_grup', {'GROUP': '81', 'TITULACIÓN': 'GXX'})['ok']
    r = e.executa('ocupacio_aula', {'ignorat': 'x'})
    assert not r['ok'] and 'aula' in r['error']
    for args in ({'grup': '81', 'grupo': '82'}, {'grupo': '82', 'grup': '81'}):
        assert e._normalitza_parametres(args) == {'grup': '81'}


def test_simulacio_context_oficial_i_alias_nested(paquet):
    path = e.nb.RESULTATS_PRINCIPAL / '5.2' / 'informe.json'
    verdict = 'VALIDA AMB RELAXACIONS DECLARADES'
    path.write_text(json.dumps({'veredicte': verdict}))
    r = e.executa('prova_canvi', {'APARTAT': '5.2', 'CANVI': {
        'tipus': 'moure', 'id_sessio': 'S1', 'HOUR': '15:00'}})
    assert r['ok'], r
    result = r['resultat']
    assert result['aplicat'] is False and result['desat'] is False
    assert result['veredicte_oficial'] == verdict
    assert verdict in result['nota_validacio']
    assert 'sense les relaxacions declarades' in result['nota_validacio']
    assert result['total_incompliments_nous'] == 0


@pytest.mark.parametrize('sql,abast', [
    ('SELECT count(*) FROM sessions', 'tot el curs (els dos semestres)'),
    ("SELECT 'setmana', '2027-W07', 'sem = 2'", 'tot el curs (els dos semestres)'),
    ('SELECT 1 /* WHERE sem = 2 */', 'tot el curs (els dos semestres)'),
    ("SELECT count(*) FROM sessions WHERE setmana = '2027-W06'", 'setmana 2027-W06'),
    ('SELECT count(*) FROM sessions WHERE sem = 2', '2n semestre'),
    ('SELECT count(*) FROM sessions WHERE sem = 1', '1r semestre'),
])
def test_sql_abast(paquet, sql, abast):
    con = e.dades.connexio()
    con.execute("ALTER TABLE sessions ADD COLUMN setmana VARCHAR DEFAULT '2027-W06'")
    con.execute('ALTER TABLE sessions ADD COLUMN sem INTEGER DEFAULT 2')
    r = e.executa('consulta_sql', {'SQL': sql})
    assert r['ok'], r
    assert r['resultat']['abast'] == abast


def test_descripcions_recomptes():
    for definicio in e.EINES:
        f = definicio['function']
        if f['name'] in ('horari_grup', 'ocupacio_aula', 'aules_lliures'):
            assert 'fes servir `recomptes` per a qualsevol número' in f['description'].lower()


# Regressions de l’auditoria: totes les files següents són inventades.
@pytest.mark.parametrize('funcio', ['CURRENT_DATE', 'current_timestamp', 'now()', 'today()'])
def test_b1_sql_rebutja_rellotge(paquet, funcio):
    r = e.executa('consulta_sql', {'sql': f'SELECT count(*) FROM sessions WHERE data = {funcio}'})
    assert r == {'ok': False, 'error': 'avui = horari de partida; no filtris per la data del sistema'}


def test_b1_sql_rellotge_nomes_codi(paquet):
    r = e.executa('consulta_sql', {'sql': "SELECT 'CURRENT_DATE now() today()' AS text /* current_timestamp */"})
    assert r['ok']


@pytest.mark.parametrize('torn,valor', [('matí', 'mati'), ('MATI', 'mati'), ('morning', 'mati'),
                                       ('tarda', 'tarda'), ('AFTERNOON', 'tarda')])
def test_b1_sql_torns(paquet, torn, valor):
    e.dades.connexio().execute("ALTER TABLE sessions ADD COLUMN torn_actual VARCHAR DEFAULT 'mati'")
    r = e.executa('consulta_sql', {'sql': f"SELECT count(*) AS n FROM sessions WHERE torn_actual = '{torn}'"})
    assert r['ok']
    assert r['resultat']['files'][0]['n'] == (65 if valor == 'mati' else 0)
    assert f"'{valor}'" in r['consulta']


def test_b1_sql_abast_propostes_i_anuals(paquet):
    e.dades.connexio().execute("ALTER TABLE sessions ADD COLUMN semestre VARCHAR DEFAULT 'C/2'")
    for sql, abast in [
        ("SELECT count(*) FROM proposta_5_2 WHERE h_ini >= '14:30'", '2n semestre'),
        ('WITH p AS (SELECT * FROM proposta_5_2) SELECT count(*) FROM p', '2n semestre'),
        ("SELECT count(*) FROM sessions WHERE semestre = 'C/2'", 'assignatures C/2, sense les anuals'),
        ('SELECT count(*) FROM proposta_5_2 CROSS JOIN sessions', 'tot el curs (els dos semestres)'),
    ]:
        r = e.executa('consulta_sql', {'sql': sql})
        assert r['ok'], r
        assert r['resultat']['abast'] == abast
    assert 'aula_partida NULL = sessió sense aula' in e._DESCRIPCIO_SQL
    assert 'no vol dir sense aula' in e._DESCRIPCIO_SQL
    assert 'sessions sense aula: quantes' in e._DESCRIPCIO_XIFRA


def test_b3_aules_tancades_i_ocupacio(paquet):
    from horaris.model import Tancament
    b, _ = paquet
    b.tancaments.append(Tancament('Q9/0003', dt.date(2027, 2, 8), dt.date(2027, 2, 10)))
    r = e.executa('aules_lliures', dict(data='2027-02-08', hora_ini='15', durada_min=60,
                                      places_min=0, tipus='Seminaris', proposta='5.3'))
    assert r['ok'] and r['resultat']['total'] == 0
    r = e.executa('ocupacio_aula', dict(aula='Q9/0003', proposta='5.3'))
    assert r['ok']
    assert r['resultat']['tancada'] == ['2027-02-08', '2027-02-09', '2027-02-10']
    r = e.executa('ocupacio_aula', dict(aula='Q9/0003', dia='X', proposta='5.3'))
    assert r['resultat']['tancada'] == ['2027-02-10']


def test_b13_reserva_total_sense_filtre_places_i_limit(paquet):
    b, _ = paquet
    for i in range(7):
        aula = f'Q9/1{i:03}'
        b.aules[aula] = Aula(aula, 'Q9', 'Aules docents', 30+i*10)
    r = e.executa('aules_lliures', dict(dia='L', hora_ini='15', durada_min=60, places_min=40))
    assert r['ok']
    resultat = r['resultat']
    assert resultat['recomptes'] == {'total_aules': 6, 'ordinaries_lliures': 7,
        'respecta_reserva': True, 'sessions_sense_aula_a_la_franja': 0}
    assert len(resultat['files']) == 5
    assert [a['capacitat'] for a in resultat['files']] == [40, 50, 60, 70, 80]
    for aula in list(b.aules):
        if aula.startswith('Q9/1') and aula not in ('Q9/1000', 'Q9/1001'):
            del b.aules[aula]
    r = e.executa('aules_lliures', dict(dia='L', hora_ini='15', durada_min=60, places_min=0))
    assert r['resultat']['recomptes']['ordinaries_lliures'] == 2
    assert r['resultat']['recomptes']['respecta_reserva'] is False
    assert all(a['respecta_reserva'] is False for a in r['resultat']['files'])


def test_b13_demanda_sense_aula_i_dates(paquet):
    b, _ = paquet
    b.sessions['S1'].aula = ''
    b.sessions['S2'].aula = ''
    b.sessions['S2'].sense_espai = True
    r = e.executa('aules_lliures', dict(dia='L', hora_ini='15', durada_min=120,
                                      places_min=0, tipus='Seminaris'))
    assert r['ok']
    assert r['resultat']['recomptes']['sessions_sense_aula_a_la_franja'] == 1
    for data in ('2026-10-14', '2027-02-09'):
        r = e.executa('aules_lliures', dict(data=data, hora_ini='15', durada_min=60, places_min=0))
        assert not r['ok']
        assert 'Les dades són del 2n semestre (08/02/2027–08/02/2027)' in r['error']


def test_f3_avissos_dates_i_grup(paquet):
    r = e.executa('prova_canvi', dict(apartat='5.2', canvi={
        'tipus': 'imprevist', 'sessions_cancel_lades': [
            {'id_sessio': 'S3', 'recuperar_fins': '2027-02-10'}]}))
    assert r['ok']
    resultat = r['resultat']
    assert resultat['data_avis'] == dt.date.today().isoformat()
    canvi = next(c for c in resultat['canvis'] if c['id_sessio'] == 'S3')
    assert canvi['assignatura'] == 'Assignatura inventada'
    assert canvi['grup'] == 'Grup 82 · teoria' and canvi['tipus'] == 'TE'
    assert canvi['abans']['data'] == '2027-02-08'
    assert '2027-02-08' < canvi['despres']['data'] <= '2027-02-10'
    assert canvi['abans']['h_ini'] == '15:00' and canvi['abans']['h_fi'] == '16:00'
    assert '08/02/2027' in canvi['abans']['lloc']
    assert 'Q9/' in canvi['despres']['lloc']


def test_f3_sense_proposta_explica_aforament(paquet):
    r = e.executa('prova_canvi', dict(apartat='5.2', canvi={'tipus': 'imprevist',
        'grups_creixen': [{'codi': '900001', 'grup': 'TE/81', 'alumnes': 200}]}))
    assert r['ok']
    assert r['resultat']['veredicte'] == 'SENSE PROPOSTA'
    assert '200 places' in r['resultat']['motiu'] and '60' in r['resultat']['motiu']
    assert r['resultat']['data_avis'] == dt.date.today().isoformat()


def test_d8_fixades_excepcions_no_conflictes_nous(paquet):
    b, _ = paquet
    b.sessions['S1'].fixada = 'R1: inventada'
    r = e.executa('prova_canvi', dict(apartat='5.2', canvi={'tipus': 'imprevist',
        'aules_tancades': [{'aula': 'Q9/0001', 'data_ini': '2027-02-08', 'data_fi': '2027-02-08'}]}))
    assert r['ok']
    resultat = r['resultat']
    assert resultat['total'] == 2
    assert resultat['total_incompliments_nous'] == 0
    assert resultat['nous_per_regla'] == {}
    assert resultat['veredicte'] == 'VALIDA AMB EXCEPCIONS INEVITABLES'
    assert resultat['total_excepcions_inevitables'] == 1
    assert resultat['excepcions_inevitables'][0]['declarada'] is True
    assert 'mateixa hora' in resultat['excepcions_inevitables'][0]['motiu']


def test_d8_incompliments_heretats_no_son_nous(paquet):
    b, _ = paquet
    b.sessions['S1'].torn = 'mati'
    r = e.executa('prova_canvi', dict(apartat='5.2', canvi={
        'tipus': 'moure', 'id_sessio': 'S1', 'aula': 'Q9/0003'}))
    assert r['ok']
    assert r['resultat']['veredicte_abans'] == 'NO VALIDA'
    assert r['resultat']['total_incompliments_nous'] == 0


def test_d8_regressio_escenari_oficial():
    # Executa el projecte; no imprimeix cap fila ni modifica els resultats.
    r = e.executa('prova_canvi', {'apartat': '5.2', 'canvi': {'tipus': 'imprevist',
        'aules_tancades': [{'aula': 'Q1/1003', 'data_ini': '2027-03-10', 'data_fi': '2027-03-10'}]}})
    assert r['ok'], 'La simulació oficial ha fallat; cap fila exposada.'
    resultat = r['resultat']
    assert resultat['total'] == 6
    assert resultat['total_excepcions_inevitables'] == 2
    assert resultat['total_incompliments_nous'] == 0
    assert resultat['veredicte'] == 'VALIDA AMB EXCEPCIONS INEVITABLES'


def test_b2_f2_imprevistos_de_dades_i_referencia(paquet, monkeypatch):
    from horaris.model import Tancament
    b, p52 = paquet
    contingencies = copy.deepcopy(b)
    contingencies.tancaments.append(Tancament('Q9/0001', dt.date(2027, 2, 8), dt.date(2027, 2, 8)))
    contingencies.sessions['S1'].alumnes = 55
    contingencies.cancellades['S3'] = dt.date(2027, 2, 10)
    # L’aula de referència 5.2 difereix de l’horari de partida.
    p52.files['S2'].aula = 'Q9/0002'
    p52.escriu(e.nb.RESULTATS_PRINCIPAL/'5.2'/'proposta.csv')
    p53 = copy.deepcopy(p52)
    p53.files['S1'].aula = 'Q9/0003'
    p53.files['S3'].dia = 'M'
    p53.files['S3'].data = '2027-02-09'
    p53.escriu(e.nb.RESULTATS_PRINCIPAL/'5.3'/'proposta.csv')
    monkeypatch.setattr(e.nb, 'carrega_oficial', lambda escenari=None: copy.deepcopy(
        contingencies if escenari == e.nb.CONTINGENCIES else b))
    r = e.executa('imprevistos_53', {})
    assert r['ok']
    resultat = r['resultat']
    assert resultat['aules_tancades'][0]['total'] == 1
    sessio = resultat['aules_tancades'][0]['sessions'][0]
    assert sessio['id_sessio'] == 'S1' and sessio['assignatura'] == 'Assignatura inventada'
    assert sessio['abans']['aula'] == 'Q9/0001' and sessio['despres']['aula'] == 'Q9/0003'
    assert resultat['alumnes'][0]['alumnes_abans'] == 20
    assert resultat['alumnes'][0]['alumnes'] == 55
    assert resultat['cancellades'][0]['sessions'][0]['despres']['data'] == '2027-02-09'
    assert e.executa('resultat_proposta', {'apartat': '5.3'})['resultat']['imprevistos'] == resultat


@pytest.mark.parametrize('apartat', e.APARTATS)
def test_b3_d6_xifres_csv_de_cada_proposta(paquet, apartat):
    # Xifres inventades diferents per proposta: no s’han de prendre d’avui ni del resum.
    carpeta = e.nb.RESULTATS_PRINCIPAL / apartat
    n = e.APARTATS.index(apartat) + 7
    (carpeta / 'xifres.csv').write_text(
        f'xifra,abans,despres\nveredicte,NO VALIDA,VALIDA\ncanvis_torn,0,{n}\n'
        'heretats:R1-TORN,12,3\ndeclarats:R1-TORN,0,3\ncanvis_franja,0,9\n'
        'canvis_aula,0,11\nactivitats_rutinaries_pct,90.5,95.25\n', encoding='utf-8')
    r = e.executa('resultat_proposta', {'apartat': apartat})
    assert r['ok'], r
    xifres = {f['xifra']: (f['abans'], f['despres']) for f in r['resultat']['xifres']}
    assert xifres['canvis_torn'] == (0, n)
    assert xifres['veredicte'] == ('NO VALIDA', 'VALIDA')
    assert xifres['heretats:R1-TORN'] == (12, 3)
    assert xifres['activitats_rutinaries_pct'] == (90.5, 95.25)
    assert 'xifres.csv' in r['consulta']
    if apartat == '5.4':
        motiu = r['resultat']['motius']['sessions_grau_nou_fora_franja']
        assert '1.740' in motiu and 'PAUL/91' in motiu and '0 sessions mogudes' in motiu


def test_b3_d6_xifra_nomes_avui(paquet, monkeypatch):
    from nivell1 import troballes
    import pandas as pd
    t = troballes.Troballa('inventada', 'Prova', '1', 'Una classe', 'Recompte', 'SELECT 1', pd.DataFrame())
    monkeypatch.setattr(troballes, 'moduls', lambda: [type('Modul', (), {'ID': 'inventada'})])
    monkeypatch.setattr(troballes, 'una', lambda *a: t)
    assert 'no és cap proposta' in e.xifra('inventada')['resultat']['abast']
    assert "mai d'una proposta" in e._DESCRIPCIO_XIFRA


def test_b3_d6_sql_torn_actual_proposta(paquet):
    b, p = paquet
    b.sessions['N90001'] = copy.deepcopy(b.sessions['S1'])
    b.sessions['N90001'].id = 'N90001'
    p.files['N90001'] = copy.deepcopy(p.files['S1'])
    p.files['N90001'].h_ini = '08:30'
    p.escriu(e.nb.RESULTATS_PRINCIPAL / '5.4' / 'proposta.csv')
    r = e.consulta_sql("SELECT torn_actual, count(*) AS n FROM proposta_5_4 WHERE id_sessio LIKE 'N%' GROUP BY torn_actual")
    assert r['ok']
    assert r['resultat']['files'] == [{'torn_actual': 'mati', 'n': 1}]


def test_f3_b8_aforament_no_crida_solver(paquet, monkeypatch):
    import nivell2.reparacio as reparacio
    def prohibit(*args, **kwargs):
        pytest.fail('Un creixement superior a qualsevol aula no ha de cridar el solver')
    monkeypatch.setattr(reparacio, 'repara', prohibit)
    r = e.executa('prova_canvi', {'apartat': '5.2', 'canvi': {'tipus': 'imprevist',
        'grups_creixen': [{'codi': '900001', 'grup': 'TE/81', 'alumnes': 200}]}})
    assert r['ok']
    assert r['resultat']['estat'] == 'INFEASIBLE'
    assert '200 places' in r['resultat']['motiu'] and '60' in r['resultat']['motiu']


def test_f3_diagnostic_aforament_en_intent_anterior(paquet, monkeypatch):
    import nivell2.reparacio as reparacio
    monkeypatch.setattr(reparacio, 'repara', lambda *a: reparacio.Reparacio(None, 'UNKNOWN',
        {'intents': [{'diagnostic': {'alumnes': 50, 'aules_amb_aforament': 0}}, {'diagnostic': {}}]}))
    r = e.executa('prova_canvi', {'apartat': '5.2', 'canvi': {'tipus': 'imprevist',
        'grups_creixen': [{'codi': '900001', 'grup': 'TE/81', 'alumnes': 50}]}})
    assert r['ok'] and '50 places' in r['resultat']['motiu']
    assert 'temps' not in r['resultat']['motiu']


def test_f3_recuperacio_pressupost_30_segons(paquet, monkeypatch):
    import nivell2.reparacio as reparacio
    pressupostos = []
    original = reparacio.repara
    def repara(p, canvi):
        pressupostos.append(canvi.temps_s)
        return original(p, canvi)
    monkeypatch.setattr(reparacio, 'repara', repara)
    r = e.executa('prova_canvi', {'apartat': '5.2', 'canvi': {'tipus': 'imprevist',
        'sessions_cancel_lades': [{'id_sessio': 'S3', 'recuperar_fins': '2027-02-10'}]}})
    assert r['ok'] and r['resultat']['total'] > 0
    assert pressupostos == [30]


@pytest.mark.parametrize('tipus', ['seminari', 'seminaris', 'SEMINARIS', 'Seminaris'])
def test_b8_tipus_singular_i_minuscules(paquet, tipus):
    r = e.executa('aules_lliures', {'dia': 'L', 'hora_ini': '17', 'durada_min': 60,
        'places_min': 0, 'tipus': tipus})
    assert r['ok'] and r['resultat']['total'] == 3


def test_b8_resol_nom_assignatura_i_error_codi(paquet):
    r = e.executa('prova_canvi', {'apartat': '5.2', 'canvi': {'tipus': 'imprevist',
        'grups_creixen': [{'codi': 'Assignatura inventada', 'grup': 'TE/81', 'alumnes': 30}]}})
    assert r['ok'], r
    r = e.executa('prova_canvi', {'apartat': '5.2', 'canvi': {'tipus': 'imprevist',
        'grups_creixen': [{'codi': 'TE', 'grup': 'TE/81', 'alumnes': 30}]}})
    assert not r['ok']
    assert 'el grup TE/81 existeix' in r['error'] and '900001 (Assignatura inventada)' in r['error']


def test_f20_tancament_per_hores(paquet):
    r = e.executa('prova_canvi', {'apartat': '5.2', 'canvi': {'tipus': 'imprevist',
        'aules_tancades': [{'aula': 'Q9/0001', 'data_ini': '2027-02-08', 'data_fi': '2027-02-08',
                            'hora_ini': '15', 'hora_fi': '16'}]}})
    assert r['ok'], r
    assert r['resultat']['total'] == 1
    assert r['resultat']['canvis'][0]['id_sessio'] == 'S1'


@pytest.mark.parametrize('hores,camp', [
    ({'hora_ini': 'xyz', 'hora_fi': '12'}, 'hora_ini'),
    ({'hora_ini': '12', 'hora_fi': 'xyz'}, 'hora_fi'),
    ({'hora_ini': '12', 'hora_fi': '10'}, 'hora_fi'),
    ({'hora_ini': '12', 'hora_fi': '12'}, 'hora_fi'),
])
def test_f20_hores_invalides(paquet, hores, camp):
    r = e.executa('prova_canvi', {'apartat': '5.2', 'canvi': {'tipus': 'imprevist',
        'aules_tancades': [{'aula': 'Q9/0001', 'data_ini': '2027-02-08', 'data_fi': '2027-02-08', **hores}]}})
    assert not r['ok'] and camp in r['error']


def test_d8_horari_identifica_activitat_per_moure(paquet):
    r = e.executa('horari_grup', {'grup': '81'})
    assert r['ok']
    activitat = r['resultat']['horaris'][0]['files'][0]['activitat_id']
    assert activitat == 'A1'
    r = e.executa('prova_canvi', {'apartat': '5.2', 'canvi': {
        'tipus': 'moure', 'activitat_id': activitat, 'hora_ini': '17'}})
    assert r['ok'] and r['resultat']['total'] == 2


def test_f12_d7_classes_suport_i_motiu(paquet, monkeypatch):
    b, p52 = paquet
    contingencies = copy.deepcopy(b)
    contingencies.sessions['S3'].alumnes = 55
    p53 = copy.deepcopy(p52)
    p53.files['S3'].aula = 'Q9/0001'
    p53.files['S1'].aula = 'Q9/0003'
    p53.escriu(e.nb.RESULTATS_PRINCIPAL / '5.3' / 'proposta.csv')
    monkeypatch.setattr(e.nb, 'carrega_oficial', lambda escenari=None: copy.deepcopy(
        contingencies if escenari == e.nb.CONTINGENCIES else b))
    r = e.imprevistos_53()['resultat']
    assert r['classes_de_suport']['total'] == 1
    fila = r['classes_de_suport']['sessions'][0]
    assert fila['id_sessio'] == 'S1'
    assert fila['per_fer_lloc_a'][0]['id_sessio'] == 'S3'
    assert 'Assignatura inventada' in fila['motiu'] and 'Grup 82' in fila['motiu']
    assert 'Un grup de teoria creix' in fila['motiu']


def test_d7_distingeix_reserva_i_avaria(paquet):
    from horaris.model import Tancament
    b, _ = paquet
    b.tancaments.extend([
        Tancament('Q9/0001', dt.date(2027, 2, 8), dt.date(2027, 2, 8)),
        Tancament('Q9/0002', dt.date(2027, 2, 8), dt.date(2027, 2, 12))])
    tancaments = e.imprevistos_53()['resultat']['aules_tancades']
    assert [t['tipus'] for t in tancaments] == ['avaria', 'reserva per a un acte']
    assert all(t['descripcio'] for t in tancaments)


def test_auditoria_xifres_i_demo_oficials():
    # Només veredictes i recomptes; cap fila real en un missatge d’error.
    r = e.executa('resultat_proposta', {'apartat': '5.2'})
    assert r['ok'], 'No s’han pogut consultar les xifres oficials.'
    canvis_torn = next(f['despres'] for f in r['resultat']['xifres'] if f['xifra'] == 'canvis_torn')
    assert canvis_torn == 2007
    r = e.executa('aules_lliures', {'dia': 'M', 'hora_ini': '10', 'durada_min': 60,
                                  'places_min': 0, 'proposta': '5.2'})
    assert r['ok'], 'La consulta de la demo ha fallat.'
    total = r['resultat']['recomptes']['ordinaries_lliures']
    assert total == 6
    r = e.executa('consulta_sql', {'sql': "SELECT count(*) AS total, count(*) FILTER (WHERE torn_actual = 'tarda') AS tarda FROM proposta_5_4 WHERE id_sessio LIKE 'N%'"})
    assert r['ok'], 'La consulta de torns del grau nou ha fallat.'
    total = r['resultat']['files'][0]['total']
    tarda = r['resultat']['files'][0]['tarda']
    assert total == 235 and tarda == 0


def test_f3_recuperacio_oficial():
    r = e.executa('prova_canvi', {'apartat': '5.3', 'canvi': {'tipus': 'imprevist',
        'sessions_cancel_lades': [{'id_sessio': 'S13793', 'recuperar_fins': '2027-03-26'}]}})
    assert r['ok'], 'La simulació de recuperació ha fallat.'
    total = r['resultat']['total']
    assert total > 0
    assert r['resultat']['estat'] in ('FEASIBLE', 'OPTIMAL')


def test_f12_d7_imprevistos_oficials_inclouen_suport():
    r = e.executa('imprevistos_53', {})
    assert r['ok'], 'No s’han pogut consultar els imprevistos oficials.'
    resultat = r['resultat']
    total_suport = resultat['classes_de_suport']['total']
    assert total_suport == 12
    sense_destinatari = sum(not f['per_fer_lloc_a'] for f in resultat['classes_de_suport']['sessions'])
    assert sense_destinatari == 0
    ids = {f['id_sessio'] for bloc in ('aules_tancades', 'alumnes', 'cancellades')
           for canvi in resultat[bloc] for f in canvi['sessions']}
    ids.update(f['id_sessio'] for f in resultat['classes_de_suport']['sessions'])
    total = len(ids)
    assert total == 65
