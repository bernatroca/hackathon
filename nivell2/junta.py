"""Resum de decisió de la Junta; no substitueix el verificador oficial."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from statistics import median

from nivell2.base import (Informe, RESULTATS, Proposta, carrega_model,
                         carrega_oficial, fmt)
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


def nom(cohort):
    tit, _, curs = cohort.partition(':')
    sufix = ', curs desconegut' if curs == '?' else f', {curs}' if curs not in ('', 'M') else ''
    return NOMS.get(tit, f'Titulació {tit}') + sufix


def carrega_proposta(path, base):
    """Rebutja errors estructurals; ignora les files d'altres semestres com el jurat."""
    files = llegeix_proposta(Path(path))
    altres = {f.id for f in files} - base.sessions.keys()
    if altres:
        conegudes = carrega_oficial(semestre=None).sessions
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

    Les mides acumulades són cotes amb reserva flexible: min(19, aules prou
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
    out = {}
    for torn, ini, fi in [('mati', 510, 870), ('tarda', 870, 1260)]:
        pics = [(d, h, v) for (d, h), v in ocupacio.items() if ini <= h < fi]
        def pic(rows):
            d, h, v = min(rows, key=lambda r: (-len(r[2]), r[0], r[1])) if rows else (None, ini, {})
            return {'classes': len(v), 'aules_disponibles': 19,
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
            disponibles = min(19, sum(a.capacitat >= baix for a in base.aules.values() if a.ordinaria))
            mides.append({'mida': etiqueta, 'pic_categoria': exacta,
                          'ocupades_al_pic': sum(baix <= n <= alt for n in al_pic.values()),
                          'estimacio': any((d, h) in estimacions for d, h, _ in pics),
                          'aules_categoria': oferta,
                          'minim_places': baix, 'demanda_acumulada': demanda,
                          'oferta_acumulada': disponibles, 'marge': disponibles - demanda,
                          'falten': max(0, demanda - disponibles),
                          'sobren': max(0, disponibles - demanda)})
        out[torn] = {'pitjor': pic(pics),
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
    relax = llegeix_relaxacions(relaxacions)
    for sid, c in col.items():
        s = c.s
        if (c.data, c.ini) != (s.data, s.ini):
            mogudes.update(set(s.cohorts))
        if s.aula and not a_traslladar(s.aula) and not s.sense_espai and c.aula != s.aula:
            canvis_aula.update(set(s.cohorts))
        if not s.aula and c.aula and not s.sense_espai:
            assignades.update(set(s.cohorts))
        if _torn_ok(s.torn, c.ini, c.fi) is False:
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
        r.update(aula=canvis_aula[r['cohort']],
                 aula_pct=100 * canvis_aula[r['cohort']] / r['sessions'],
                 aules_assignades=assignades[r['cohort']],
                 nom=nom(r['cohort']), mogudes=mogudes[r['cohort']],
                 mogudes_pct=100 * mogudes[r['cohort']] / r['sessions'])
    pitjor = max((r['mogudes_pct'] for r in cohorts), default=0)
    return {'data': datetime.now().astimezone().isoformat(timespec='seconds'),
            'pics': pics_i_mides(base, model, col), 'sessions_mogudes': cohorts,
            'pitjor_cohort': [r['cohort'] for r in cohorts if r['mogudes_pct'] == pitjor],
            'excepcions': excepcions,
            'excepcions_resum': [{'motiu': m, 'cohort': c, 'nom': nom(c), 'sessions': n,
                                  'percentatge': 100 * n / totals[c]}
                                 for (m, c), n in sorted(grups.items())],
            'torn_no_avaluable': sum(c.s.torn not in ('mati', 'tarda') for c in col.values()),
            'com_ho_hem_calculat': (
                'Segon semestre; hores proposades; franges d’una hora des de les 8.30 '
                '(última: 20.30–21); aules ordinàries diferents ocupades (R8). Sense aula: estimació de demanda ordinària, sense PLAB, dobles sense espai, seminaris, laboratoris ni aules externes de partida. Mides segons les places de l’aula ocupada; sense aula, alumnes estimats. Compartides un cop i alumnes sumats; sense laboratoris '
                'ni dobles sense espai per a la demanda. Setmana típica: sessions més properes '
                'a la mediana, desempat per la primera. Pitjor setmana: pic màxim de cada torn. '
                'Torns de la base oficial, segons l’hora d’inici. Alumnes de la base del model. '
                'Sessió moguda: canvi de dia o hora; canvi d’aula només si ja en tenia, sense J ni dobles sense espai; denominador: totes les sessions de cada titulació i curs. '
                'Les compartides compten en cada titulació. Excepcions: totes les sessions fora de torn, '
                'incloses les heretades que el verificador pot no penalitzar. No és una validació de l’horari.')}


def documents(d):
    """Una mateixa pàgina de contingut per al Markdown i l’HTML imprimible."""
    md = ['# Resum per a la Junta', f"Data: {d['data'][:10]}",
          '## Pic d’aules ordinàries',
          'Comptem les aules ordinàries diferents ocupades durant cada hora. Sense aula assignada, estimem la demanda ordinària.', '21 aules ordinàries − 2 de reserva = **19 disponibles**.',
          '| Torn | Pitjor setmana: pic | Setmana típica: pic |', '|---|---|---|']
    for torn, nom_torn in [('mati', 'Matí'), ('tarda', 'Tarda')]:
        p, t = d['pics'][torn]['pitjor'], d['pics'][torn]['tipica']
        nom_torn += ' (estimació)' if p['estimacio'] else ' (aules ordinàries)'
        md.append(f"| {nom_torn} | {p['classes']}/19 · {p['setmana']} · {p['hora']} | {t['classes']}/19 · {t['setmana']} · {t['hora']} |")
    md += ['## Aules ordinàries per mida (estimació si falta aula)',
           'Les mides són les places de l’aula assignada; sense aula, les dels alumnes (estimació). Les ocupades al pic se sumen i coincideixen amb el pic del torn. Marge al pitjor moment del semestre: + sobren; − falten. Llindars acumulats: una aula gran pot acollir un grup petit. Reserva flexible de dues aules; cota optimista, no garantia d’encaix. No se sumen els marges.',
           '| Places | Aules ordinàries | Ocupades al pic matí / tarda | Matí: demanda/oferta (marge) acumulats | Tarda: demanda/oferta (marge) acumulats |', '|---|---|---|---|---|']
    for i, (_, _, mida) in enumerate(MIDES):
        vals = [d['pics'][t]['mides'][i] for t in ('mati', 'tarda')]
        llindar = ['Totes', '≥35', '≥51', '≥64', '≥91'][i]
        md.append('| ' + mida + ' · ' + llindar + f" | {vals[0]['aules_categoria']} | {vals[0]['ocupades_al_pic']} / {vals[1]['ocupades_al_pic']} | " + ' | '.join(
            f"{v['demanda_acumulada']}/{v['oferta_acumulada']} ({v['marge']:+})" for v in vals) + ' |')
    md += ['## Sessions mogudes',
           'Sessions mogudes: canvi de dia o hora. Aules assignades: abans sense aula; no són canvis. Percentatge i nombre sobre les seves sessions.',
           '| Titulació i curs | Canvien de franja | Canvien d’aula | Canvien de torn | Aules assignades |', '|---|---|---|---|---|']
    for r in d['sessions_mogudes']:
        md.append(f"| {r['nom']} | {r['mogudes_pct']:.1f}% ({r['mogudes']}/{r['sessions']}) | " +
                  ' | '.join(f"{r[c+'_pct']:.1f}% ({r[c]})" for c in ('aula', 'torn')) + f" | {r['aules_assignades']} |")
    pitjors = [r for r in d['sessions_mogudes'] if r['cohort'] in d['pitjor_cohort']]
    md.append('Cap sessió moguda; totes les titulacions i cursos empaten al 0%.' if all(r['mogudes'] == 0 for r in pitjors)
              else 'Pitjor percentatge: ' + '; '.join(f"{r['nom']}: {r['mogudes_pct']:.1f}% ({r['mogudes']})" for r in pitjors) + '.')
    md += ['## Excepcions al torn requerit']
    if not d['excepcions']:
        md.append('No hi ha cap sessió fora del torn requerit.')
    else:
        md.append(f"{len(d['excepcions'])} sessions fora de torn. L’hora acredita l’incompliment, no la impossibilitat de corregir-lo. Detall individual i hores a junta.json.")
        motius = defaultdict(list)
        for r in d['excepcions_resum']:
            motius[r['motiu']].append(f"{r['nom']}: {r['percentatge']:.1f}% ({r['sessions']})")
        for motiu, files in motius.items():
            md.append(motiu + ': ' + '; '.join(files) + '.')
    if d['torn_no_avaluable']:
        md.append(f"Torn no avaluable: {d['torn_no_avaluable']} sessions sense torn definit.")
    md += ['## Com ho hem calculat', d['com_ho_hem_calculat']]
    # Petit renderitzador segur: tot text de la proposta s’escapa abans d’anar a HTML.
    html, taula = [], False
    for line in md:
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
    css = '''@page{size:A4;margin:10mm}*{box-sizing:border-box}body{font-family:Arial,sans-serif;color:#172b38;margin:0;font-size:8pt;line-height:1.15}main{max-width:190mm;margin:auto}h1{font-size:17pt;margin:0 0 3mm}h2{font-size:10pt;margin:3mm 0 1mm}p{margin:1mm 0}table{width:100%;border-collapse:collapse;font-size:7.2pt}td{padding:1mm;border-bottom:1px solid #ccd5da}tr:first-child{font-weight:bold;background:#edf2f4}@media screen{body{background:#eee;padding:12mm}main{background:white;padding:8mm;max-width:210mm}}@media print{main{width:190mm}h2{break-after:avoid}tr{break-inside:avoid}}'''
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
        base, model = carrega_oficial(), carrega_model()
        proposta, col = carrega_proposta(args.proposta, base)
        relax = args.proposta.parent / 'relaxacions.csv'
        dades = calcula(proposta, base, model, col, relax if relax.exists() else None)
        md, html = documents(dades)
        args.sortida.mkdir(parents=True, exist_ok=True)
        for nom_fitxer, text in [('junta.json', json.dumps(dades, ensure_ascii=False, indent=2)),
                                 ('junta.md', md), ('junta.html', html)]:
            (args.sortida / nom_fitxer).write_text(text, encoding='utf-8')
        for torn in ('mati', 'tarda'):
            resum = dades['pics'][torn]
            etiqueta = ' (estimació)' if resum['pitjor']['estimacio'] else ''
            print(f"{torn}{etiqueta}: pic {resum['pitjor']['classes']}/19; "
                  f"total taula de mides {resum['total_mides']}/19")
        print(f"Resum escrit a {args.sortida}: junta.json, junta.md i junta.html")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'No s’ha pogut generar el resum: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
