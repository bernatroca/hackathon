"""python -m nivell1.comprova: calcula totes les troballes del 2n semestre i comprova les xifres de l'enunciat."""
from __future__ import annotations

import sys

from nivell1.dades import connexio, consulta
from nivell1.troballes import moduls


def main() -> int:
    con = connexio()
    n, n2 = con.execute("SELECT count(*), count(*) FILTER (WHERE sem = 2) FROM sessions").fetchone()
    errors = 0
    comprovacions = [('sessions totals', 17026, n), ('sessions del 2n semestre', 7739, n2)]
    setmanes, _ = consulta('semestre_setmanes', semestre=2, setmana=None)
    comprovacions.append(('setmanes lectives del 2n semestre (50 % del màxim)', 14, int(setmanes.setmanes.iloc[0])))
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
