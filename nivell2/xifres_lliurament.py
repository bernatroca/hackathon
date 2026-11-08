"""Artifacts de lliurament calculats exclusivament dels CSV finals."""
import csv
import json
from html import escape

from nivell2.base import Proposta, carrega_oficial, GRAU_NOU
from nivell2.verificacio import opcions_pregunta
from nivell2.xifres import compara
from nivell2.readmes import normalitza, explica_comptatge


def genera(pregunta, arrel):
    out = arrel / pregunta
    comparison = compara(Proposta.llegeix(out / 'proposta.csv'),
                         proposta_path=out / 'proposta.csv',
                         **opcions_pregunta(pregunta, arrel))
    rows = list(comparison.files)
    seen = {row['xifra'] for row in rows}
    if pregunta == '5.4' and (out / 'resum.json').is_file():
        summary = json.loads((out / 'resum.json').read_text(encoding='utf-8'))
        for key in ('sessions_grau_nou_fora_franja', 'sessions_52_mogudes'):
            if key not in seen and key in summary:
                rows.append({'xifra': key, 'abans': 0, 'despres': summary[key]})
                seen.add(key)
    # Migra també els lliuraments ja generats sense tornar a executar el solver.
    summary_path = out / 'resum.json'
    if pregunta == '5.3' and summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        if 'comparacio_anterior' in summary:
            execution_path = out / 'execucio.json'
            execution = json.loads(execution_path.read_text(encoding='utf-8')) if execution_path.is_file() else {}
            execution['comparacio_anterior'] = summary.pop('comparacio_anterior')
            execution_path.write_text(json.dumps(execution, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (out / 'xifres.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['xifra', 'abans', 'despres'])
        writer.writeheader()
        writer.writerows(rows)
    path = out / 'README.md'
    text = path.read_text(encoding='utf-8')
    import re
    explanations = {}
    for line in text.splitlines():
        match = re.fullmatch(r'- (.*): ([^;]+); (.+)', line)
        if match:
            explanations[(match[1], match[2])] = match[3]
    text = re.sub(r'(?:\A|\n)## Què empitjora i per què\n.*?(?=\n## |\Z)', '', text, flags=re.S)
    text = normalitza(text, pregunta, arrel)
    text = explica_comptatge(text, comptatge_verificador(pregunta, arrel), pregunta)
    lines = []
    neutral = {'sessions_avaluades', 'aules_assignades', 'relaxacions_declarades'}
    for row in comparison.files:
        key, a, d = row['xifra'], row['abans'], row['despres']
        if isinstance(a, (int, float)) and isinstance(d, (int, float)):
            worse = d < a if key == 'activitats_rutinaries_pct' else d > a
            if worse and key not in neutral:
                explanation = explanations.get((key, f'{a} → {d}'), 'per explicar.')
                lines.append(f'- {key}: {a} → {d}; {explanation}')
    path.write_text(text.rstrip() + '\n\n## Què empitjora i per què\n\n' +
                    ('\n'.join(lines) if lines else 'Cap empitjorament numèric detectat.') + '\n', encoding='utf-8')


def graelles(sortida, arrel):
    # Carrega el component sense importar l'entrada Streamlit app.py.
    import importlib.util
    import sys
    from nivell2.base import ARREL
    spec = importlib.util.spec_from_file_location('_graella_lliurament', ARREL / 'app/components/graella.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    exporta_aula_html, setmana_tipica = module.exporta_aula_html, module.setmana_tipica
    base = carrega_oficial(GRAU_NOU)
    proposta = Proposta.llegeix(arrel / '5.4/proposta.csv')
    setmana = setmana_tipica(base)
    folder = sortida / 'graelles'
    folder.mkdir(parents=True, exist_ok=True)
    links = []
    for i, aula in enumerate(sorted(base.aules)):
        name = f'aula-{i:03d}.html'
        (folder / name).write_text(exporta_aula_html(base, proposta, setmana, aula), encoding='utf-8')
        links.append(f'<li><a href="{name}">{escape(aula)}</a></li>')
    (folder / 'index.html').write_text('<!doctype html><html lang="ca"><meta charset="utf-8"><title>Graelles 5.4</title><h1>Graelles 5.4</h1><p>Setmana del ' + str(setmana) + '</p><ul>' + ''.join(links) + '</ul></html>', encoding='utf-8')
    return folder


def comptatge_verificador(pregunta, arrel):
    """Només recomptes: mateixa col·locació i ordre estable que check.py."""
    from collections import defaultdict
    from horaris.check import Informe, _col_loca, _objectius, _vs_referencia

    opcions = opcions_pregunta(pregunta, arrel)
    base = carrega_oficial(opcions.get('escenari'))
    proposta = Proposta.llegeix(arrel / pregunta / 'proposta.csv')
    # El costat abans és la referència 5.2 si hi és; altrament, l’horari de partida.
    referencia = (Proposta.llegeix(opcions['referencia']) if opcions.get('referencia')
                  else Proposta.de_base(carrega_oficial()))
    col = _col_loca(base, proposta.a_files(), Informe())
    base_partida = carrega_oficial()
    partida = _col_loca(base_partida, referencia.a_files(), Informe())

    def simultanis(placements):
        agenda = defaultdict(list)
        for c in placements.values():
            for coh in c.s.cohorts:
                agenda[coh, c.s.linia, c.data, c.s.num_grup if c.s.tipus != 'TE' else '*'].append(c)
        linies = defaultdict(set)
        for coh, linia, data, grup in agenda:
            linies[coh, linia, data].add(grup)
        total = 0
        for key, grups in linies.items():
            for grup in (grups - {'*'} or {'*'}):
                classes = agenda.get((*key, '*'), []) + (agenda[(*key, grup)] if grup != '*' else [])
                classes = sorted({id(c): c for c in classes}.values(), key=lambda c: c.ini)
                total += sum(a.ini == b.ini and bool(a.aula and b.aula) and a.aula != b.aula
                             for a, b in zip(classes, classes[1:]))
        return total

    sense_dobles = {sid: c for sid, c in col.items() if not c.s.sense_espai}
    x = {'simultanis_proposta': simultanis(col), 'simultanis_partida': simultanis(partida),
         'te_partida': _objectius(base_partida, partida)['r6_aules_te_extra_per_grup'],
         'te_partida_sense_dobles': _objectius(base_partida, {sid: c for sid, c in partida.items() if not c.s.sense_espai})['r6_aules_te_extra_per_grup'],
         'te_oficial': _objectius(base, col)['r6_aules_te_extra_per_grup'],
         'te_sense_dobles': _objectius(base, sense_dobles)['r6_aules_te_extra_per_grup']}
    if pregunta == '5.3':
        x['aula_csv'] = sum(a.aula != referencia.files[sid].aula
                            for sid, a in proposta.files.items() if sid in referencia.files)
        x['aula_oficial'] = _vs_referencia(base, col, referencia.a_files())['canvis_aula_vs_referencia']
    return x
