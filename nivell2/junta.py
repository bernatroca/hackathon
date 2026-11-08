"""Resum de decisió de la Junta; no substitueix el verificador oficial."""
from __future__ import annotations

import argparse
import csv
import json
import hashlib
import os
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime
from html import escape
from pathlib import Path
from statistics import median

from nivell2.base import (CONTINGENCIES, GRAU_NOU, Informe, RESULTATS, Proposta, carrega_model,
                         carrega_oficial, fmt, avalua)
from nivell2.franges import RESERVA
from nivell2.xifres import calcula as calcula_xifres
from horaris.check import Informe as InformeIntern, _col_loca, _torn_ok
from horaris.model import llegeix_proposta, llegeix_relaxacions, a_traslladar

MIDES = [(0, 34, 'Fins a 34'), (35, 50, '35–50'), (51, 63, '51–63'),
         (64, 90, '64–90'), (91, 160, '91–160')]
NOMS = {'GED': 'Enginyeria de Dades', 'GEI': 'Enginyeria Informàtica',
        'GEQ': 'Enginyeria Química', 'GIA': 'Intel·ligència Artificial',
        'GCIS': 'Gestió de Ciutats Intel·ligents i Sostenibles',
        'GEET': 'Enginyeria Electrònica de Telecomunicació',
        'GEST': 'Enginyeria de Sistemes de Telecomunicació',
        'GEET+GEST': 'Enginyeria Electrònica i de Sistemes de Telecomunicació',
        'MEBA': 'Màster en Enginyeria Biològica i Ambiental',
        'MET': 'Màster en Enginyeria de Telecomunicació', 'MRICSE': 'Màster RICSE',
        'GNOU': 'Grau nou (40 places)'}
NOMS_PROPOSTES = {'Avui': 'Avui', '5.1': 'Aules assignades (5.1)',
                 '5.2': 'Torns nous (5.2)', '5.3': 'Resoldre els imprevistos (5.3)',
                 '5.4': 'Incorporar el grau nou (5.4)'}


COM_HO_HEM_CALCULAT = (
    'Hem comptat les aules necessàries per a les classes del segon semestre, '
    'amb els dies i les hores de la proposta. '
    'Les places de les aules i els torns venen de les dades oficials; '
    'el nombre d’alumnes ve de les dades del model. '
    'Si una classe no té aula, estimem quantes places necessita. '
    'També comptem quines classes canvien de dia, d’hora o d’aula i quines queden fora del torn que els toca.')

DETALL_TECNIC = (
                'Segon semestre; hores proposades; franges d’una hora des de les 8.30 '
                '(última: 20.30–21); aules ordinàries diferents ocupades (R8). Sense aula: estimació de demanda ordinària, sense PLAB, dobles sense espai, seminaris, laboratoris ni aules externes de partida. Demanda per mida segons els alumnes; ocupació per mida segons la capacitat de l’aula. Compartides un cop i alumnes sumats; sense laboratoris '
                'ni dobles sense espai per a la demanda. Setmana típica: sessions més properes '
                'a la mediana, desempat per la primera. Pitjor setmana: pic màxim de cada torn. '
                'Torns de la base oficial, segons l’hora d’inici. Alumnes de la base del model. '
                'Sessió moguda: canvi de dia o hora; canvi d’aula només si ja en tenia, sense J ni dobles sense espai; denominador: totes les sessions de cada titulació i curs. '
                'Les compartides compten en cada titulació. Excepcions: incompliments de torn declarats segons el verificador, sense els heretats. '
                'Les que ja es fan avui fora de torn, sense excepció declarada, es compten a part. No és una validació de l’horari.')
DETALL_TECNIC += (
    ' R1-TORN identifica la regla de torn; PLAB identifica els laboratoris. '
    'Les aules J són aules d’un altre edifici que s’han de portar a l’Escola. '
    'Llindars acumulats: demanda i oferta de totes les mides a partir del mínim indicat. '
    'Oferta limitada a les aules ordinàries menys la reserva flexible: cota optimista, '
    'no garantia d’encaix. No se sumen els marges.')


VERSIO_RESUM = 7
VERSIO_CALCUL = 6
MOTIU_FIXADES = 'La regla 1 diu que les classes de 1r i 2n d’aquests graus no es toquen; ja es fan a la tarda.'
MOTIU_S04526 = ("Aquesta classe és el divendres 9/4, l’únic dia lectiu de la setmana "
                "d’avaluació: del 5 al 8/4 és avaluació. Aquell dia no hi ha cap "
                "franja de tarda lliure per a aquesta classe; ho demostra el càlcul.")


EXPLICACIO_PICS = ('Les aules es compten durant tota la franja d’una hora; '
                   'les classes alhora es compten per instant. Tots dos recomptes inclouen '
                   'els laboratoris en aules ordinàries. Per això les xifres poden diferir.')


def resum_canvis_aula(d):
    if 'canvis_franja' in d:
        return (f"Canvien de dia o hora: {numero(d['canvis_franja'])} {classe(d['canvis_franja'])} · "
                f"Canvien d’aula: {numero(d['canvis_aula'])} {classe(d['canvis_aula'])}.")
    return (f"Canvis d’aula: {d['canvis_aula']} {classe(d['canvis_aula'])}." if 'canvis_aula' in d
            else 'Canvis d’aula: vegeu el recompte per curs a la taula.')


def classe(n):
    return 'classe' if n == 1 else 'classes'


def numero(n):
    if isinstance(n, float) and n.is_integer():
        n = int(n)
    return f'{n:,}'.replace(',', '.')


def empremtes(proposta=None):
    if proposta is None:
        return {'proposta': 'Avui', 'relaxacions': None}
    proposta = Path(proposta)
    relax = proposta.with_name('relaxacions.csv')
    return {'proposta': hashlib.sha256(proposta.read_bytes()).hexdigest(),
            'relaxacions': hashlib.sha256(relax.read_bytes()).hexdigest() if relax.exists() else None}


def escriu_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         delete=False) as f:
            temporal = Path(f.name)
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporal, path)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)



def es_motiu_avaluacio(text):
    normalitzat = re.sub(r'(?:\.\./5\.2/)?diagnostic\.md', 'diagnostic.md',
                         text.replace("'", '’').strip())
    return normalitzat == ('Setmana d’avaluació: impossibilitat demostrada '
                           'amb R1 dura; vegeu diagnostic.md.')


