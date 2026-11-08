"""Revalida els quatre lliuraments abans de crear el ZIP."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import contextlib
import io
import zipfile
from pathlib import Path

from nivell2.xifres_lliurament import genera, graelles
from nivell2.base import RESULTATS
from nivell2.junta import documents
from nivell2.comprova_persones import comprova as comprova_persones
from nivell2.verificacio import OPCIONS, VALIDES, ordre, ordre_oficial, verifica_pregunta

OPCIONALS = ('relaxacions.csv', 'diagnostic.md', 'resum.json', 'execucio.json',
             'excepcions.csv', 'titulacions.csv')

JUNTA = ('junta.html', 'junta.md', 'junta.json')

OBLIGATORIS = ('proposta.csv', 'informe.json', 'violacions.csv', 'xifres.csv', 'README.md')


def contracte(out, pregunta):
    if any(not (out / name).is_file() for name in OBLIGATORIS):
        return False
    if pregunta == '5.2':
        junta = out.parent / 'junta' / '5.2'
        if any(not (junta / name).is_file() for name in JUNTA):
            return False
        try:
            metadata = json.loads((junta / 'junta.json').read_text(encoding='utf-8'))
            digest = hashlib.sha256((out / 'proposta.csv').read_bytes()).hexdigest()
            if metadata.get('empremtes', {}).get('proposta') != digest:
                return False
            relax = out / 'relaxacions.csv'
            relax_digest = hashlib.sha256(relax.read_bytes()).hexdigest() if relax.is_file() else None
            if metadata.get('empremtes', {}).get('relaxacions') != relax_digest:
                print("resum de la Junta desactualitzat; regenera'l")
                return False
            md, html = documents(metadata)
            for name, content in (('junta.md', md), ('junta.html', html)):
                if (junta / name).read_bytes() != content.encode('utf-8'):
                    print("resum de la Junta desactualitzat; regenera'l")
                    return False
        except (OSError, ValueError, AttributeError, KeyError, TypeError):
            return False
    with (out / 'xifres.csv').open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        if next(reader, None) != ['xifra', 'abans', 'despres']:
            return False
        rows = list(reader)
        if not rows or any(len(row) != 3 for row in rows):
            return False
    readme = (out / 'README.md').read_text(encoding='utf-8')
    return (ordre_oficial(pregunta, out.parent) in readme and ordre(pregunta) in readme and f'-m nivell2.s{pregunta.replace(".", "")}' in readme
            and '--llavor' in readme and '--temps' in readme
            and not re.search(r'/(?:Users|home|tmp|private|opt)/', readme))


def empaqueta(sortida, *, sense_zip=False, arrel=RESULTATS):
    sortida = Path(sortida)
    sortida.mkdir(parents=True, exist_ok=True)
    desti = sortida / 'lliurament-nivell2.zip'
    desti.unlink(missing_ok=True)
    valid = True
    print('Pregunta | Veredicte | Contracte')
    print('--- | --- | ---')
    for pregunta in OPCIONS:
        try:
            # És la mateixa entrada que executa l'ordre publicada al README.
            report = verifica_pregunta(pregunta, arrel)
            verdict = report.veredicte
            ok = verdict in VALIDES and not report.compten()
            genera(pregunta, arrel)
            complete = contracte(arrel / pregunta, pregunta)
        except Exception:
            verdict, ok, complete = 'ERROR de verificació o contracte', False, False
        valid &= ok and complete
        print(f'{pregunta} | {verdict} | {"OK" if complete else "ERROR"}')
    try:
        # La funció és també l'entrada del CLI; només publiquem el veredicte.
        with contextlib.redirect_stdout(io.StringIO()):
            persones = comprova_persones(resultats=arrel)
    except Exception:
        persones = False
    print('Persones | ' + ('CORRECTE' if persones else 'NO CORRECTE') + ' | —')
    valid &= persones
    if not valid:
        return 1
    folder = graelles(sortida, arrel)
    if not sense_zip:
        temporary = sortida / 'lliurament-nivell2.zip.tmp'
        try:
            with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(folder.glob('*.html')):
                    archive.write(path, f'graelles/{path.name}')
                for name in JUNTA:
                    archive.write(arrel / 'junta' / '5.2' / name, f'junta/5.2/{name}')
                for pregunta in OPCIONS:
                    for name in (*OBLIGATORIS, *OPCIONALS):
                        path = arrel / pregunta / name
                        if path.is_file():
                            archive.write(path, f'nivell2/{pregunta}/{name}')
            temporary.replace(desti)
        finally:
            temporary.unlink(missing_ok=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sortida', required=True, type=Path)
    parser.add_argument('--sense-zip', action='store_true')
    args = parser.parse_args(argv)
    return empaqueta(args.sortida, sense_zip=args.sense_zip)


if __name__ == '__main__':
    raise SystemExit(main())
