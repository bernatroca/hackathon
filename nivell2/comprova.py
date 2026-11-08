"""python -m nivell2.comprova proposta.csv --sortida xifres.csv."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from nivell2.base import Proposta
from nivell2.xifres import compara

ETIQUETES = {
    'sessions_avaluades': 'Sessions avaluades pel verificador',
    'veredicte': 'Veredicte oficial',
    'sessions_no_avaluables': 'Sessions absents o no avaluables (comparació incompleta)',
    'activitats_rutinaries_pct': 'Activitats amb el mateix dia, hora i aula (%)',
    'excepcions_rutina': 'Sessions que trenquen el patró més freqüent de l’activitat',
    'canvis_torn': 'Sessions que canvien de torn respecte d’avui',
    'canvis_torn_sense_regla1': 'Sessions que canvien de torn sense que ho demani la regla 1 (ha de ser 0)',
    'aules_grup_setmana_mitjana': 'Aules diferents per grup i setmana: mitjana',
    'aules_grup_setmana_maxim': 'Aules diferents per grup i setmana: pitjor cas',
    'relaxacions_declarades': 'Relaxacions declarades (files)',
    'hores_mortes_min': 'Minuts d’hores mortes (hores_mortes_min)',
    'desplacaments_aula': 'Canvis d’aula entre classes seguides (desplacaments_aula)',
    'desplacaments_edifici': 'Canvis d’edifici entre classes seguides (desplacaments_edifici)',
    'r6_aules_te_extra_per_grup': 'Aules extra de teoria per grup (r6_aules_te_extra_per_grup)',
    'r6_canvis_te_paul_fora_passadis': 'Canvis teoria-problemes fora del passadís (r6_canvis_te_paul_fora_passadis)',
    'canvis_franja': 'Sessions que canvien de dia o hora (canvis_franja)',
    'canvis_aula': 'Sessions amb canvi d’aula segons el verificador (canvis_aula)',
    'canvis_franja_vs_referencia': 'Canvis de dia o hora respecte de la referència',
    'canvis_aula_vs_referencia': 'Canvis d’aula respecte de la referència',
    'canvis_torn_vs_referencia': 'Sessions que canvien de torn respecte de la referència',
    'sessions_canvien_hora': 'Sessions que canvien de dia o hora respecte d’avui',
    'sessions_nomes_canvien_aula': 'Sessions que només canvien d’aula respecte d’avui',
    'sessions_canvien_hora_vs_referencia': 'Sessions que canvien de dia o hora respecte de la referència',
    'sessions_nomes_canvien_aula_vs_referencia': 'Sessions que només canvien d’aula respecte de la referència',
    'incompliments_declarats': 'Incompliments declarats',
    'incompliments_heretats': 'Incompliments heretats',
    'aules_assignades': 'Sessions que reben una aula que faltava',
    'sessions_grau_nou_fora_franja': 'Sessions noves fora de la franja original',
    'sessions_52_mogudes': 'Sessions del 5.2 mogudes',
}


def etiqueta(clau):
    for prefix, text in (('heretats:', 'Incompliments heretats: '),
                         ('declarats:', 'Incompliments declarats: '),
                         ('relaxacions:', 'Relaxacions declarades: ')):
        if clau.startswith(prefix):
            return text + clau.split(':', 1)[1]
    if clau.startswith('incompliments:'):
        return 'Incompliments que compten: ' + clau.split(':', 1)[1]
    if clau.startswith('relaxacio:'):
        return 'Relaxacions declarades: ' + clau.split(':', 1)[1]
    if clau.startswith('pitjor_cohort_'):
        canvi = clau.removeprefix('pitjor_cohort_').replace('_pct', ' (%)')
        return 'Titulació i curs amb més canvis ' + ("d’" if canvi.startswith('aula') else 'de ') + canvi
    return ETIQUETES.get(clau, clau)


def format_valor(v):
    if v is None:
        return 'No disponible'
    return f'{v:.2f}' if isinstance(v, float) else str(v)


def escriu_csv(path, files):
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(files[0]))
        w.writeheader()
        w.writerows(files)


def main(argv=None):
    p = argparse.ArgumentParser(description='Compara l’horari d’avui amb una proposta.')
    p.add_argument('proposta', type=Path)
    for nom in ('escenari', 'referencia', 'relaxacions', 'sortida', 'per-titulacio'):
        p.add_argument('--' + nom, type=Path)
    p.add_argument('--nomes-aules', action='store_true')
    args = p.parse_args(argv)
    try:
        resultat = compara(Proposta.llegeix(args.proposta), escenari=args.escenari,
                           referencia=args.referencia, relaxacions=args.relaxacions,
                           nomes_aules=args.nomes_aules, proposta_path=args.proposta)
        print('Què mirem | Abans | Després')
        for r in resultat.files:
            print(f"{etiqueta(r['xifra'])} | {format_valor(r['abans'])} | {format_valor(r['despres'])}")
        abans = {r['cohort']: r for r in resultat.titulacions if r['horari'] == 'abans'}
        for r in resultat.titulacions:
            if r['horari'] != 'despres':
                continue
            for canvi in ('franja', 'aula', 'torn'):
                a = abans.get(r['cohort'])
                av = f"{format_valor(a[canvi + '_pct'])}% ({a[canvi]}/{a['sessions']})" if a else 'No existia'
                dv = f"{format_valor(r[canvi + '_pct'])}% ({r[canvi]}/{r['sessions']})"
                preposicio = 'd’' if canvi == 'aula' else 'de '
                print(f"{r['cohort']}: sessions que canvien {preposicio}{canvi} | {av} | {dv}")
        print('Els canvis es comparen amb avui, excepte els indicadors etiquetats «respecte de la referència»; '
              'els percentatges per cohort inclouen totes les seves sessions. '
              'Cada sessió compartida compta a cadascuna de les seves cohorts.')
        if args.sortida:
            escriu_csv(args.sortida, resultat.files)
        if args.per_titulacio:
            escriu_csv(args.per_titulacio, resultat.titulacions)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        p.exit(2, f'No s’ha pogut calcular la comparació: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