def motiu_planer(text):
    if text == MOTIU_S04526 or es_motiu_avaluacio(text):
        return MOTIU_S04526
    if text.replace("'", '’').strip() == MOTIU_FIXADES:
        return 'Classe fixada de 1r/2n: no es mou (regla 1)'
    text = text.replace('../5.2/diagnostic.md', 'diagnostic.md')
    for tecnic, planer in [
            ('Restauració al patró rebutjada: restriccions oficials: ', ''),
            ('Restauració al patró rebutjada: ', ''),
            ('R2-CALENDARI', 'dia no lectiu'),
            ('R4-ALUMNAT', 'coincideix amb una altra classe del grup'),
            ('R4-AULA', 'l’aula està ocupada'),
            ('R4-DOCENT', 'el professor té una altra classe'),
            ('supera el límit de qualitat de la variant de referència',
             'empitjorava massa la resta de l’horari'),
            ('R1 dura', 'el torn obligatori')]:
        text = text.replace(tecnic, planer)
    for tecnic, planer in [('R1-TORN', 'regla de torn'), ('PLAB', 'laboratori'),
                           ('TE/', 'grup '), ('PAUL', 'problemes'), ('SEM', 'seminari'),
                           (' J ', ' d’un altre edifici '), ('R8', 'reserva d’aules'),
                           ('llindar', 'mínim'), ('cota', 'estimació')]:
        text = text.replace(tecnic, planer)
    return text.replace('diagnostic.md', 'el diagnòstic tècnic')


def percentatge(valor):
    return f'{valor:.1f}'.rstrip('0').rstrip('.').replace('.', ',') + ' %'


def escenari_proposta(nom):
    return CONTINGENCIES if nom == '5.3' else GRAU_NOU if nom.startswith('5.4') else None


def aulari(base):
    ordinaries = sum(a.ordinaria for a in base.aules.values())
    return {'ordinaries': ordinaries, 'reserva': RESERVA,
            'disponibles': max(0, ordinaries - RESERVA)}


def explicacio_aulari(d):
    a = d['aulari']
    return (f"L'aulari té {a['ordinaries']} aules ordinàries; "
            f"en guardem {a['reserva']} de reserva per a imprevistos.")


def titol_marge(d):
    m = d.get('marge_imprevistos')
    if m and m['marge'] <= 0:
        aules = '1 aula' if m['marge'] == -1 else f"{abs(m['marge'])} aules"
        return ('Durant l’imprevist no queda cap aula lliure fora de la reserva' if m['marge'] == 0
                else f"Durant l’imprevist {'cal' if m['marge'] == -1 else 'calen'} {aules} de la reserva")
    n = d['aulari']['disponibles']
    torn, pic = torn_amb_menys_marge(d)
    if pic > n:
        if any(t['pitjor']['classes'] == pic and t['pitjor']['estimacio'] for t in d['pics'].values()):
            return f'{torn} s’estimen {pic} aules de {n}; cal confirmar l’assignació'
        return f'{torn} calen {pic} aules de {n}: ja cal fer servir la reserva'
    if pic == n:
        return f'{torn} no queda cap aula lliure a l’hora punta'
    marge = n - pic
    return f"{torn} {'queda' if marge == 1 else 'queden'} {marge} {'aula lliure' if marge == 1 else 'aules lliures'} a l’hora punta"


def torn_amb_menys_marge(d):
    torn = max(('mati', 'tarda'), key=lambda t: d['pics'][t]['pitjor']['classes'])
    return ('Al matí' if torn == 'mati' else 'A la tarda'), d['pics'][torn]['pitjor']['classes']


def explicacio_marge(d):
    m = d.get('marge_imprevistos')
    if m:
        marge = ('cap aula lliure fora de la reserva' if m['marge'] == 0 else
                 f"{m['marge']} aules lliures fora de la reserva" if m['marge'] > 0 else
                 f"un dèficit de {abs(m['marge'])} aules fora de la reserva")
        return (f"El {date.fromisoformat(m['data']):%d/%m} a les {m['hora']} "
                f"({', '.join(m['aules_tancades'])} {'tancada' if len(m['aules_tancades']) == 1 else 'tancades'} per l’imprevist): "
                f"{m['utilitzables']} aules utilitzables, {m['ocupades']} {'ocupada' if m['ocupades'] == 1 else 'ocupades'} i {marge}. "
                f"Es mantenen {d['aulari']['reserva']} aules de reserva.")
    torn, pic = torn_amb_menys_marge(d)
    if pic < d['aulari']['disponibles']:
        return "Aquest marge permet absorbir imprevistos, a més de les aules de reserva."
    if pic > d['aulari']['disponibles']:
        if any(t['pitjor']['classes'] == pic and t['pitjor']['estimacio'] for t in d['pics'].values()):
            return 'És una estimació de demanda; cal assignar les aules abans de concloure si falta espai.'
        return (f"{torn} ja se superen les aules disponibles per a classes: "
                f"calen {pic - d['aulari']['disponibles']} aules de la reserva o moure classes. "
                'No queda marge per absorbir imprevistos.')
    return ("Ocupar totes les aules disponibles a l'hora punta vol dir que qualsevol avaria, "
            f"reserva o grup que creix obliga a fer servir les {d['aulari']['reserva']} aules "
            'de reserva o a moure classes. Recomanem mantenir almenys 1–2 aules lliures '
            "a l'hora punta.")


def nom(cohort):
    tit, _, curs = cohort.partition(':')
    sufix = ', sense curs a les dades' if curs == '?' else f', {curs}' if curs not in ('', 'M') else ''
    return NOMS.get(tit, f'Titulació {tit}') + sufix


def carrega_proposta(path, base, escenari=None):
    """Rebutja errors estructurals; ignora les files d'altres semestres com el jurat."""
    files = llegeix_proposta(Path(path))
    altres = {f.id for f in files} - base.sessions.keys()
    if altres:
        conegudes = carrega_oficial(escenari, semestre=None).sessions
        desconegudes = altres - conegudes.keys()
        if desconegudes:
            raise ValueError(f'Sessions desconegudes: {sorted(desconegudes)[:5]}')
    files = [f for f in files if f.id in base.sessions]
    inf = InformeIntern()
    col = _col_loca(base, files, inf)
    if inf.violacions:
        raise ValueError('Proposta incompleta o amb format incorrecte: ' +
                         '; '.join(f'{v.regla}: {v.sessions}' for v in inf.violacions[:5]))
    return Proposta.llegeix(Path(path)), col


