"""Eines de consulta i simulació: cap operació desa dades ni propostes."""
from __future__ import annotations

import copy
import dataclasses
import datetime as dt
import json
import importlib
import inspect
import math
import re
import threading
import unicodedata
from collections import Counter

from nivell1 import dades
from nivell2 import base as nb

APARTATS = ('5.1', '5.2', '5.3', '5.4')
DIES = ('L', 'M', 'X', 'J', 'V')
LIMIT = 50
TEMPS_SQL = 5


class EntradaError(ValueError):
    pass


def _json(x):
    if dataclasses.is_dataclass(x):
        return _json(dataclasses.asdict(x))
    if hasattr(x, 'to_dict'):
        return _json(x.to_dict(orient='records'))
    if isinstance(x, dict):
        return {str(k): _json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set, frozenset)):
        return [_json(v) for v in x]
    if isinstance(x, (dt.date, dt.time)):
        return x.isoformat()
    if hasattr(x, 'tolist'):
        return _json(x.tolist())
    if hasattr(x, 'item'):
        return _json(x.item())
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def _retorn(resultat, consulta, ids=None):
    resultat = _json(resultat)
    files = resultat if isinstance(resultat, list) else None
    if files is not None:
        ids = [r['id_sessio'] for r in files[:LIMIT] if isinstance(r, dict) and r.get('id_sessio')] if ids is None else ids
        resultat = {'total': len(files), 'files': files[:LIMIT]}
    return {'ok': True, 'resultat': resultat, 'id_sessio': list(dict.fromkeys(ids or []))[:LIMIT], 'consulta': consulta}


def _apartat(apartat):
    if apartat not in APARTATS:
        raise EntradaError(f'apartat {apartat!r} no vàlid: fes servir 5.1, 5.2, 5.3 o 5.4.')
    return apartat


def _carrega(proposta='avui'):
    if proposta not in ('avui', *APARTATS):
        raise EntradaError(f'proposta {proposta!r} no vàlida: fes servir avui, 5.1, 5.2, 5.3 o 5.4.')
    escenari = nb.CONTINGENCIES if proposta == '5.3' else nb.GRAU_NOU if proposta == '5.4' else None
    b = nb.carrega_oficial(escenari)
    p = nb.Proposta.de_base(b) if proposta == 'avui' else nb.Proposta.llegeix(nb.RESULTATS_PRINCIPAL / proposta / 'proposta.csv')
    if set(p.files) != set(b.sessions):
        raise EntradaError('La proposta és incompleta o conté sessions desconegudes.')
    return b, p


def _dia(dia):
    nom = ''.join(c for c in unicodedata.normalize('NFD', str(dia).strip().lower())
                  if not unicodedata.combining(c))
    noms = {nom: codi for codi, variants in zip(DIES, (
        ('l', 'dilluns', 'lunes', 'monday'),
        ('m', 'dimarts', 'martes', 'tuesday'),
        ('x', 'dimecres', 'miercoles', 'wednesday'),
        ('j', 'dijous', 'jueves', 'thursday'),
        ('v', 'divendres', 'viernes', 'friday'))) for nom in variants}
    if nom not in noms:
        raise EntradaError(f'dia {dia!r} no vàlid: fes servir L, M, X, J o V, o el nom en català, castellà o anglès.')
    return noms[nom]


def _hora(h):
    match = re.fullmatch(r'([01]?\d|2[0-3])(?:(?:[:.])([0-5]\d)|h)?', str(h).strip().lower())
    if not match:
        raise EntradaError(f'hora_ini {h!r} no vàlida: indica una hora de 00:00 a 23:59, com 16, 16:00, 16.00 o 16h.')
    return int(match[1])*60 + int(match[2] or 0)


def _modul(nom):
    return importlib.import_module(('app.' if __package__.startswith('app.') else '') + nom)


def _data(valor, parametre='data'):
    try:
        if not isinstance(valor, str):
            raise ValueError
        return dt.date.fromisoformat(valor)
    except ValueError:
        raise EntradaError(f'{parametre} {valor!r} no vàlida: fes servir una data AAAA-MM-DD, com 2027-02-15.') from None


