"""Artifacts de lliurament calculats exclusivament dels CSV finals."""
import csv
import json
import re
import argparse
from html import escape
from pathlib import Path

from nivell2.base import Proposta, carrega_oficial, GRAU_NOU, RESULTATS
from nivell2.verificacio import OPCIONS, opcions_pregunta
from nivell2.xifres import compara
from nivell2.readmes import normalitza, explica_comptatge, documenta, arrodoneix_text


EXPLICACIONS_51 = {
    'sessions_nomes_canvien_aula': 'S’assignen les 4.541 aules que faltaven, es canvien 369 aules prèvies i 153 classes de dobles deixen d’ocupar aula pròpia: 5.063 diferències al CSV, sense moure dia ni hora.',
    'canvis_aula': 'Es canvien 369 aules prèviament assignades per prioritzar la rutina i l’aula base; les assignacions que faltaven es compten separadament.',
    'aules_grup_setmana_mitjana': 'Assignar espai a les classes que no en tenien augmenta les aules diferents del grup per setmana; es compten tots els tipus de classe.',
    'aules_grup_setmana_maxim': 'El pitjor grup/setmana incorpora les aules que abans faltaven; és un màxim, no el nombre habitual d’aules de cada grup.',
    'pitjor_cohort_aula_pct': 'El percentatge usa totes les sessions de la cohort, incloses les que no tenien aula; només el numerador compta canvis d’aules prèvies computables.',
    'desplacaments_aula': 'La rutina i l’aula base tenen prioritat; assignar les aules pendents també fa computables més trajectes entre classes seguides.',
    'r6_canvis_te_paul_fora_passadis': 'L’assignació prioritza rutina i aula base TE; alguns trajectes entre teoria i problemes queden fora del mateix passadís.',
    'desplacaments_edifici': 'Algunes aules assignades obliguen a canviar d’edifici entre classes seguides, darrere la prioritat de rutina i aula base.',
    'excepcions_rutina': 'La disponibilitat i el tipus d’aula impedeixen mantenir el mateix espai en totes les setmanes d’algunes activitats.',
    'activitats_rutinaries_pct': 'Algunes activitats necessiten aules diferents entre setmanes per respectar disponibilitat, tipus i aforament.',
    'r6_aules_te_extra_sense_dobles': 'Sense dobles sense espai propi, les aules de teoria addicionals passen de 8 a 9; el recompte oficial inclou també els dobles.',
}

# Explicacions de les claus que es desdoblen ara per fer explícita la referència.
EXPLICACIONS_REFERENCIA = {
    'sessions_canvien_hora_vs_referencia': 'Canvis de dia o hora respecte del 5.2 congelat; es compten separadament dels canvis respecte d’avui.',
    'sessions_nomes_canvien_aula_vs_referencia': 'Canvis exclusivament d’aula respecte del 5.2 congelat; permeten reparar les incidències sense canviar-ne les franges.',
    'canvis_torn_vs_referencia': 'Canvis de torn respecte del 5.2 congelat, separats dels canvis de torn que ja feia el 5.2 respecte d’avui.',
}

EXPLICACIONS_54 = {
    'sessions_canvien_hora': 'Als canvis del 5.2 respecte d’avui s’afegeixen 41 sessions noves mogudes amb la regla prudent de subgrups de l’equip per reduir esperes; amb la regla oficial el grau nou hi cap sense moure’n cap.',
    'sessions_nomes_canvien_aula': 'Es compten les diferències exclusivament d’aula respecte de la partida de cada sessió, incloses les noves; les sessions del 5.2 es conserven.',
}

EXPLICACIONS_52 = {
    'pitjor_cohort_aula_pct': 'A GEQ,1r canvien d’aula 80 de 231 sessions (34,63 %), és a dir, totes les que ja tenien aula; les altres 151 no en tenien i ara se n’assignen. El denominador és tota la cohort.',
}


def format_valor(valor):
    return f'{valor:.2f}'.replace('.', ',') if isinstance(valor, float) else str(valor)


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
    path = out / 'README.md'
    text = path.read_text(encoding='utf-8')
    explanations = {}
    for line in text.splitlines():
        match = re.fullmatch(r'- (.*): ([^;]+); (.+)', line)
        if match:
            explanations[match[1]] = match[3]
    text = re.sub(r'(?:\A|\n)## Què empitjora i per què\n.*?(?=\n## |\Z)', '', text, flags=re.S)
    text = normalitza(text, pregunta, arrel)
    text = documenta(pregunta, out, text)
    text = explica_comptatge(text, comptatge_verificador(pregunta, arrel), pregunta)
    lines = []
    neutral = {'sessions_avaluades', 'aules_assignades', 'relaxacions_declarades'}
    for row in comparison.files:
        key, a, d = row['xifra'], row['abans'], row['despres']
        if isinstance(a, (int, float)) and isinstance(d, (int, float)):
            worse = d < a if key == 'activitats_rutinaries_pct' else d > a
            if worse and key not in neutral:
                explanation = ({'5.1': EXPLICACIONS_51, '5.2': EXPLICACIONS_52,
                                '5.4': EXPLICACIONS_54}.get(pregunta, {}).get(key))
                explanation = explanation or explanations.get(key) or EXPLICACIONS_REFERENCIA.get(key)
                if not explanation or 'per explicar.' in explanation:
                    raise ValueError(f'Falta explicar l’indicador {key} de {pregunta}')
                lines.append(f'- {key}: {format_valor(a)} → {format_valor(d)}; {explanation}')
    text = text.rstrip() + '\n\n## Què empitjora i per què\n\n' + (
        '\n'.join(lines) if lines else 'Cap empitjorament numèric detectat.') + '\n'
    # Valida les explicacions abans de substituir els artifacts finals.
    with (out / 'xifres.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['xifra', 'abans', 'despres'])
        writer.writeheader()
        writer.writerows(rows)
    path.write_text(arrodoneix_text(text), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preguntes', nargs='*', choices=tuple(OPCIONS), default=list(OPCIONS))
    parser.add_argument('--resultats', type=Path, default=RESULTATS)
    args = parser.parse_args(argv)
    for pregunta in args.preguntes:
        genera(pregunta, args.resultats)
        print(f'{pregunta} | derivats OK')
    return 0


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


if __name__ == '__main__':
    raise SystemExit(main())