def pics_i_mides(base, model, col, nomes_mati_requerit=False):
    """Pic R8 d’aules ordinàries; demanda estimada quan falta aula.

    Les mides acumulades són cotes amb reserva flexible: min(disponibles, aules prou
    grans). No se sumen els marges dels diferents llindars.
    """
    setmanes = Counter(c.data.isocalendar()[:2] for c in col.values())
    if not setmanes:
        raise ValueError('La proposta no conté sessions del segon semestre')
    tipica = min(setmanes, key=lambda w: (abs(setmanes[w] - median(setmanes.values())), w))
    unitats = defaultdict(list)
    for sid, c in col.items():
        if not c.s.sense_espai:
            unitats[c.s.unitat].append(sid)
    alumnes_unitat = {u: sum(model.sessions[sid].alumnes for sid in membres)
                      for u, membres in unitats.items()}
    ocupacio, demanda_per_instant = {}, defaultdict(list)
    franges = defaultdict(list)
    estimacions = set()
    ordinaries = {a for a, x in base.aules.items() if x.ordinaria}
    maxim = aulari(base)['disponibles']
    simultanies = defaultdict(list)
    for c in col.values():
        if c.s.sense_espai or (nomes_mati_requerit and c.s.torn != 'mati'):
            continue
        estimada = (not c.aula and c.s.tipus != 'PLAB'
                    and (not c.s.aula or c.s.aula in ordinaries or a_traslladar(c.s.aula)))
        if c.aula not in ordinaries and not estimada:
            continue
        simultanies[c.data].append(c)
        for h in range(510, 1260, 60):
            if c.ini < h + 60 and c.fi > h:
                franges[c.data, h].append(c)
                if estimada:
                    estimacions.add((c.data, h))
    for (dia, h), classes in franges.items():
        def aules_ocupades(actives):
            return {('aula', c.aula) if c.aula else ('estimada', c.s.unitat):
                    base.aules[c.aula].capacitat if c.aula else alumnes_unitat[c.s.unitat]
                    for c in actives}
        instants = sorted({max(h, c.ini) for c in classes})
        instantanies = [[c for c in classes if c.ini <= t < c.fi] for t in instants]
        # Amb aula: el recompte R8 ocupa tota la franja. Sense aula: només
        # estimem el pic per instant, perquè les classes successives comparteixen espai.
        ocupacio[dia, h] = (max((aules_ocupades(cs) for cs in instantanies), key=len)
                            if (dia, h) in estimacions else aules_ocupades(classes))
        # La demanda sempre ve dels alumnes, mai de la capacitat on s'han col·locat.
        demanda_per_instant[dia, h] = [
            [alumnes_unitat[u] for u in {c.s.unitat for c in cs}] for cs in instantanies]
    out = {}
    for torn, ini, fi in [('mati', 510, 870), ('tarda', 870, 1260)]:
        pics = [(d, h, v) for (d, h), v in ocupacio.items() if ini <= h < fi]
        def pic(rows):
            d, h, v = min(rows, key=lambda r: (-len(r[2]), r[0], r[1])) if rows else (None, ini, {})
            return {'classes': len(v), 'aules_disponibles': maxim,
                    'estimacio': any((dd, hh) in estimacions for dd, hh, _ in rows),
                    'setmana': d.strftime('%G-W%V') if d else None,
                    'data': str(d) if d else None, 'hora': fmt(h)}
        # La descomposició per mida correspon a la mateixa franja que el pic;
        # els màxims independents de cada mida no es poden sumar.
        al_pic = min(pics, key=lambda r: (-len(r[2]), r[0], r[1]))[2] if pics else {}
        mides = []
        for baix, alt, etiqueta in MIDES:
            exacta = max((sum(baix <= n <= alt for n in v.values()) for _, _, v in pics), default=0)
            oferta = sum(baix <= a.capacitat <= alt for a in base.aules.values() if a.ordinaria)
            demanda = max((sum(n >= max(1, baix) for n in v)
                           for d, h, _ in pics for v in demanda_per_instant[d, h]), default=0)
            # El primer llindar inclou també els grups encara sense dada.
            if baix == 0:
                demanda = max((len(v) for d, h, _ in pics
                               for v in demanda_per_instant[d, h]), default=0)
            disponibles = min(maxim, sum(a.capacitat >= baix for a in base.aules.values() if a.ordinaria))
            mides.append({'mida': etiqueta, 'pic_categoria': exacta,
                          'ocupades_al_pic': sum(baix <= n <= alt for n in al_pic.values()),
                          'estimacio': any((d, h) in estimacions for d, h, _ in pics),
                          'aules_categoria': oferta,
                          'minim_places': baix, 'demanda_acumulada': demanda,
                          'oferta_acumulada': disponibles, 'marge': disponibles - demanda,
                          'falten': max(0, demanda - disponibles),
                          'sobren': max(0, disponibles - demanda)})
        candidats = []
        for dia, classes in simultanies.items():
            instants = {max(ini, c.ini) for c in classes if c.ini < fi and c.fi > ini}
            for instant in instants:
                n = len({c.s.unitat for c in classes if c.ini <= instant < c.fi})
                candidats.append((n, dia, instant))
        n, dia, instant = min(candidats, key=lambda x: (-x[0], x[1], x[2])) if candidats else (0, None, ini)
        out[torn] = {'simultani': {'classes': n, 'data': str(dia) if dia else None, 'hora': fmt(instant)},
                     'pitjor': pic(pics),
                     'tipica': pic([r for r in pics if r[0].isocalendar()[:2] == tipica]),
                     'mides': mides, 'total_mides': sum(m['ocupades_al_pic'] for m in mides)}
        out[torn]['tipica']['setmana'] = f'{tipica[0]}-W{tipica[1]:02}'
    return out


def marge_imprevistos(base, col):
    """Marge real durant els tancaments, descomptant-los també de l'oferta."""
    ordinaries = {a for a, x in base.aules.items() if x.ordinaria}
    candidats = []
    per_dia = defaultdict(list)
    for c in col.values():
        if not c.s.sense_espai and c.aula in ordinaries:
            per_dia[c.data].append(c)
    for dia, classes in sorted(per_dia.items()):
        for h in range(510, 1260, 60):
            tancades = {t.aula for t in base.tancaments if t.aula in ordinaries
                        and t.data_ini <= dia <= t.data_fi and t.ini < h + 60 and t.fi > h}
            if not tancades:
                continue
            ocupades = len({c.aula for c in classes if c.ini < h + 60 and c.fi > h})
            utilitzables = len(ordinaries - tancades)
            candidats.append({'data': str(dia), 'hora': fmt(h),
                               'aules_tancades': sorted(tancades), 'utilitzables': utilitzables,
                               'ocupades': ocupades, 'marge': utilitzables - RESERVA - ocupades})
    return min(candidats, key=lambda m: (m['marge'], m['data'], m['hora'])) if candidats else None


