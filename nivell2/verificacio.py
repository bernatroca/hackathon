"""Única configuració de verificació oficial del lliurament."""
from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from nivell2.base import CONTINGENCIES, GRAU_NOU, RESULTATS, REPTE, ordre_verificador, verifica

OPCIONS = {
    '5.1': {'nomes_aules': True},
    '5.2': {},
    '5.3': {'escenari': CONTINGENCIES, 'referencia': Path('5.2/proposta.csv')},
    '5.4': {'escenari': GRAU_NOU, 'referencia': Path('5.2/proposta.csv')},
}
VALIDES = {'VALIDA', 'VALIDA AMB RELAXACIONS DECLARADES'}


def ordre(pregunta):
    if pregunta not in OPCIONS:
        raise ValueError('Pregunta desconeguda')
    return f'python -m nivell2.verificacio {pregunta}'


def opcions_pregunta(pregunta, arrel=RESULTATS):
    opcions = dict(OPCIONS[pregunta])
    if 'referencia' in opcions:
        opcions['referencia'] = arrel / opcions['referencia']
    relax = arrel / pregunta / 'relaxacions.csv'
    if relax.exists():
        opcions['relaxacions'] = relax
    return opcions


def ordre_oficial(pregunta, arrel=RESULTATS):
    opcions = opcions_pregunta(pregunta, arrel)
    out = Path('../../resultats/nivell2') / pregunta
    for key in ('referencia', 'relaxacions'):
        if key in opcions:
            opcions[key] = Path('../../resultats/nivell2') / opcions[key].relative_to(arrel)
    if 'escenari' in opcions:
        opcions['escenari'] = opcions['escenari'].relative_to(REPTE)
    cmd = ordre_verificador(out / 'proposta.csv', **opcions, python='python', absolut=False,
                           json_path=out / 'informe.json', violacions_path=out / 'violacions.csv')
    return 'cd repte/repte-horaris-escola\n' + shlex.join(cmd)


def verifica_pregunta(pregunta, arrel=RESULTATS):
    out = arrel / pregunta
    return verifica(out / 'proposta.csv', **opcions_pregunta(pregunta, arrel),
                    json_path=out / 'informe.json', violacions_path=out / 'violacions.csv')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pregunta', choices=OPCIONS)
    args = parser.parse_args(argv)
    try:
        report = verifica_pregunta(args.pregunta)
    except Exception:
        print(f'{args.pregunta} | ERROR de verificació')
        return 1
    print(f'{args.pregunta} | {report.veredicte}')
    return 0 if report.veredicte in VALIDES and not report.compten() else 1


if __name__ == '__main__':
    raise SystemExit(main())