def _setmana(b, setmana):
    graella = _modul('components.graella')
    text = str(setmana).strip().lower() if setmana is not None else ''
    normal = ''.join(c for c in unicodedata.normalize('NFD', text) if not unicodedata.combining(c))
    if normal in ('', 'tipica', 'tipica del semestre', 'typical', 'normal'):
        return graella.setmana_tipica(b)
    try:
        match = re.fullmatch(r'(\d{4})-w(\d{2})', text)
        if match:
            return dt.date.fromisocalendar(int(match[1]), int(match[2]), 1)
        numero = re.fullmatch(r'(?:w|setmana\s+)?(\d{1,2})', text)
        if numero and not isinstance(setmana, bool):
            return dt.date.fromisocalendar(2027, int(numero[1]), 1)
        return graella.dilluns(dt.date.fromisoformat(text))
    except (ValueError, TypeError):
        raise EntradaError(f"setmana {setmana!r} no vàlida: deixa-la buida o fes servir 'típica', 2027-W07, 7, W07, 'setmana 7' o una data AAAA-MM-DD.") from None


def _aula(b, aula):
    if not isinstance(aula, str) or aula not in b.aules:
        raise EntradaError(f'aula {aula!r} no vàlida: fes servir un codi exacte d’aula de l’inventari.')
    return aula


def _files(b, p):
    for sid, s in b.sessions.items():
        a = p.files[sid]
        date = dt.date.fromisoformat(a.data) if a.data else s.data - dt.timedelta(days=s.data.weekday()) + dt.timedelta(days=DIES.index(a.dia))
        ini = _hora(a.h_ini)
        yield {'id_sessio': sid, 'activitat_id': s.activitat, 'data': date, 'setmana': date.strftime('%G-W%V'),
               'dia': DIES[date.weekday()], 'h_ini': a.h_ini, 'h_fi': nb.fmt(ini+s.durada),
               'ini_min': ini, 'fi_min': ini+s.durada, 'aula': a.aula,
               'assignatura': s.codi, 'tipus': s.tipus, 'grup': s.grup}


def horari_grup(grup, titulacio=None, curs=None, dia=None, setmana=None, proposta='avui'):
    graella = _modul('components.graella')
    b, p = _carrega(proposta)
    if not isinstance(grup, (str, int)) or isinstance(grup, bool) or not re.fullmatch(r'(?:(?:TE|PAUL|SEM|PLAB)/)?\d+', str(grup).strip(), re.I):
        raise EntradaError(f'grup {grup!r} no vàlid: fes servir un grup existent com 81, TE/81 o 811.')
    cohorts = {cohort.rsplit(':', 1)[0] for sessio in b.sessions.values() for cohort in sessio.cohorts}
    if titulacio is not None and (not isinstance(titulacio, str) or titulacio not in cohorts):
        raise EntradaError(f'titulacio {titulacio!r} no vàlida: fes servir un codi de titulació existent o omet el paràmetre.')
    cursos = {cohort.rsplit(':', 1)[1] for sessio in b.sessions.values() for cohort in sessio.cohorts}
    if curs is not None and (not isinstance(curs, str) or curs not in cursos):
        raise EntradaError(f'curs {curs!r} no vàlid: fes servir un curs existent (1r, 2n, 3r…) o omet el paràmetre.')
    numero = str(grup).strip().rsplit('/', 1)[-1]
    tipus = str(grup).split('/', 1)[0].upper() if '/' in str(grup) else None
    seleccions = set()
    for s in b.sessions.values():
        if s.grup.rsplit('/', 1)[-1] != numero or (tipus and s.tipus != tipus):
            continue
        for cohort in s.cohorts:
            tit, c = cohort.rsplit(':', 1)
            if (titulacio is None or tit == str(titulacio)) and (curs is None or c == str(curs)):
                seleccions.add((tit, c, s.linia))
    if not seleccions:
        raise EntradaError(f'grup {grup!r} no trobat: fes servir un grup existent per a aquesta titulacio i curs, o omet aquests filtres.')
    w = _setmana(b, setmana)
    d = _dia(dia) if dia is not None else None
    rows = []
    for tit, c, linia in sorted(seleccions):
        cs = graella.celles(b, p, w, cohort=f'{tit}:{c}', linia=linia)
        rows.extend(dict(_json(cella), titulacio=tit, curs=c) for cella in cs if d is None or cella.dia == d)
    horaris = {}
    for r in rows[:LIMIT]:
        key = (r['titulacio'], r['curs'])
        horaris.setdefault(key, {'titulacio': key[0], 'curs': key[1], 'files': []})['files'].append(r)
    return _retorn({'total': len(rows), 'horaris': list(horaris.values())},
                   f'celles(grup={grup}, titulacio={titulacio}, curs={curs}, setmana={w}, dia={d}, proposta={proposta})',
                   [r['id_sessio'] for r in rows[:LIMIT]])