def calcula(proposta, base, model, col, relaxacions=None, nom_proposta='Avui'):
    _, cohorts = calcula_xifres(proposta, base, Informe(
        {'veredicte': 'No s’ha verificat aquí', 'restriccions': {}, 'objectius': {}}, ''))
    totals = {r['cohort']: r['sessions'] for r in cohorts}
    mogudes, canvis_aula, assignades = Counter(), Counter(), Counter()
    excepcions, grups = [], Counter()
    fora_torn_ja_avui = 0
    fixades_tarda = 0
    afectades = Counter()
    relax = llegeix_relaxacions(relaxacions)
    informe = avalua(base, proposta.a_files(), relaxacions=relax)
    inicial = avalua(base, Proposta.de_base(base).a_files())
    existents_ids = {sid for sid, s in base.sessions.items() if not (nom_proposta == '5.4'
                     and any(coh.startswith('GNOU:') for coh in s.cohorts))}
    torn_avui = [v for v in inicial.violacions if v.regla == 'R1-TORN']
    heretades = {sid for v in torn_avui if v.heretada for sid in v.sessions} & existents_ids
    comptables = {sid for v in torn_avui if not v.heretada for sid in v.sessions} & existents_ids
    excepcions_aula = []
    for regla in sorted({v.regla for v in informe.violacions
                         if v.declarada and not v.heretada and v.regla != 'R1-TORN'}):
        ids = sorted({sid for v in informe.violacions
                      if v.regla == regla and v.declarada and not v.heretada for sid in v.sessions})
        cohorts_aula = sorted({coh for sid in ids if sid in base.sessions
                               for coh in base.sessions[sid].cohorts})
        motius = list(dict.fromkeys(motiu_planer(r.justificacio) for r in relax
                      if r.restriccio == regla and (not r.sessions or set(ids) & set(r.sessions))))
        nomes_aula = bool(ids) and all(sid in col and (col[sid].data, col[sid].ini) ==
                       (col[sid].s.data, col[sid].s.ini) for sid in ids)
        per_tancament = nomes_aula and all(any(t.aula == col[sid].s.aula
            and t.data_ini <= col[sid].s.data <= t.data_fi
            and t.ini < col[sid].s.fi and t.fi > col[sid].s.ini for t in base.tancaments) for sid in ids)
        if regla in ('R1-FIXADA', 'R7-PLAB') and per_tancament:
            motius = ['L’aula està tancada per l’imprevist; només es canvia l’aula, amb el mateix dia i hora.']
        excepcions_aula.append({'restriccio': regla, 'sessions': ids, 'nombre': len(ids),
                                'cohorts': cohorts_aula, 'motiu': ' '.join(motius),
                                'nomes_aula': nomes_aula, 'per_tancament': per_tancament})
    declarades = {sid for v in informe.violacions
                  if v.regla == 'R1-TORN' and v.declarada and not v.heretada
                  for sid in v.sessions}
    for sid, c in col.items():
        s = c.s
        if ((c.data, c.ini) != (s.data, s.ini) or
                (s.aula and not a_traslladar(s.aula) and not s.sense_espai and c.aula != s.aula)):
            afectades.update(set(s.cohorts))
        if (c.data, c.ini) != (s.data, s.ini):
            mogudes.update(set(s.cohorts))
        if s.aula and not a_traslladar(s.aula) and not s.sense_espai and c.aula != s.aula:
            canvis_aula.update(set(s.cohorts))
        if not s.aula and c.aula and not s.sense_espai:
            assignades.update(set(s.cohorts))
        if (s.fixada.startswith('R1')
                and any(r.restriccio == 'R1-TORN' and (not r.sessions or sid in r.sessions) for r in relax)
                and _torn_ok(s.torn, c.ini, c.fi) is False):
            fixades_tarda += 1
            continue
        if _torn_ok(s.torn, c.ini, c.fi) is False:
            if (c.data, c.ini) == (s.data, s.ini) and sid not in declarades:
                fora_torn_ja_avui += 1
            if sid not in declarades:
                continue
            motius = list(dict.fromkeys(r.justificacio for r in relax
                          if r.restriccio == 'R1-TORN' and (not r.sessions or sid in r.sessions)
                          and r.justificacio))
            motius = [MOTIU_S04526 if es_motiu_avaluacio(m) else m for m in motius]
            motiu = '; '.join(motius) or "No s'ha explicat per què"
            excepcions.append({'id_sessio': sid, 'cohorts': list(s.cohorts),
                               'torn_requerit': s.torn, 'motiu': motiu,
                               'prova': f'{c.data} {fmt(c.ini)}–{fmt(c.fi)}',
                               'prova_impossibilitat': None})
            for coh in set(s.cohorts):
                grups[motiu, coh] += 1
    for r in cohorts:
        r.update(afectades=afectades[r['cohort']],
                 afectades_pct=100 * afectades[r['cohort']] / r['sessions'], aula=canvis_aula[r['cohort']],
                 aula_pct=100 * canvis_aula[r['cohort']] / r['sessions'],
                 aules_assignades=assignades[r['cohort']],
                 nom=nom(r['cohort']), mogudes=mogudes[r['cohort']],
                 mogudes_pct=100 * mogudes[r['cohort']] / r['sessions'])
    if nom_proposta == '5.4':
        cohorts = [r for r in cohorts if r['cohort'].partition(':')[0] != 'GNOU']
    cohorts.sort(key=lambda r: (-r['afectades_pct'], -r['afectades'], r['cohort']))
    pitjor = max((r['mogudes_pct'] for r in cohorts), default=0)
    existents = [c for c in col.values() if not (nom_proposta == '5.4' and
                 any(coh.startswith('GNOU:') for coh in c.s.cohorts))]
    return {'versio_resum': VERSIO_RESUM, 'versio_calcul': VERSIO_CALCUL, 'data': datetime.now().astimezone().isoformat(timespec='seconds'),
            'proposta': nom_proposta,
            'veredicte': None, 'xifres': {},
            'canvis_franja': sum((c.data, c.ini) != (c.s.data, c.s.ini) for c in existents),
            'fora_torn_avui_compten': len(comptables),
            'fora_torn_avui_heretades': len(heretades),
            'aplica_torns_nous': nom_proposta not in ('Avui', '5.1'),
            'relaxacio_torn': any(r.restriccio == 'R1-TORN' for r in relax),
            'fora_torn_avui': sum(_torn_ok(s.torn, s.ini, s.fi) is False for s in base.sessions.values()
                                 if not (nom_proposta == '5.4' and any(c.startswith('GNOU:') for c in s.cohorts))),
            'fora_torn_proposta': sum(_torn_ok(c.s.torn, c.ini, c.fi) is False for c in col.values()
                                     if not (nom_proposta == '5.4' and any(coh.startswith('GNOU:') for coh in c.s.cohorts))),
            'canvis_aula': sum(bool(c.s.aula and not a_traslladar(c.s.aula) and not c.s.sense_espai and c.aula != c.s.aula) for c in col.values()),
            'aulari': aulari(base),
            'pics': pics_i_mides(base, model, col), 'sessions_mogudes': cohorts,
            'pitjor_cohort': [r['cohort'] for r in cohorts if r['mogudes_pct'] == pitjor],
            'excepcions': excepcions, 'fora_torn_ja_avui': fora_torn_ja_avui,
            'excepcions_aula': excepcions_aula,
            'marge_imprevistos': marge_imprevistos(base, col),
            'fixades_tarda': fixades_tarda,
            'excepcions_resum': [{'motiu': m, 'cohort': c, 'nom': nom(c), 'sessions': n,
                                  'percentatge': 100 * n / totals[c]}
                                 for (m, c), n in sorted(grups.items())],
            'torn_no_avaluable': sum(c.s.torn not in ('mati', 'tarda') for c in col.values()),
            'com_ho_hem_calculat': COM_HO_HEM_CALCULAT,
            'detall_tecnic': DETALL_TECNIC}


