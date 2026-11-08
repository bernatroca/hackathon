"""python -m nivell1.comprova: calcula totes les troballes del 2n semestre i comprova les xifres de l'enunciat."""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Barrier

from nivell1.dades import connexio, consulta
from nivell1.troballes import moduls, una


def comprova_concurrencia():
    """Dues consultes de pàgina simultànies han de conservar la seva xifra."""
    casos = [('fora-torn', 1), ('docents-cavall', 2)]
    esperades = [una(id_, semestre).xifra for id_, semestre in casos]
    barrera = Barrier(2)

    def calcula(cas):
        id_, semestre = casos[cas]
        for _ in range(5):
            barrera.wait(timeout=30)
            if una(id_, semestre).xifra != esperades[cas]:
                return False
        return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultats = list(executor.map(calcula, range(2)))
    return all(resultats)


def main() -> int:
    with closing(connexio().cursor()) as cur:
        n, n2 = cur.execute("SELECT count(*), count(*) FILTER (WHERE sem = 2) FROM sessions").fetchone()
    errors = 0
    comprovacions = [('sessions totals', 17026, n), ('sessions del 2n semestre', 7739, n2)]
    setmanes, _ = consulta('semestre_setmanes', semestre=2, setmana=None)
    comprovacions.append(('setmanes lectives del 2n semestre (50 % del màxim)', 14, int(setmanes.setmanes.iloc[0])))
    problemes, _ = consulta('problemes_millores', semestre=2, setmana=None)
    comprovacions.append(('tipus de problemes amb incidències, excloses les aules permeses', 7, len(problemes)))
    comprovacions.append(('consultes simultànies amb cursors independents', True, comprova_concurrencia()))
    for m in moduls():
        t = m.calcula(2, None)
        print(f'[{m.ID}] {t.titol}: {t.xifra} · {t.frase}')
        comprovacions += [(f'{m.ID}: {q}', e, o) for q, e, o in getattr(m, 'comprova', lambda: [])()]
    print()
    for que, esperat, obtingut in comprovacions:
        ok = esperat == obtingut
        errors += not ok
        print(f"{'OK ' if ok else 'ERR'} {que}: esperat {esperat}, obtingut {obtingut}")
    print(f'\n{len(comprovacions) - errors}/{len(comprovacions)} comprovacions correctes')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