def ocupacio_aula(aula, dia=None, setmana=None, proposta='avui'):
    b, p = _carrega(proposta)
    _aula(b, aula)
    d = _dia(dia) if dia is not None else None
    w = _setmana(b, setmana)
    rows = [r for r in _files(b, p) if r['aula'] == aula and w <= r['data'] < w+dt.timedelta(days=7) and (d is None or r['dia'] == d)]
    return _retorn(sorted(rows, key=lambda r: (r['data'], r['ini_min'], r['id_sessio'])), f'ocupacio_aula(aula={aula}, dia={dia}, setmana={w}, proposta={proposta})')


def aules_lliures(hora_ini, durada_min, places_min, dia=None, data=None, tipus=None, setmana=None, proposta='avui'):
    if (dia is None) == (data is None):
        raise EntradaError('Indica exactament un dia o una data.')
    ini = _hora(hora_ini)
    if type(durada_min) is not int or durada_min <= 0 or ini+durada_min > 1440:
        raise EntradaError(f'durada_min {durada_min!r} no vàlida: fes servir un enter positiu i una franja que acabi abans de mitjanit.')
    if type(places_min) is not int or places_min < 0:
        raise EntradaError(f'places_min {places_min!r} no vàlid: fes servir un enter igual o superior a 0.')
    b, p = _carrega(proposta)
    if tipus is not None and (not isinstance(tipus, str) or tipus not in {a.tipus for a in b.aules.values()}):
        raise EntradaError(f'tipus {tipus!r} no vàlid: fes servir el tipus exacte de l’inventari o omet el paràmetre per cercar aules ordinàries.')
    w = _setmana(b, setmana)
    date = _data(data) if data is not None else w+dt.timedelta(days=DIES.index(_dia(dia)))
    ocupades = {r['aula'] for r in _files(b, p) if r['data'] == date and r['ini_min'] < ini+durada_min and r['fi_min'] > ini}
    # Les aules addicionals de partida també ocupen espai.
    if proposta == 'avui':
        for r in dades.connexio().cursor().execute('SELECT data, ini_min, fi_min, aules_addicionals_partida FROM sessions').fetchall():
            if r[0] == date and r[1] < ini+durada_min and r[2] > ini:
                ocupades.update((r[3] or '').split('|'))
    rows = [{'aula': a.aula, 'capacitat': a.capacitat, 'tipus': a.tipus, 'data': date, 'h_ini': nb.fmt(ini), 'h_fi': nb.fmt(ini+durada_min)}
            for a in b.aules.values() if a.aula not in ocupades and a.capacitat >= places_min and (a.tipus == tipus if tipus else a.ordinaria)]
    return _retorn(sorted(rows, key=lambda r: (r['capacitat'], r['aula'])), f'aules_lliures(data={date}, hora_ini={hora_ini}, durada_min={durada_min}, places_min={places_min}, tipus={tipus}, proposta={proposta}); solapament: inici < fi AND final > inici')


def xifra(id):
    from nivell1 import troballes
    ids = [m.ID for m in troballes.moduls()]
    if id not in ids:
        raise EntradaError(f'id {id!r} no vàlid. IDs disponibles: '+', '.join(ids))
    t = troballes.una(id, 2, None)
    rows = _json(t.taula)
    return _retorn({'id': t.id, 'xifra': t.xifra, 'frase': t.frase, 'metode': t.metode, 'total': len(rows), 'files': rows[:LIMIT]}, t.sql,
                   [r['id_sessio'] for r in rows[:LIMIT] if r.get('id_sessio')])


def resultat_proposta(apartat):
    _apartat(apartat)
    carpeta = nb.RESULTATS_PRINCIPAL / apartat
    informe = json.loads((carpeta / 'informe.json').read_text(encoding='utf-8'))
    # L'informe és suficient: el 5.1 no sempre té resum.json. Conservem
    # també el mode nomes_aules i qualsevol altra metadada del verificador.
    resultat = dict(informe)
    resultat.setdefault('restriccions', {})
    consulta = f'informes nivell2/{apartat}/informe.json'
    resum_path = carpeta / 'resum.json'
    if resum_path.is_file():
        resultat['resum'] = json.loads(resum_path.read_text(encoding='utf-8'))
        consulta += f'; nivell2/{apartat}/resum.json'
    return _retorn(resultat, consulta)


