"""Resum de decisió de la Junta; no substitueix el verificador oficial."""
from __future__ import annotations

import argparse
import json
import hashlib
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
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
        'MET': 'Màster en Enginyeria de Telecomunicació', 'MRICSE': 'Màster (pla 1530)'}


COM_HO_HEM_CALCULAT = (
    'Hem comptat les aules necessàries per a les classes del segon semestre, '
    'amb els dies i les hores de la proposta. '
    'Les places de les aules i els torns venen de les dades oficials; '
    'el nombre d’alumnes ve de les dades del model. '
    'Si una classe no té aula, estimem quantes places necessita. '
    'També comptem quines classes canvien de dia, d’hora o d’aula i quines queden fora del torn que els toca.')

DETALL_TECNIC = (
                'Segon semestre; hores proposades; franges d’una hora des de les 8.30 '
                '(última: 20.30–21); aules ordinàries diferents ocupades (R8). Sense aula: estimació de demanda ordinària, sense PLAB, dobles sense espai, seminaris, laboratoris ni aules externes de partida. Mides segons les places de l’aula ocupada; sense aula, alumnes estimats. Compartides un cop i alumnes sumats; sense laboratoris '
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


VERSIO_RESUM = 3
VERSIO_CALCUL = 1
MOTIU_S04526 = ("A la setmana d’avaluació no hi ha cap franja de tarda lliure "
                "per a aquesta classe; ho demostra el càlcul.")


def classe(n):
    return 'classe' if n == 1 else 'classes'


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


def motiu_planer(text):
    if 'diagnostic.md' in text or 'S04526' in text:
        return MOTIU_S04526
    for tecnic, planer in [('R1-TORN', 'regla de torn'), ('PLAB', 'laboratori'),
                           ('TE/', 'grup '), ('PAUL', 'problemes'), ('SEM', 'seminari'),
                           (' J ', ' d’un altre edifici '), ('R8', 'reserva d’aules'),
                           ('llindar', 'mínim'), ('cota', 'estimació')]:
        text = text.replace(tecnic, planer)
    return text


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
    n = d['aulari']['disponibles']
    return f'Per què {n} de {n} no és prou'


def explicacio_marge(d):
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
        if c.s.tipus != 'PLAB' and not c.s.sense_espai:
            unitats[c.s.unitat].append((sid, c))
    ocupacio = defaultdict(dict)
    estimacions = set()
    ordinaries = {a for a, x in base.aules.items() if x.ordinaria}
    maxim = aulari(base)['disponibles']
    alumnes_unitat = {u: sum(model.sessions[sid].alumnes for sid, _ in membres)
                      for u, membres in unitats.items()}
    # R8 compta aules diferents durant tota l'hora, també si dues classes
    # successives comparteixen aula. Les sessions sense aula són demanda estimada.
    for sid, c in col.items():
        if c.s.sense_espai or (nomes_mati_requerit and c.s.torn != 'mati'):
            continue
        estimada = (not c.aula and c.s.tipus != 'PLAB'
                    and (not c.s.aula or c.s.aula in ordinaries or a_traslladar(c.s.aula)))
        if c.aula not in ordinaries and not estimada:
            continue
        for h in range(510, 1260, 60):
            if c.ini < h + 60 and c.fi > h:
                clau = ('estimada', c.s.unitat) if estimada else ('aula', c.aula)
                ocupacio[c.data, h][clau] = (alumnes_unitat[c.s.unitat] if estimada
                                                   else base.aules[c.aula].capacitat)
                if estimada:
                    estimacions.add((c.data, h))
    # Escombrat per instant, amb finals abans dels inicis i compartides un cop.
    simultanies = defaultdict(list)
    for c in col.values():
        if c.s.sense_espai or c.s.tipus == 'PLAB':
            continue
        if c.aula not in ordinaries and not (not c.aula and
                (not c.s.aula or c.s.aula in ordinaries or a_traslladar(c.s.aula))):
            continue
        if nomes_mati_requerit and c.s.torn != 'mati':
            continue
        simultanies[c.data].append(c)
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
            demanda = max((sum(n >= max(1, baix) for n in v.values()) for _, _, v in pics), default=0)
            # El primer llindar inclou també els grups encara sense dada.
            if baix == 0:
                demanda = max((len(v) for _, _, v in pics), default=0)
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


def calcula(proposta, base, model, col, relaxacions=None):
    _, cohorts = calcula_xifres(proposta, base, Informe(
        {'veredicte': 'No s’ha verificat aquí', 'restriccions': {}, 'objectius': {}}, ''))
    totals = {r['cohort']: r['sessions'] for r in cohorts}
    mogudes, canvis_aula, assignades = Counter(), Counter(), Counter()
    excepcions, grups = [], Counter()
    fora_torn_ja_avui = 0
    afectades = Counter()
    relax = llegeix_relaxacions(relaxacions)
    informe = avalua(base, proposta.a_files(), relaxacions=relax)
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
        if _torn_ok(s.torn, c.ini, c.fi) is False:
            if (c.data, c.ini) == (s.data, s.ini) and sid not in declarades:
                fora_torn_ja_avui += 1
            if sid not in declarades:
                continue
            motius = list(dict.fromkeys(r.justificacio for r in relax
                          if r.restriccio == 'R1-TORN' and (not r.sessions or sid in r.sessions)
                          and r.justificacio))
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
    cohorts.sort(key=lambda r: (-r['afectades_pct'], -r['afectades'], r['cohort']))
    pitjor = max((r['afectades_pct'] for r in cohorts), default=0)
    return {'versio_resum': VERSIO_RESUM, 'versio_calcul': VERSIO_CALCUL, 'data': datetime.now().astimezone().isoformat(timespec='seconds'),
            'aulari': aulari(base),
            'pics': pics_i_mides(base, model, col), 'sessions_mogudes': cohorts,
            'pitjor_cohort': [r['cohort'] for r in cohorts if r['afectades_pct'] == pitjor],
            'excepcions': excepcions, 'fora_torn_ja_avui': fora_torn_ja_avui,
            'excepcions_resum': [{'motiu': m, 'cohort': c, 'nom': nom(c), 'sessions': n,
                                  'percentatge': 100 * n / totals[c]}
                                 for (m, c), n in sorted(grups.items())],
            'torn_no_avaluable': sum(c.s.torn not in ('mati', 'tarda') for c in col.values()),
            'com_ho_hem_calculat': COM_HO_HEM_CALCULAT,
            'detall_tecnic': DETALL_TECNIC}


def documents(d):
    """Una mateixa pàgina de contingut per al Markdown i l’HTML imprimible."""
    md = ['# Resum per a la Junta', f"Data: {d['data'][:10]}",
          '## Aules ocupades a l’hora punta (per a la reserva)',
          'Mostrem quantes aules calen en el moment de més ocupació. Si falta assignar una aula, en fem una estimació.', explicacio_aulari(d),
          '| Torn | Màxim de la setmana més plena | Màxim d’una setmana habitual |', '|---|---|---|']
    for torn, nom_torn in [('mati', 'Matí'), ('tarda', 'Tarda')]:
        p, t = d['pics'][torn]['pitjor'], d['pics'][torn]['tipica']
        nom_torn += ' (estimació)' if p['estimacio'] else ' (aules per a classes)'
        md.append(f"| {nom_torn} | {p['classes']}/{p['aules_disponibles']} · {p['setmana']} · {p['hora']} | {t['classes']}/{t['aules_disponibles']} · {t['setmana']} · {t['hora']} |")
    md += ['## Màxim de classes alhora']
    for torn, etiqueta in [('mati', 'Matí'), ('tarda', 'Tarda')]:
        p = d['pics'][torn].get('simultani')
        if p:
            md.append(f"{etiqueta}: {p['classes']} {classe(p['classes'])} · {p['hora']}. Comptem per instant les classes que necessiten aula ordinària, amb les compartides un cop.")
    md += ['## Aules per nombre de places (estimació si falta aula)',
           f"La mida indica les places de l’aula; si encara no en té, indica els alumnes previstos. Les aules ocupades per mida sumen el màxim de cada torn. Comparem també les classes i les aules prou grans: + vol dir que sobren aules; − vol dir que en falten. Una aula gran pot acollir un grup petit. Cal guardar {d['aulari']['reserva']} aules de reserva. No s’han de sumar els resultats de les files. Aquest recompte no garanteix que tot l’horari encaixi.",
           '| Places · mínim per comparar | Aules d’aquesta mida | Ocupades al màxim: matí / tarda | Matí: classes/aules prou grans (sobren o falten) | Tarda: classes/aules prou grans (sobren o falten) |', '|---|---|---|---|---|']
    for i, (_, _, mida) in enumerate(MIDES):
        vals = [d['pics'][t]['mides'][i] for t in ('mati', 'tarda')]
        llindar = ['Totes', '≥35', '≥51', '≥64', '≥91'][i]
        md.append('| ' + mida + ' · ' + llindar + f" | {vals[0]['aules_categoria']} | {vals[0]['ocupades_al_pic']} / {vals[1]['ocupades_al_pic']} | " + ' | '.join(
            f"{v['demanda_acumulada']}/{v['oferta_acumulada']} ({v['marge']:+})" for v in vals) + ' |')
    md += ['## Classes que canvien',
           'Comptem les classes que canvien de dia, d’hora o d’aula. Ordenem pel percentatge total afectat, sense duplicar classes. Les aules assignades són per a classes que abans no en tenien. Els percentatges es calculen sobre totes les classes de cada titulació i curs.',
           '| Titulació i curs | Canvien de dia o hora | Canvien d’aula | Canvien de torn | Aules assignades |', '|---|---|---|---|---|']
    for r in d['sessions_mogudes']:
        md.append(f"| {r['nom']} | {percentatge(r['mogudes_pct'])} ({r['mogudes']}/{r['sessions']}) | " +
                  ' | '.join(f"{percentatge(r[c+'_pct'])} ({r[c]})" for c in ('aula', 'torn')) + f" | {r['aules_assignades']} |")
    pitjors = [r for r in d['sessions_mogudes'] if r['cohort'] in d['pitjor_cohort']]
    md.append("Cap curs canvia de dia ni d'hora." if all(r.get('afectades', r['mogudes']) == 0 for r in pitjors)
              else 'Percentatge més alt: ' + '; '.join(f"{r['nom']}: {percentatge(r.get('afectades_pct', r['mogudes_pct']))} ({r.get('afectades', r['mogudes'])})" for r in pitjors) + '.')
    md += ['## Excepcions noves als torns']
    if not d['excepcions']:
        md.append('No hi ha excepcions noves als torns.')
    else:
        md.append(f"{len(d['excepcions'])} {classe(len(d['excepcions']))} amb una excepció declarada al torn que els toca. Sabem a quina hora es fan, però això no demostra que sigui impossible canviar-les. Els motius consten al detall tècnic.")
        motius = defaultdict(list)
        for r in d['excepcions_resum']:
            motius[r['motiu']].append(f"{r['nom']}: {percentatge(r['percentatge'])} ({r['sessions']})")
        for motiu, files in motius.items():
            n = sum(e.get('motiu') == motiu for e in d['excepcions'])
            md.append(motiu_planer(motiu) + f' ({n} {classe(n)}): ' + '; '.join(files) + '.')
    for e in d['excepcions']:
        if e.get('id_sessio') == 'S04526':
            md.append('Cas S04526: ' + MOTIU_S04526)
    if d['fora_torn_ja_avui']:
        md.append(f"{d['fora_torn_ja_avui']} {classe(d['fora_torn_ja_avui'])} ja es {'fa' if d['fora_torn_ja_avui'] == 1 else 'fan'} avui fora del seu torn i no es {'toca' if d['fora_torn_ja_avui'] == 1 else 'toquen'}.")
    if d['torn_no_avaluable']:
        md.append(f"No podem comprovar el torn de {d['torn_no_avaluable']} {classe(d['torn_no_avaluable'])} perquè no tenen un torn definit.")
    md += ['## Com ho hem calculat', COM_HO_HEM_CALCULAT,
           '## Detall tècnic', '<small>',
           '## ' + titol_marge(d), explicacio_marge(d),
           d.get('detall_tecnic', DETALL_TECNIC)]
    for r in d['excepcions_resum']:
        md.append(r['motiu'] + ': ' + r['nom'] + f": {percentatge(r['percentatge'])} ({r['sessions']}).")
    md.append('</small>')
    # Petit renderitzador segur: tot text de la proposta s’escapa abans d’anar a HTML.
    html, taula = [], False
    for line in md:
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
            html.append('<tr>' + ''.join('<td>' + escape(c.strip()) + '</td>' for c in line.strip('|').split('|')) + '</tr>')
        else:
            if taula:
                html.append('</table>')
                taula = False
            tag = 'h1' if line.startswith('# ') else 'h2' if line.startswith('## ') else 'p'
            html.append(f'<{tag}>' + escape(line.lstrip('# ')).replace('**', '') + f'</{tag}>')
    html.append('</section>')
    css = '''@page{size:A4;margin:10mm}*{box-sizing:border-box}body{font-family:Arial,sans-serif;color:#172b38;margin:0;font-size:8pt;line-height:1.15}main{max-width:190mm;margin:auto}h1{font-size:17pt;margin:0 0 3mm}h2{font-size:10pt;margin:3mm 0 1mm}p{margin:1mm 0}table{width:100%;border-collapse:collapse;font-size:7.2pt}td{padding:1mm;border-bottom:1px solid #ccd5da}tr:first-child{font-weight:bold;background:#edf2f4}@media screen{body{background:#eee;padding:12mm}main{background:white;padding:8mm;max-width:210mm}}@media print{main{width:190mm}h2{break-after:avoid}tr{break-inside:avoid}}'''
    css += '.detall-tecnic{font-size:7pt}.detall-tecnic h2{font-size:8pt}'
    css += '@media print{#page{width:190mm;height:277mm}}'
    ajust = '''<script>
window.addEventListener('beforeprint', () => {
  const main = document.querySelector('main');
  main.style.zoom = 1;
  const available = document.querySelector('#page').clientHeight;
  main.style.zoom = Math.min(1, (available - 2) / main.scrollHeight);
});
</script>'''
    markdown = '\n'.join(line + ('' if line.startswith('|') else '\n') for line in md)
    return markdown + '\n', '<!doctype html><html lang="ca"><meta charset="utf-8"><title>Resum per a la Junta</title><style>' + css + '</style><div id="page"><main>' + '\n'.join(html) + '</main></div>' + ajust + '</html>\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('proposta', type=Path)
    parser.add_argument('--sortida', type=Path, default=RESULTATS / 'junta')
    args = parser.parse_args(argv)
    try:
        escenari = escenari_proposta(args.proposta.parent.name)
        base, model = carrega_oficial(escenari), carrega_model(escenari)
        abans = empremtes(args.proposta)
        proposta, col = carrega_proposta(args.proposta, base, escenari)
        relax = args.proposta.parent / 'relaxacions.csv'
        dades = calcula(proposta, base, model, col, relax if relax.exists() else None)
        if empremtes(args.proposta) != abans:
            raise ValueError('Les fonts han canviat durant el càlcul')
        dades['empremtes'] = abans
        md, html = documents(dades)
        args.sortida.mkdir(parents=True, exist_ok=True)
        for nom_fitxer, text in [('junta.json', json.dumps(dades, ensure_ascii=False, indent=2)),
                                 ('junta.md', md), ('junta.html', html)]:
            escriu_atomic(args.sortida / nom_fitxer, text)
        for torn in ('mati', 'tarda'):
            resum = dades['pics'][torn]
            etiqueta = ' (estimació)' if resum['pitjor']['estimacio'] else ''
            maxim = resum['pitjor']['aules_disponibles']
            print(f"{torn}{etiqueta}: pic {resum['pitjor']['classes']}/{maxim}; "
                  f"total taula de mides {resum['total_mides']}/{maxim}")
        print(f"Resum escrit a {args.sortida}: junta.json, junta.md i junta.html")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'No s’ha pogut generar el resum: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
