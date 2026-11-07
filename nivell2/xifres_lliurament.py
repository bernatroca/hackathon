"""Artifacts de lliurament calculats exclusivament dels CSV finals."""
import csv
from html import escape

from nivell2.base import Proposta, carrega_oficial, GRAU_NOU
from nivell2.verificacio import opcions_pregunta
from nivell2.xifres import compara
from nivell2.readmes import normalitza


def genera(pregunta, arrel):
    out = arrel / pregunta
    comparison = compara(Proposta.llegeix(out / 'proposta.csv'),
                         proposta_path=out / 'proposta.csv',
                         **opcions_pregunta(pregunta, arrel))
    with (out / 'xifres.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['xifra', 'abans', 'despres'])
        writer.writeheader()
        writer.writerows(comparison.files)
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