def _normalitza_dies_sql(sql):
    import duckdb
    # Normalitza dies i setmana típica. DuckDB identifica els literals:
    # no toquem comentaris, identificadors,
    # ni cadenes delimitades amb dòlar. Els offsets són bytes UTF-8.
    original = sql.encode('utf-8')
    canvis = []
    setmana_tipica = None
    for inici, tipus in duckdb.tokenize(sql):
        if tipus.name != 'string_const' or original[inici:inici+1] != b"'":
            continue
        literal = re.match(rb"'(?:[^']|'')*'", original[inici:])
        if literal is None:
            continue
        valor = literal[0][1:-1].decode('utf-8')
        if len(valor) <= 1 or valor != valor.strip():
            continue
        normal = ''.join(c for c in unicodedata.normalize('NFD', valor.lower()) if not unicodedata.combining(c))
        if normal in ('tipica', 'typical', 'setmana tipica'):
            if setmana_tipica is None:
                setmana_tipica = _setmana(nb.carrega_oficial(), None).strftime('%G-W%V')
            codi = setmana_tipica
        else:
            try:
                codi = _dia(valor)
            except EntradaError:
                continue
        canvis.append((inici, inici + len(literal[0]), f"'{codi}'".encode('utf-8')))
    for inici, fi, literal in reversed(canvis):
        original = original[:inici] + literal + original[fi:]
    return original.decode('utf-8')


def consulta_sql(sql):
    import duckdb
    if not isinstance(sql, str) or len(sql) > 20000:
        raise EntradaError('Cal una consulta SQL de com a molt 20.000 caràcters.')
    con = duckdb.connect(config={'enable_external_access': False, 'threads': 1})
    timer = None
    try:
        sql = _normalitza_dies_sql(sql)
        statements = con.extract_statements(sql)
        if len(statements) != 1 or statements[0].type != duckdb.StatementType.SELECT or not re.match(r'^\s*(SELECT|WITH)\b', sql, re.I):
            raise EntradaError('Només es permet una sentència SELECT o WITH…SELECT.')
        if re.search(r'\b(?:duckdb_|pragma_|sqlite_|query\s*\(|query_table\s*\()', sql, re.I):
            raise EntradaError('Només es permet consultar les vistes de l’horari.')
        names = con.get_table_names(sql)
        allowed = {'sessions', 'aules', 'activitats', *(f'proposta_{a.replace(".", "_")}' for a in APARTATS)}
        if not names <= allowed:
            raise EntradaError('Només es permeten les vistes sessions, aules, activitats i proposta_5_1…proposta_5_4.')
        for name in names:
            if name.startswith('proposta_'):
                b, p = _carrega(name.removeprefix('proposta_').replace('_', '.'))
                import pandas as pd
                df = pd.DataFrame(_files(b, p))
            else:
                cur = dades.connexio().cursor()
                try:
                    if name == 'activitats':
                        df = cur.execute('SELECT * FROM read_csv_auto(?, all_varchar=true)', [str(nb.PAQUET/'activitats.csv')]).df()
                    else:
                        df = cur.execute(f'SELECT * FROM {name}').df()
                finally:
                    cur.close()
            con.register('_font', df)
            con.execute(f'CREATE TABLE {name} AS SELECT * FROM _font')
            con.unregister('_font')
        timer = threading.Timer(TEMPS_SQL, con.interrupt)
        timer.start()
        cur = con.execute(f'SELECT *, count(*) OVER () AS __total_eina FROM ({sql.rstrip().rstrip(";")}) AS consulta LIMIT 50')
        cols = [c[0] for c in cur.description[:-1]]
        fetched = cur.fetchall()
        total = fetched[0][-1] if fetched else 0
        rows = [dict(zip(cols, r[:-1])) for r in fetched]
        out = _retorn(rows, sql)
        out['resultat']['total'] = total
        out['resultat']['truncat'] = total > LIMIT
        return out
    except duckdb.Error as exc:
        # Els errors de vinculació/sintaxi descriuen la consulta, no les files.
        # Conversió i lectura poden incloure valors: n'ometem el detall sensible.
        if isinstance(exc, (duckdb.ConversionException, duckdb.InvalidInputException)):
            error = str(exc).splitlines()[0]
            error = re.sub(r"(['\"])(.*?)\1", "'[valor omès]'", error)
        else:
            error = str(exc)
        return {'ok': False, 'error': error[:300]}
    finally:
        if timer:
            timer.cancel()
            timer.join()
        con.close()