def data_planera(valor):
    moment = datetime.fromisoformat(valor)
    return moment.strftime('%d/%m/%Y %H:%M') if 'T' in valor else moment.strftime('%d/%m/%Y')


def setmana_planera(valor):
    if not valor:
        return 'sense classes'
    any_iso, setmana = valor.split('-W')
    return 'setmana del ' + date.fromisocalendar(int(any_iso), int(setmana), 1).strftime('%d/%m')


def resum_curs_afectat(d):
    cursos = d['sessions_mogudes']
    pitjor = max(cursos, key=lambda r: r['franja_pct'], default=None)
    if not pitjor or not pitjor['franja_pct']:
        aula = max(cursos, key=lambda r: r['aula_pct'], default=None)
        if aula and aula['aula_pct']:
            return (f"{aula['nom']}: {percentatge(aula['aula_pct'])} de les classes canvien d’aula "
                    f"({aula['aula']} de {aula['sessions']}); cap canvi de dia ni d’hora.")
        return "Cap curs canvia de dia ni d’hora."
    empatats = sum(r['franja_pct'] == pitjor['franja_pct'] for r in cursos) - 1
    torn = ('per passar al torn que els toca' if pitjor.get('torn') == pitjor['franja']
            else 'per fer encaixar l’horari')
    return (f"{pitjor['nom']}: {percentatge(pitjor['franja_pct'])} de les classes canvien de dia o hora "
            f"({pitjor['franja']} de {pitjor['sessions']}), {torn}"
            + (f'; i {empatats} cursos més amb el mateix percentatge' if empatats else '') + '.')


def resum_guany_torn(d):
    if 'fora_torn_avui' not in d or 'fora_torn_proposta' not in d:
        return ''
    detall = ''
    if 'fora_torn_avui_compten' in d:
        detall = (f" ({numero(d['fora_torn_avui_compten'])} compten al verificador; "
                  f"{numero(d['fora_torn_avui_heretades'])} són fixades heretades)")
    if d.get('proposta') == 'Avui':
        return f"{numero(d['fora_torn_avui'])} classes es fan avui fora del seu torn{detall}. Encara no s’apliquen els torns nous."
    return (f"Classes fora del seu torn: {numero(d['fora_torn_avui'])} avui{detall} → "
            f"{numero(d['fora_torn_proposta'])} amb aquesta proposta."
            + (' Aquesta proposta no aplica els torns nous.' if d.get('proposta') == '5.1' else ''))


def resum_escenari(d):
    if 'grau_nou' in d:
        g = d['grau_nou']
        resposta = 'Hi cap el grau nou de 40 places' if g['hi_cap'] else 'El grau nou de 40 places encara no hi cap'
        n = g['sessions_collocades']
        return (f"{resposta}: {n} {classe(n)} {'col·locada' if n == 1 else 'col·locades'}. "
                f"El pic del matí passa de {g['pic_mati_52']} a {g['pic_mati']} de {d['aulari']['disponibles']} aules. "
                + ('Cap classe de la resta es mou respecte de Torns nous (5.2).'
                   if g['sessions_52_mogudes'] == 0 else
                   f"{g['sessions_52_mogudes']} {classe(g['sessions_52_mogudes'])} de la resta "
                   f"es {'mou' if g['sessions_52_mogudes'] == 1 else 'mouen'} respecte de Torns nous (5.2)."))
    if 'vs_52' in d:
        v = d['vs_52']
        n = v['canvis_franja_vs_referencia']
        a = v.get('canvis_aula_oficials', v['canvis_aula_vs_referencia'])
        recuperades = v.get('canvis_aula_recuperades', 0)
        recuperacio = ("La classe cancel·lada es recupera un altre dia (canvia de dia i d’aula) i "
                       if recuperades == 1 and n == 1 else
                       f"{n} {classe(n)} canvien de dia o hora i ")
        return (f"Respecte de Torns nous (5.2): {recuperacio}{a} {classe(a)} més "
                f"{'canvia' if a == 1 else 'canvien'} d’aula "
                f"per {v['imprevistos']} {'imprevist' if v['imprevistos'] == 1 else 'imprevistos'}. "
                + resum_excepcions_aula(d))
    return ''


def resum_excepcions_aula(d):
    files = d.get('excepcions_aula', [])
    fixades = sum(r['nombre'] for r in files if r['restriccio'] == 'R1-FIXADA' and r['per_tancament'])
    labs = sum(r['nombre'] for r in files if r['restriccio'] == 'R7-PLAB' and r['per_tancament'])
    parts = []
    if fixades or labs:
        parts.append(f"{fixades} {'classe fixada' if fixades == 1 else 'classes fixades'} i "
                     f"{labs} {'laboratori' if labs == 1 else 'laboratoris'} canvien només d’aula perquè "
                     'la seva aula està tancada per l’imprevist (mateix dia i hora).')
    for r in files:
        if r['restriccio'] not in ('R1-FIXADA', 'R7-PLAB') or not r['per_tancament']:
            parts.append(f"{r['nombre']} {classe(r['nombre'])}: {r['motiu']}")
    return ' '.join(parts)


def resum_empitjora(d):
    x = d.get('xifres', {})
    parts = []
    for clau, etiqueta, unitat in [('hores_mortes_min', 'les esperes', ' min'),
                                   ('desplacaments_aula', 'els desplaçaments d’aula', ''),
                                   ('desplacaments_edifici', 'els canvis d’edifici', '')]:
        valors = x.get(clau)
        if not valors:
            continue
        a, b = valors['abans'], valors['despres']
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b > a:
            increment = f" (+{percentatge(round(100 * (b - a) / a))})" if a else ''
            parts.append(f"{etiqueta} passen de {numero(a)} a {numero(b)}{unitat}{increment}")
    return ('; '.join(parts) + '.') if parts else (
        'Cap augment en esperes ni desplaçaments.' if x else 'Sense comparació oficial d’esperes i desplaçaments disponible.')


