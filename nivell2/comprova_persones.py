"""Comprova que cap persona tingui dues classes alhora ni una classe repetida, a tots els escenaris.

Escenaris: l'horari d'avui i cada proposta desada a resultats/nivell2/<nom>/proposta.csv.
Per pantalla només surten recomptes i el veredicte: cap nom, identificador, hora ni aula.
El detall (amb identificadors) només s'escriu si es demana amb --detall, a un fitxer fora de git.

Què es mira:
1. Persones amb dues classes alhora: dues sessions que se solapen i que comparteixen alumnat segons la
   regla oficial (mateix estudi, mateixa línia o mateix número de grup). Les sessions d'una mateixa
   classe física (compartida) no compten. Si les dues són de la mateixa assignatura i tipus, és una
   classe repetida.
2. Dobles titulacions: les sessions «sense espai» són classes que el doble fa amb un altre grup.
   Avui coincideixen amb la classe d'aquell grup (mateixa assignatura, tipus, grup, dia i hora).
   A cada proposta: no se n'han de separar (mateix dia i hora) i no han de tenir aula pròpia diferent
   (seria la mateixa classe duplicada).

Ús:  python -m nivell2.comprova_persones [--detall FITXER]
Surt amb 0 si tot és correcte i amb 1 si alguna proposta té problemes nous.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from nivell2.base import CONTINGENCIES, GRAU_NOU, RESULTATS_PRINCIPAL, Proposta, carrega_oficial
from horaris.check import Informe as InformeIntern, _alumnat_comparteix, _col_loca


def colloca_avui(base):
    return _col_loca(base, Proposta.de_base(base).a_files(), InformeIntern())


def conflictes(col) -> dict[tuple[str, str], str]:
    """Parells de sessions que posen una mateixa persona a dues classes alhora -> 'repetida' o 'diferents'."""
    per_dia = defaultdict(list)
    for sid, c in col.items():
        for coh in c.s.cohorts:
            per_dia[c.data, coh].append(sid)
    out = {}
    for sids in per_dia.values():
        sids.sort(key=lambda i: (col[i].ini, i))
        for n, a in enumerate(sids):
            ca = col[a]
            for b in sids[n + 1:]:
                cb = col[b]
                if cb.ini >= ca.fi:
                    break
                sa, sb = ca.s, cb.s
                if sa.unitat == sb.unitat or not _alumnat_comparteix(sa, sb):
                    continue
                parell = tuple(sorted((a, b)))
                out[parell] = 'repetida' if (sa.codi, sa.tipus) == (sb.codi, sb.tipus) else 'diferents'
    return out


# Com pot estar lligada una classe del doble a la classe d'un altre grup, de més estricte a més ampli.
# Les quatre primeres serveixen per aparellar; la de docent només es compta (és massa àmplia).
CLAUS = {
    'mateixa classe compartida': lambda s: [('u', s.unitat)],
    'assignatura, tipus, grup, dia i hora': lambda s: [('g', s.codi, s.tipus, s.grup, s.data, s.ini)],
    'assignatura, tipus, dia i hora': lambda s: [('t', s.codi, s.tipus, s.data, s.ini)],
    'assignatura, dia i hora': lambda s: [('a', s.codi, s.data, s.ini)],
}
CLAU_DOCENT = 'mateix docent, dia i hora (només informatiu)'


def _index(base):
    index = defaultdict(list)
    for s in base.sessions.values():
        if not s.sense_espai:
            for f in CLAUS.values():
                for k in f(s):
                    index[k].append(s.id)
            for d in s.docents:
                index['d', d, s.data, s.ini].append(s.id)
    return index


def parelles_dobles(base) -> tuple[dict[str, list[str]], int]:
    """Sessió sense espai -> sessions de la classe on va avui (primera clau que coincideix). I quantes no en tenen."""
    index = _index(base)
    parelles, sense_parella = {}, 0
    for s in base.sessions.values():
        if s.sense_espai:
            p = next((index[k] for f in CLAUS.values() for k in f(s) if index.get(k)), None)
            if p:
                parelles[s.id] = p
            else:
                sense_parella += 1
    return parelles, sense_parella


def diagnosi_dobles(base) -> dict[str, int]:
    """Només recomptes: amb quantes classes sense espai coincideix cada clau, i com són."""
    index = _index(base)
    dobles = [s for s in base.sessions.values() if s.sense_espai]
    altres_codis = {s.codi for s in base.sessions.values() if not s.sense_espai}
    cohorts_amb_classes_propies = {c for s in base.sessions.values() if not s.sense_espai for c in s.cohorts}
    d = {nom: sum(any(index.get(k) for k in f(s)) for s in dobles) for nom, f in CLAUS.items()}
    d[CLAU_DOCENT] = sum(any(index.get(('d', x, s.data, s.ini)) for x in s.docents) for s in dobles)
    d["la mateixa assignatura la fa un altre grup (a qualsevol hora)"] = sum(s.codi in altres_codis for s in dobles)
    d['tenen aula avui'] = sum(bool(s.aula) for s in dobles)
    d['estudis diferents'] = len({c for s in dobles for c in s.cohorts})
    d['dels quals també tenen classes amb espai'] = len({c for s in dobles for c in s.cohorts} & cohorts_amb_classes_propies)
    for t in sorted({s.tipus for s in dobles}):
        d[f'de tipus {t}'] = sum(s.tipus == t for s in dobles)
    return d


def comprova_dobles(base, col, parelles) -> dict[str, list[str]]:
    separades, duplicades = [], []
    for sid, socis in parelles.items():
        c = col[sid]
        if (c.data, c.ini) not in {(col[p].data, col[p].ini) for p in socis}:
            separades.append(sid)
    for s in base.sessions.values():
        if s.sense_espai:
            c = col[s.id]
            aules_socis = {col[p].aula for p in parelles.get(s.id, ())}
            if c.aula and c.aula != s.aula and c.aula not in aules_socis:
                duplicades.append(s.id)
    return {'separades': separades, 'duplicades': duplicades}


def resum_conflictes(conf):
    rep = sum(v == 'repetida' for v in conf.values())
    return f'{len(conf)} ({rep} de la mateixa assignatura repetida, {len(conf) - rep} de dues assignatures diferents)'


def escenaris(resultats=None):
    resultats = RESULTATS_PRINCIPAL if resultats is None else Path(resultats)
    yield 'avui', None, None
    if resultats.is_dir():
        for path in sorted(resultats.glob('*/proposta.csv')):
            nom = path.parent.name
            yield nom, path, (CONTINGENCIES if nom == '5.3' else
                             GRAU_NOU if nom.startswith('5.4') else None)


def comprova(detall: Path | None = None, *, resultats=None) -> bool:
    from nivell2.junta import carrega_proposta

    bases, avui, dobles_base = {}, {}, {}
    correcte, informe = True, {}
    for nom, path, escenari in escenaris(resultats):
        clau = str(escenari)
        if clau not in bases:
            bases[clau] = carrega_oficial(escenari)
            avui[clau] = conflictes(colloca_avui(bases[clau]))
            dobles_base[clau] = parelles_dobles(bases[clau])
        base = bases[clau]
        parelles, sense_parella = dobles_base[clau]
        if path is None:
            col, conf = colloca_avui(base), avui[clau]
        else:
            try:
                _, col = carrega_proposta(path, base)
            except (ValueError, KeyError):
                print(f'\n== {nom}: no s\'ha pogut llegir la proposta (format o sessions d\'un altre escenari).')
                correcte = False
                continue
            conf = conflictes(col)
        nous = {k: v for k, v in conf.items() if k not in avui[clau]}
        d = comprova_dobles(base, col, parelles)
        n_dobles = sum(s.sense_espai for s in base.sessions.values())

        etiqueta = {str(GRAU_NOU): ' (amb el grau nou)', str(CONTINGENCIES): ' (amb els imprevistos)'}.get(str(escenari), '')
        print(f'\n== {nom}{etiqueta}')
        print(f'  Persones amb dues classes alhora: {resum_conflictes(conf)}')
        if path is not None:
            print(f'    - noves respecte d\'avui: {resum_conflictes(nous)}')
            print(f'    - que ja hi eren avui: {len(conf) - len(nous)}')
        print(f'  Dobles: {n_dobles} classes que fan amb un altre grup; {len(parelles)} coincideixen avui amb la classe '
              f'd\'aquell grup i {sense_parella} no en tenen cap a la mateixa hora.')
        if path is None:
            print('    Com estan lligades a les dades (quantes coincideixen amb cada criteri):')
            for nom_clau, n in diagnosi_dobles(base).items():
                print(f'      · {nom_clau}: {n}')
        print(f'    - separades de la classe on van: {len(d["separades"])}')
        print(f'    - amb aula pròpia nova (classe duplicada): {len(d["duplicades"])}')
        if path is not None and (nous or d['separades'] or d['duplicades']):
            correcte = False
        informe[nom] = {'conflictes': [list(k) + [v] for k, v in conf.items()],
                        'nous': [list(k) + [v] for k, v in nous.items()], **d}

    print('\nVEREDICTE: ' + ('CORRECTE. Cap proposta posa ningú a dues classes alhora ni separa o duplica '
                             'classes dels dobles.' if correcte else
                             'NO CORRECTE. Alguna proposta té problemes nous (vegeu els recomptes de dalt).'))
    if detall:
        detall.parent.mkdir(parents=True, exist_ok=True)
        detall.write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'Detall amb identificadors a {detall} (fora de git; no el comparteixis).')
    return correcte


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--detall', type=Path, help='fitxer JSON per al detall amb identificadors (fora de git)')
    ap.add_argument('--resultats', type=Path, help='carpeta de propostes a comprovar')
    args = ap.parse_args(argv)
    sys.exit(0 if comprova(args.detall, resultats=args.resultats) else 1)


if __name__ == '__main__':
    main()