def _violacions(informe):
    return [v for v in informe.violacions if v.compta]


def prova_canvi(apartat, canvi):
    _apartat(apartat)
    if not isinstance(canvi, dict):
        raise EntradaError('canvi ha de ser un objecte amb tipus imprevist o moure.')
    if canvi.get('tipus') == 'imprevist':
        camps = {'aules_tancades': ('aula', 'data_ini', 'data_fi'),
                 'grups_creixen': ('codi', 'grup', 'alumnes'),
                 'sessions_cancel_lades': ('id_sessio', 'recuperar_fins')}
        for camp, obligatoris in camps.items():
            valors = canvi.get(camp, [])
            if not isinstance(valors, list):
                raise EntradaError(f'canvi.{camp} no vàlid: fes servir una llista d’objectes amb {", ".join(obligatoris)}.')
            for valor in valors:
                if not isinstance(valor, dict) or any(k not in valor for k in obligatoris):
                    raise EntradaError(f'canvi.{camp} no vàlid: cada objecte ha de contenir {", ".join(obligatoris)}.')
    b, p = _carrega(apartat)
    before = nb.avalua_rapid(b, p, nomes_aules=apartat == '5.1')
    nova = copy.deepcopy(p)
    estat = 'MOVIMENT_EXPLICIT'
    if canvi.get('tipus') == 'moure':
        if bool(canvi.get('id_sessio')) == bool(canvi.get('activitat_id')):
            raise EntradaError('Indica id_sessio o activitat_id, exactament un.')
        ids = [sid for sid, s in b.sessions.items() if sid == canvi.get('id_sessio') or s.activitat == canvi.get('activitat_id')]
        if not ids:
            camp = 'id_sessio' if canvi.get('id_sessio') else 'activitat_id'
            raise EntradaError(f'{camp} {canvi.get(camp)!r} no vàlid: fes servir un identificador existent a la proposta.')
        if not any(k in canvi for k in ('dia', 'hora_ini', 'aula')):
            raise EntradaError('canvi moure sense destí: indica almenys dia, hora_ini o aula.')
        for sid in ids:
            a = nova.files[sid]
            if 'dia' in canvi:
                a.dia = _dia(canvi['dia'])
                if a.data:
                    d = dt.date.fromisoformat(a.data)
                    a.data = (d-dt.timedelta(days=d.weekday())+dt.timedelta(days=DIES.index(a.dia))).isoformat()
            if 'hora_ini' in canvi:
                _hora(canvi['hora_ini'])
                a.h_ini = nb.fmt(_hora(canvi['hora_ini']))
            if 'aula' in canvi:
                _aula(b, canvi['aula'])
                a.aula = canvi['aula']
    elif canvi.get('tipus') == 'imprevist':
        from nivell2.reparacio import Canvi, repara
        from horaris.model import Tancament
        after = copy.deepcopy(b)
        if not any(canvi.get(k) for k in ('aules_tancades', 'grups_creixen', 'sessions_cancel_lades')):
            raise EntradaError('Indica almenys un tancament, creixement o cancel·lació.')
        for t in canvi.get('aules_tancades', []):
            _aula(b, t['aula'])
            d1, d2 = _data(t['data_ini'], 'data_ini'), _data(t['data_fi'], 'data_fi')
            if d2 < d1:
                raise EntradaError('data_fi no vàlida: ha de ser igual o posterior a data_ini.')
            after.tancaments.append(Tancament(t['aula'], d1, d2))
        for g in canvi.get('grups_creixen', []):
            rows = [s for s in after.sessions.values() if s.codi == g['codi'] and s.grup == g['grup']]
            if not rows:
                raise EntradaError('codi/grup no vàlids: indica un codi d’assignatura i un grup existents (p. ex. TE/81).')
            if type(g['alumnes']) is not int or any(g['alumnes'] < s.alumnes for s in rows):
                raise EntradaError('alumnes no vàlid: fes servir un enter igual o superior a l’alumnat actual del grup.')
            for s in rows:
                s.alumnes = g['alumnes']
        for c in canvi.get('sessions_cancel_lades', []):
            if not isinstance(c['id_sessio'], str) or c['id_sessio'] not in b.sessions:
                raise EntradaError('id_sessio no vàlid: fes servir un identificador de sessió existent a la proposta.')
            limit = _data(c['recuperar_fins'], 'recuperar_fins')
            if limit <= b.sessions[c['id_sessio']].data:
                raise EntradaError('recuperar_fins no vàlid: ha de ser una data AAAA-MM-DD posterior a la sessió.')
            after.cancellades[c['id_sessio']] = limit
        res = repara(p, Canvi(after, b, temps_s=10))
        estat = res.estat
        b = after
        if res.proposta is None:
            return _retorn({'estat': estat, 'veredicte': 'SENSE PROPOSTA', 'canvis': [], 'total': 0}, 'repara + avalua_rapid: sense solució al veïnat provat')
        nova = res.proposta
    else:
        raise EntradaError('tipus ha de ser imprevist o moure.')
    inf = nb.avalua_rapid(b, nova, nomes_aules=apartat == '5.1')
    # Identitat completa, incloent sessions, per detectar conflictes nous encara que el recompte no canviï.
    def clau(v):
        return json.dumps(_json(v), sort_keys=True, ensure_ascii=False)
    antics = Counter(clau(v) for v in _violacions(before))
    nous = []
    for v in _violacions(inf):
        k = clau(v)
        if antics[k]:
            antics[k] -= 1
        else:
            nous.append(_json(v))
    diffs = [{'id_sessio': sid, 'abans': _json(p.files[sid]), 'despres': _json(a)} for sid, a in nova.files.items() if a != p.files[sid]]
    ids_conflictes = set(re.findall(r'[\w/.-]+', json.dumps(nous))) & b.sessions.keys()
    return _retorn({'veredicte': inf.veredicte, 'veredicte_abans': before.veredicte,
                    'verificacio': 'Ràpida, sense relaxacions declarades; compara incompliments amb la proposta original.',
                    'estat': estat, 'total': len(diffs), 'canvis': diffs[:LIMIT],
                    'total_incompliments_nous': len(nous), 'incompliments_nous': nous[:LIMIT],
                    'nous_per_regla': dict(Counter(v['regla'] for v in nous))},
                   f'prova_canvi({apartat}, {json.dumps(canvi, ensure_ascii=False)}); avalua_rapid abans/després',
                   [r['id_sessio'] for r in diffs] + sorted(ids_conflictes))