def conclusio(d):
    parts = [d['veredicte'] + '.' if d.get('veredicte') else
             'Horari d’avui.' if d.get('proposta') == 'Avui' else 'Veredicte oficial no disponible.']
    if d.get('proposta') != 'Avui':
        parts.append(resum_canvis_aula(d))
        if d.get('canvis_franja_grau_nou'):
            parts.append(f"Dels canvis de dia o hora, {numero(d['canvis_franja_existents'])} són de cursos "
                         f"existents i {numero(d['canvis_franja_grau_nou'])} del grau nou respecte del seu horari inicial.")
        x = d.get('xifres', {})
        if 'aules_assignades' in x:
            n = x['aules_assignades']['despres']
            parts.append(f"{numero(n)} {classe(n)} {'rep' if n == 1 else 'reben'} aula.")
        millores = []
        for clau, etiqueta in [('R3-AFORAMENT', 'aforament'), ('R3-TIPUS', 'tipus d’aula'),
                               ('R2-FINESTRA', 'finestra horària')]:
            v = x.get('incompliments:' + clau)
            if v:
                millores.append(f"{etiqueta}: {numero(v['abans'])} → {numero(v['despres'])}")
        if millores:
            parts.append('Incompliments: ' + '; '.join(millores) + '.')
    parts += [titol_marge(d) + '.', explicacio_marge(d)]
    return parts


def documents(d):
    """Una mateixa pàgina de contingut per al Markdown i l’HTML imprimible."""
    proposta = d.get('proposta', 'Avui')
    titol = 'Resum per a la Junta · ' + NOMS_PROPOSTES.get(proposta, proposta)
    md = ['# ' + titol, '## Conclusió', *conclusio(d)]
    if proposta != 'Avui':
        md += ['## Què empitjora', resum_empitjora(d)]
    md += [
          ('Horari d’avui.' if proposta == 'Avui' else
           NOMS_PROPOSTES.get(proposta, proposta) + ' comparat amb l’horari d’avui.'),
          f"Data: {data_planera(d['data'])}"]
    if d.get('nota_pics'):
        md.append(d['nota_pics'])
    if resum_escenari(d):
        md.append(resum_escenari(d))
    md += [
          '## Aules ocupades a l’hora punta (per a la reserva)',
          'Mostrem quantes aules calen en el moment de més ocupació. Si falta assignar una aula, en fem una estimació.', explicacio_aulari(d),
          '| Torn | Màxim de la setmana més plena | Màxim d’una setmana habitual |', '|---|---|---|']
    for torn, nom_torn in [('mati', 'Matí'), ('tarda', 'Tarda')]:
        p, t = d['pics'][torn]['pitjor'], d['pics'][torn]['tipica']
        nom_torn += ' (estimació)' if p['estimacio'] else ''
        md.append(f"| {nom_torn} | {p['classes']}/{p['aules_disponibles']} · {setmana_planera(p['setmana'])} · {p['hora']} | {t['classes']}/{t['aules_disponibles']} · {setmana_planera(t['setmana'])} · {t['hora']} |")
    md += ['## Aules per nombre de places (estimació si falta aula)',
           f"L’ocupació indica les places de l’aula utilitzada. La demanda compta classes que necessiten almenys el mínim de places indicat, segons els alumnes; compartides un cop. + sobren aules; − en falten. Una aula gran pot acollir un grup petit. Guardem {d['aulari']['reserva']} aules de reserva. No s’han de sumar les files; no garanteix l’encaix de tot l’horari.",
           '| Places · mínim per comparar | Aules d’aquesta mida | Ocupades al màxim: matí / tarda | Matí: classes/aules prou grans (sobren o falten) | Tarda: classes/aules prou grans (sobren o falten) |', '|---|---|---|---|---|']
    for i, (_, _, mida) in enumerate(MIDES):
        vals = [d['pics'][t]['mides'][i] for t in ('mati', 'tarda')]
        llindar = ['Totes', '≥35', '≥51', '≥64', '≥91'][i]
        md.append('| ' + mida + ' · ' + llindar + f" | {vals[0]['aules_categoria']} | {vals[0]['ocupades_al_pic']} / {vals[1]['ocupades_al_pic']} | " + ' | '.join(
            f"{v['demanda_acumulada']}/{v['oferta_acumulada']} ({v['marge']:+})" for v in vals) + ' |')
    if proposta != 'Avui':
        md += ['## Classes que canvien', resum_canvis_aula(d),
           'Comptem les classes que canvien de dia, d’hora o d’aula. Ordenem pel percentatge total afectat, sense duplicar classes. Les aules assignades són per a classes que abans no en tenien. Els percentatges es calculen sobre totes les classes de cada titulació i curs.',
           '| Titulació i curs | Canvien de dia o hora | Canvien d’aula | Canvien de torn | Aules assignades |', '|---|---|---|---|---|']
        for r in d['sessions_mogudes']:
            md.append(f"| {r['nom']} | {percentatge(r['mogudes_pct'])} ({r['mogudes']}/{r['sessions']}) | " +
                  ' | '.join(f"{percentatge(r[c+'_pct'])} ({r[c]})" for c in ('aula', 'torn')) + f" | {r['aules_assignades']} |")
        if len(d['sessions_mogudes']) > 8:
            md.append('En paper: els vuit cursos amb més canvis. La resta es pot consultar a l’app.')
        md.append(resum_curs_afectat(d))
    md += [resum_guany_torn(d), '## Excepcions noves als torns', resum_excepcions(d)]
    if d['excepcions']:
        motius = defaultdict(list)
        for r in d['excepcions_resum']:
            motius[r['motiu']].append(f"{r['nom']}: {percentatge(r['percentatge'])} ({r['sessions']})")
        for motiu, files in motius.items():
            n = sum(e.get('motiu') == motiu for e in d['excepcions'])
            md.append(motiu_planer(motiu).rstrip('.') + f' ({n} {classe(n)}; ' + '; '.join(files) + ').')
    if d['fora_torn_ja_avui'] and proposta not in ('Avui', '5.1'):
        md.append(f"{d['fora_torn_ja_avui']} {classe(d['fora_torn_ja_avui'])} ja es {'fa' if d['fora_torn_ja_avui'] == 1 else 'fan'} avui fora del seu torn i no es {'toca' if d['fora_torn_ja_avui'] == 1 else 'toquen'}.")
    if d['torn_no_avaluable']:
        md.append(f"No podem comprovar el torn de {d['torn_no_avaluable']} {classe(d['torn_no_avaluable'])} perquè no tenen un torn definit.")
    md += ['## Com ho hem calculat', COM_HO_HEM_CALCULAT,
           '## Detall tècnic', '<small>', 'Empremta: ' + empremta_resum(d),
           d.get('detall_tecnic', DETALL_TECNIC)]
    md.append('</small>')
    # Petit renderitzador segur: tot text de la proposta s’escapa abans d’anar a HTML.
    html, taula = [], False
    cursos = False
    files_curs = 0
    for line in md:
        if line == '## Classes que canvien':
            cursos = True
        elif line.startswith('## ') and cursos:
            cursos = False
        if line == '## Detall tècnic':
            html.append('<section class="detall-tecnic">')
        if line in ('<small>', '</small>'):
            html.append(line)
            continue
        if line.startswith('|'):
            if not taula:
                html.append('<table>')
                taula = True
            if line.startswith('|---'):
                continue
            files_curs += int(cursos)
            classe_fila = ' class="nomes-pantalla"' if cursos and files_curs > 9 else ''
            html.append('<tr' + classe_fila + '>' + ''.join('<td>' + escape(c.strip()) + '</td>' for c in line.strip('|').split('|')) + '</tr>')
        else:
            if taula:
                html.append('</table>')
                taula = False
            tag = 'h1' if line.startswith('# ') else 'h2' if line.startswith('## ') else 'p'
            html.append(f'<{tag}>' + escape(line.lstrip('# ')).replace('**', '') + f'</{tag}>')
    html.append('</section>')
    css = '''@page{size:A4;margin:10mm}*{box-sizing:border-box}body{font-family:Arial,sans-serif;color:#172b38;margin:0;font-size:8pt;line-height:1.15}main{max-width:190mm;margin:auto}h1{font-size:17pt;margin:0 0 3mm}h2{font-size:10pt;margin:3mm 0 1mm}p{margin:1mm 0}table{width:100%;border-collapse:collapse;font-size:7.2pt}td{padding:1mm;border-bottom:1px solid #ccd5da}tr:first-child{font-weight:bold;background:#edf2f4}@media screen{body{background:#eee;padding:12mm}main{background:white;padding:8mm;max-width:210mm}}@media print{main{width:190mm}h2{break-after:avoid}tr{break-inside:avoid}}'''
    css += '.detall-tecnic{font-size:7pt}.detall-tecnic h2{font-size:8pt}'
    css += '@media print{body{font-size:7pt;line-height:1.1}h1{font-size:14pt;margin-bottom:2mm}h2{font-size:9pt;margin:2mm 0 1mm}p{margin:0.7mm 0}table{font-size:6.5pt}td{padding:0.6mm}main{break-inside:avoid}.detall-tecnic{display:none}}'
    css += '@media print{.nomes-pantalla{display:none}}'
    markdown = '\n'.join(line + ('' if line.startswith('|') else '\n') for line in md)
    return markdown + '\n', '<!doctype html><html lang="ca"><meta charset="utf-8"><title>' + escape(titol) + '</title><style>' + css + '</style><div id="page"><main>' + '\n'.join(html) + '</main></div>' + '</html>\n'



