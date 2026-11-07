"""Només dades inventades, creades sota tmp_path."""
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
    con.execute("CREATE TABLE sessions AS SELECT 'S'||i AS id_sessio, DATE '2027-02-08' AS data, 900 AS ini_min, 960 AS fi_min, '' AS aules_addicionals_partida FROM range(65) t(i)")
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
    assert len(e.EINES) == 7
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
    assert r['resultat'] == informe
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
    assert desc.startswith("Primer opció per a xifres generals de l'horari d'avui (part 1).")
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
    assert 'Sense filtre de setmana es compta tot el semestre' in desc