_HANDLERS = {f.__name__: f for f in (horari_grup, aules_lliures, ocupacio_aula, xifra, resultat_proposta, consulta_sql, prova_canvi)}


def executa(nom: str, args: dict) -> dict:
    try:
        if not isinstance(nom, str) or nom not in _HANDLERS:
            raise EntradaError('Eina desconeguda.')
        if not isinstance(args, dict):
            raise EntradaError('Els arguments han de ser un objecte JSON.')
        try:
            inspect.signature(_HANDLERS[nom]).bind(**args)
        except TypeError as exc:
            raise EntradaError(f'Paràmetres de {nom} no vàlids: {exc}. Consulta els paràmetres acceptats a la definició de l’eina.') from None
        result = _HANDLERS[nom](**args)
        json.dumps(result, allow_nan=False)
        return result
    except EntradaError as e:
        return {'ok': False, 'error': str(e)}
    except FileNotFoundError:
        return {'ok': False, 'error': 'Les dades o la proposta demanada encara no estan disponibles.'}
    except Exception:
        # No exposem fragments de files que DuckDB o el carregador incloguin als errors.
        return {'ok': False, 'error': 'No s’ha pogut completar la consulta: revisa els valors i la disponibilitat de les dades (SQL: màxim 5 segons, sense accés extern).'}


def _obj(props, required=()):
    return {'type': 'object', 'properties': props, 'required': list(required), 'additionalProperties': False}


def _str(description):
    return {'type': 'string', 'description': description}