def resum_excepcions(d):
    n = len(d['excepcions'])
    if not d.get('relaxacio_torn', bool(d.get('fixades_tarda') or n)):
        if d.get('proposta') == '5.1':
            return ('Aquesta proposta no mou cap hora. Aquesta proposta no aplica els torns nous. '
                    + resum_excepcions_aula(d)).rstrip()
        return ('No hi ha excepcions noves als torns. ' + resum_excepcions_aula(d)).rstrip()
    noves = f"{n} excepció nova, demostrada" if n == 1 and d['excepcions'][0].get('motiu') == MOTIU_S04526 else f"{n} excepcions noves"
    return (noves + f"; {d.get('fixades_tarda', 0)} classes fixades que ja són a la tarda (regla 1). "
            + resum_excepcions_aula(d)).rstrip()


def empremta_resum(d):
    return hashlib.sha256(json.dumps({k: v for k, v in d.items() if k != 'empremta'}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def publica(desti, dades):
    """Escriu els tres formats amb la mateixa empremta i reemplaç atòmic per fitxer."""
    desti = Path(desti)
    desti.mkdir(parents=True, exist_ok=True)
    dades['empremta'] = empremta_resum(dades)
    md, html = documents(dades)
    for ext, contingut in [('md', md), ('html', html),
                           ('json', json.dumps(dades, ensure_ascii=False, indent=2))]:
        escriu_atomic(desti / f'junta.{ext}', contingut)
    # Migració de la publicació antiga: os.replace ja ha substituït els
    # enllaços públics per fitxers reals, sense seguir-los.
    actual = desti / '.actual'
    if actual.is_symlink():
        actual.unlink()
    for vell in desti.glob('.generacio-*'):
        if vell.is_symlink() or vell.is_file():
            vell.unlink()
        elif vell.is_dir():
            shutil.rmtree(vell)


def completa_escenari(d, nom_proposta, proposta, base, model, col, referencia):
    """Compara amb la 5.2 en memòria, sense alterar cap lliurament."""
    if nom_proposta == '5.3':
        # Import local: imprevistos comparteix els textos planers d’aquest mòdul.
        from nivell2.imprevistos import calcula as calcula_imprevistos
        resum = calcula_imprevistos(carrega_oficial(), base, referencia, proposta, [])
        d['vs_52'] = {k: resum['resum'][k] for k in
                      ('canvis_aula_vs_referencia', 'canvis_franja_vs_referencia')}
        recuperades = resum['resum']['canvis_aula_recuperades']
        d['vs_52']['canvis_aula_recuperades'] = recuperades
        # El verificador exclou del canvi d’aula les classes cancel·lades.
        d['vs_52']['canvis_aula_oficials'] = d['vs_52']['canvis_aula_vs_referencia'] - recuperades
        d['vs_52']['imprevistos'] = sum(t['sessions_afectades'] > 0 for t in resum['imprevistos'])
    elif nom_proposta == '5.4':
        ref_col = _col_loca(base, referencia.a_files(), InformeIntern())
        nous = {sid for sid, s in base.sessions.items() if any(c.startswith('GNOU:') for c in s.cohorts)}
        collocades = sum(sid in col and bool(col[sid].aula) for sid in nous)
        mogudes = sum((col[sid].data, col[sid].ini, col[sid].aula) !=
                      (c.data, c.ini, c.aula) for sid, c in ref_col.items())
        pic_52 = pics_i_mides(base, model, ref_col)['mati']['pitjor']['classes']
        d['grau_nou'] = {'hi_cap': collocades == len(nous), 'sessions_collocades': collocades,
                         'sessions_52_mogudes': mogudes, 'pic_mati_52': pic_52,
                         'pic_mati': d['pics']['mati']['pitjor']['classes']}


def completa_xifres(d, path):
    """Només llegeix derivats oficials; no regenera ni modifica lliuraments."""
    if not path.is_file():
        return
    def valor(text):
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return text
    with path.open(encoding='utf-8-sig', newline='') as f:
        d['xifres'] = {r['xifra']: {costat: valor(r[costat]) for costat in ('abans', 'despres')}
                       for r in csv.DictReader(f)}
    d['empremta_xifres'] = hashlib.sha256(path.read_bytes()).hexdigest()
    d['veredicte'] = d['xifres'].get('veredicte', {}).get('despres')
    # El verificador inclou també les sessions noves mogudes respecte de la
    # seva partida. Conservem el recompte dels cursos existents per separat.
    d['canvis_franja_existents'] = d['canvis_franja']
    for clau in ('canvis_franja', 'canvis_aula'):
        if clau in d['xifres']:
            d[clau] = d['xifres'][clau]['despres']
    if d['proposta'] == '5.4':
        d['canvis_franja_grau_nou'] = d['canvis_franja'] - d['canvis_franja_existents']


def genera(nom_proposta, *, resultats=None, sortida=None, proposta_path=None):
    resultats = Path(resultats) if resultats is not None else RESULTATS
    path = None if nom_proposta == 'Avui' else (Path(proposta_path) if proposta_path else resultats / nom_proposta / 'proposta.csv')
    referencia_path = resultats / '5.2' / 'proposta.csv'
    referencia_abans = empremtes(referencia_path) if nom_proposta in ('5.3', '5.4') and referencia_path.is_file() else None
    abans = empremtes(path)
    escenari = escenari_proposta(nom_proposta)
    base, model = carrega_oficial(escenari), carrega_model(escenari)
    if path is None:
        proposta = Proposta.de_base(base)
        col = _col_loca(base, proposta.a_files(), InformeIntern())
        relax = None
    else:
        proposta, col = carrega_proposta(path, base, escenari)
        relax = path.with_name('relaxacions.csv')
        relax = relax if relax.is_file() else None
    dades = calcula(proposta, base, model, col, relax, nom_proposta)
    if path is not None:
        completa_xifres(dades, path.with_name('xifres.csv'))
    elif (resultats / '5.1' / 'proposta.csv').is_file():
        path_51 = resultats / '5.1' / 'proposta.csv'
        empremta_51 = empremtes(path_51)
        _, col_51 = carrega_proposta(path_51, base)
        if all((col_51[sid].data, col_51[sid].ini) == (c.data, c.ini) for sid, c in col.items()):
            dades['pics'] = pics_i_mides(base, model, col_51)
            for torn in dades['pics'].values():
                for clau in ('pitjor', 'tipica'):
                    torn[clau]['estimacio'] = True
                for mida in torn['mides']:
                    mida['estimacio'] = True
            dades['nota_pics'] = 'Estimació amb l’assignació d’aules de la 5.1, que conserva els mateixos dies i hores.'
            dades['empremtes_assignacio_aules'] = empremta_51
        if empremtes(path_51) != empremta_51:
            raise ValueError('L’assignació d’aules ha canviat durant el càlcul')
    if referencia_abans is not None:
        referencia = Proposta.llegeix(referencia_path)
        # El segon semestre és l’àmbit del resum, també si el CSV en conté més.
        referencia.files = {sid: a for sid, a in referencia.files.items() if sid in base.sessions}
        proposta_semestre = Proposta({sid: a for sid, a in proposta.files.items() if sid in base.sessions})
        completa_escenari(dades, nom_proposta, proposta_semestre, base, model, col, referencia)
        if empremtes(referencia_path) != referencia_abans:
            raise ValueError('La proposta de referència ha canviat durant el càlcul')
        dades['empremtes_referencia'] = referencia_abans
    if empremtes(path) != abans:
        raise ValueError('Les fonts han canviat durant el càlcul')
    dades['empremtes'] = abans
    dades.setdefault('nota_pics', 'Sense aula assignada: estimació per instant.' if any(
        t['pitjor']['estimacio'] for t in dades['pics'].values()) else '')
    dades['mostrar_canvis'] = nom_proposta != 'Avui'
    dades['conclusio'] = conclusio(dades)
    dades['que_empitjora'] = resum_empitjora(dades)
    dades['resum_excepcions_aula'] = resum_excepcions_aula(dades)
    cursos = dades['sessions_mogudes']
    criteri = 'franja' if any(r['franja'] for r in cursos) else 'aula'
    dades['curs_mes_afectat'] = {'criteri': criteri, 'curs': max(
        (r for r in cursos if r[criteri + '_pct'] > 0), key=lambda r: r[criteri + '_pct'], default=None)}
    dades['cursos_afectats'] = [r for r in cursos if r['afectades_pct'] > 0]
    desti = Path(sortida) if sortida is not None else resultats / 'junta' / ('' if nom_proposta == 'Avui' else nom_proposta)
    publica(desti, dades)
    return dades


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('proposta', type=Path, nargs='?')
    parser.add_argument('--totes', action='store_true', help='Regenera Avui i les quatre propostes')
    parser.add_argument('--sortida', type=Path, default=RESULTATS / 'junta')
    args = parser.parse_args(argv)
    if args.totes and args.proposta:
        parser.error('Tria una proposta o --totes')
    try:
        noms = list(NOMS_PROPOSTES) if args.totes else [args.proposta.parent.name if args.proposta else 'Avui']
        for nom_proposta in noms:
            desti = args.sortida / nom_proposta if args.totes and nom_proposta != 'Avui' else args.sortida
            dades = genera(nom_proposta, sortida=desti, proposta_path=args.proposta,
                           resultats=args.proposta.parent.parent if args.proposta else RESULTATS)
            for torn in ('mati', 'tarda'):
                p = dades['pics'][torn]['pitjor']
                print(f"{nom_proposta}, {torn}: pic {p['classes']}/{p['aules_disponibles']}")
            print(f"{nom_proposta}: {dades.get('veredicte') or 'Horari actual'}; "
                  f"canvis de franja {dades['canvis_franja']}; d’aula {dades['canvis_aula']}; "
                  f"fora de torn avui {dades['fora_torn_avui']} "
                  f"(compten {dades['fora_torn_avui_compten']}, heretades {dades['fora_torn_avui_heretades']}); "
                  f"excepcions d’aula {sum(r['nombre'] for r in dades['excepcions_aula'])}")
            if dades['marge_imprevistos']:
                m = dades['marge_imprevistos']
                print(f"Marge amb imprevistos: {m['utilitzables']} utilitzables, "
                      f"{m['ocupades']} ocupades, {m['marge']} lliures fora de la reserva")
        print(f"{len(noms)} resums generats en JSON, Markdown i HTML")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'No s’ha pogut generar el resum: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