_PROPOSTA = {'type': 'string', 'enum': ['avui', *APARTATS], 'default': 'avui'}
_APARTAT = {'type': 'string', 'enum': list(APARTATS)}
_COMMON = {'dia': _str('L, M, X, J o V (també el nom del dia)'), 'setmana': {'type': ['string', 'integer', 'null'], 'description': "buit o 'típica' = setmana típica; o 2027-W07; o una data"}, 'proposta': _PROPOSTA}
_CANVI = {'oneOf': [
    _obj({'tipus': {'const': 'moure', 'type': 'string'}, 'id_sessio': _str('Una sola sessió'), 'activitat_id': _str('Totes les sessions de l’activitat; tria això o id_sessio'), 'dia': _COMMON['dia'], 'hora_ini': _str('Hora: 16, 16:00, 16.00 o 16h'), 'aula': _str('Codi exacte d’aula')}, ['tipus']),
    _obj({'tipus': {'const': 'imprevist', 'type': 'string'},
          'aules_tancades': {'type': 'array', 'items': _obj({k: _str(v) for k, v in [('aula', 'Codi aula'), ('data_ini', 'AAAA-MM-DD inclosa'), ('data_fi', 'AAAA-MM-DD inclosa')]}, ['aula', 'data_ini', 'data_fi'])},
          'grups_creixen': {'type': 'array', 'items': _obj({'codi': _str('Codi assignatura'), 'grup': _str('Grup exacte, p. ex. TE/81'), 'alumnes': {'type': 'integer', 'minimum': 0}}, ['codi', 'grup', 'alumnes'])},
          'sessions_cancel_lades': {'type': 'array', 'items': _obj({'id_sessio': _str('Sessió cancel·lada'), 'recuperar_fins': _str('Data límit AAAA-MM-DD')}, ['id_sessio', 'recuperar_fins'])}}, ['tipus'])]}


def _metadades_xifres():
    from nivell1 import troballes
    # Només importem mòduls i consultem metadades; mai calcula().
    moduls = troballes.moduls()
    preguntes = {
        'ocupacio': 'ocupació física de les aules de l’horari actual',
        'hores-aula': 'demanda d’hores-aula i cobertura de les aules de partida',
        'fora-torn': 'quantes sessions són al torn equivocat avui amb el model nou',
        'hi-cap-mati': 'hi cap el matí? Condicions necessàries als dos torns',
        'aforament': 'sessions que superen l’aforament segons R3',
        'marge-grau-nou': 'marge d’hores-aula per al grau nou',
        'dobles-mati': 'dobles titulacions de cursos superiors al matí',
        'docents-cavall': 'docents de cursos inicials i superiors el mateix dia',
        'canvis-aula': 'dispersió i canvis d’aula de l’alumnat',
        'hores-mortes': 'hores mortes de l’alumnat dins del mateix torn',
        'problemes-millores': 'problemes observats i propostes de millora',
    }
    descripcio = "Primer opció per a xifres generals de l'horari d'avui (part 1)."
    for m in moduls:
        titol = preguntes.get(m.ID) or getattr(m, 'TITOL', None) or getattr(m, 'PREGUNTA', None) or (m.__doc__ or m.ID).strip().splitlines()[0]
        descripcio += f'\n{m.ID}: {titol}'
    return [m.ID for m in moduls], descripcio


_IDS_XIFRES, _DESCRIPCIO_XIFRA = _metadades_xifres()
# Esquema fix a partir de docs/esquema-dades.md, nivell1.dades.connexio
# i _files: no obrim les dades per construir les definicions de tools.
_COLUMNES_SQL = {
    'sessions': 'id_sessio, activitat_id, id_compartida, codi, assignatura, tipus, grup, semestre, data, setmana, dia, h_ini, h_fi, durada_min, alumnes, capacitat_grup, aula_partida, aules_addicionals_partida, plans, titulacions_curs, dc, torn_requerit, fixada, docents, alumnes_origen, sense_espai, sem, ini_min, fi_min, torn_actual, unitat, demanda_aulari',
    'aules': 'aula, edifici, tipus, descripcio, capacitat, ordinaria',
    'activitats': 'activitat_id, codi, grup, semestre, dia, h_ini, h_fi, assignatura, tipus, n_sessions, setmana_primera, setmana_ultima, alumnes, aules_partida, sessions_sense_aula, titulacions_curs, torn_requerit, fixada, docents, sense_espai',
    'proposta_5_1, proposta_5_2, proposta_5_3, proposta_5_4': 'id_sessio, activitat_id, data, setmana, dia, h_ini, h_fi, ini_min, fi_min, aula, assignatura, tipus, grup',
}
_DESCRIPCIO_SQL = ('Una SELECT o WITH…SELECT, màxim 50 files i 5 s. Fes servir xifra primer per a xifres generals. '
                   'Sense fitxers ni xarxa. Columnes de les vistes:\n'
                   + '\n'.join(f'{nom}: {cols}' for nom, cols in _COLUMNES_SQL.items())
                   + "\ndia: L, M, X, J o V (X = dimecres); h_ini 'HH:MM'; ini_min = minuts des de mitjanit"
                   + "\nper a la setmana típica, filtra setmana = 'típica' (es tradueix sol). Sense filtre de setmana es compta tot el semestre seleccionat; a sessions filtra sem = 2 per al segon semestre."
                   + "\nel torn d'una sessió es dedueix de h_ini (abans de 14.30 matí); torn_requerit és el que li toca")

_DEFS = [
    ('horari_grup', 'Horari del grup i els seus subgrups en una setmana. Només cal grup: no preguntis titulació ni curs; si falten, retorna totes les coincidències agrupades per titulació i curs (màxim 50 files en total).', _obj({**_COMMON, 'titulacio': _str('Codi titulació'), 'curs': _str('1r, 2n, 3r, 4t…'), 'grup': _str('Grup: 81, TE/81, 811…; inclou la línia associada de teoria i subgrups')}, ['grup'])),
    ('aules_lliures', 'Aules lliures durant tota la franja en la proposta triada; ordinàries per defecte. Indica dia o data.', _obj({**_COMMON, 'data': _str('AAAA-MM-DD; exclou dia'), 'hora_ini': _str('Hora: 16, 16:00, 16.00 o 16h'), 'durada_min': {'type': 'integer', 'minimum': 1}, 'places_min': {'type': 'integer', 'minimum': 0}, 'tipus': _str('Tipus exacte de l’inventari; substitueix el filtre ordinària')}, ['hora_ini', 'durada_min', 'places_min'])),
    ('ocupacio_aula', 'Sessions que ocupen una aula durant una setmana de la proposta triada.', _obj({**_COMMON, 'aula': _str('Codi exacte d’aula')}, ['aula'])),
    ('xifra', _DESCRIPCIO_XIFRA, _obj({'id': {**_str('ID de la troballa'), 'enum': _IDS_XIFRES}}, ['id'])),
    ('resultat_proposta', 'Veredicte oficial i recomptes per regla d’una proposta 5.1–5.4.', _obj({'apartat': _APARTAT}, ['apartat'])),
    ('consulta_sql', _DESCRIPCIO_SQL, _obj({'sql': _str('Consulta SQL de lectura')}, ['sql'])),
    ('prova_canvi', 'Simula sense desar. moure: id_sessio o activitat_id i almenys dia/hora_ini/aula; valida i compara conflictes nous sense reparar. imprevist: llistes de tancaments, creixements o cancel·lacions; repara (10 s) i valida.', _obj({'apartat': _APARTAT, 'canvi': _CANVI}, ['apartat', 'canvi'])),
]
EINES: list[dict] = [{'type': 'function', 'function': {'name': n, 'description': d, 'parameters': p}} for n, d, p in _DEFS]


def main():
    # Seleccions calculades, sense imprimir files ni continguts dels resultats.
    b, p = _carrega()
    grups = _modul('components.graella').grups
    gs = grups(b)
    tit = next(iter(gs)); curs = next(iter(gs[tit])); grup = next(iter(gs[tit][curs]))
    s = next(iter(b.sessions.values()))
    from nivell1 import troballes
    calls = [('horari_grup', dict(titulacio=tit, curs=curs, grup=grup)),
             ('aules_lliures', dict(dia='L', hora_ini='10:00', durada_min=60, places_min=60)),
             ('ocupacio_aula', dict(aula=next(iter(b.aules)))), ('xifra', dict(id=troballes.moduls()[0].ID)),
             ('resultat_proposta', dict(apartat='5.2')), ('consulta_sql', dict(sql='SELECT id_sessio FROM sessions LIMIT 3')),
             ('prova_canvi', dict(apartat='5.2', canvi={'tipus': 'moure', 'id_sessio': s.id, 'hora_ini': nb.fmt(s.ini)}))]
    for name, args in calls:
        r = executa(name, args)
        if not r['ok']:
            print(f'{name}: ERROR {r["error"]}')
        else:
            result = r['resultat']
            print(f'{name}: files={result.get("total", 1)} id_sessio={r["id_sessio"][:3]}')


if __name__ == '__main__':
    main()
