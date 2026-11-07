"""Adapta dades ja calculades a textos i representacions senzilles."""
from fractions import Fraction
import re
import pandas as pd
from servei import AULES_DISPONIBLES, PLACES_GRAU_NOU
from textos import TEXTOS
from components.format import numero

DIES = {'L': 'Dilluns', 'M': 'Dimarts', 'X': 'Dimecres', 'J': 'Dijous', 'V': 'Divendres'}


def valor(text):
    match = re.search(r'-?[\d.]+(?:,\d+)?', str(text))
    return float(match[0].replace('.', '').replace(',', '.')) if match else None


def proporcio(n, total):
    if not total or n is None:
        return 'una part de les'
    fraccio = Fraction(float(n) / float(total)).limit_denominator(10)
    if not fraccio.numerator:
        return 'cap de les'
    return f'{numero(fraccio.numerator)} de cada {numero(fraccio.denominator)}'


def context(t, altres=None):
    altres = altres or {}
    extra = t.extra or {}
    c = dict(xifra=t.xifra, places=numero(PLACES_GRAU_NOU), disponibles=numero(AULES_DISPONIBLES),
             hores_noves='—', hores_lliures='—', proporcio='una part de les', sense_aula='—',
             dia='dia no indicat', pic='—', ocupacio='—')
    c['percent'] = None
    if t.id == 'hi-cap-mati':
        pic = pd.DataFrame(extra.get('pic', t.taula))
        ocupacio = pd.DataFrame(extra.get('ocupacio', []))
        if {'classes', 'dia'}.issubset(pic.columns) and not pic.empty:
            fila = pic.loc[pic.classes.idxmax()]
            c.update(pic=numero(fila.classes), dia=DIES.get(fila.dia, str(fila.dia)).lower(), pic_n=int(fila.classes))
        if 'ocupacio_pct' in ocupacio and not ocupacio.empty:
            c['ocupacio'] = numero(round(float(ocupacio.iloc[0].ocupacio_pct)))
        mida = pd.DataFrame(extra.get('per_mida', []))
        c['falla'] = ('falla' in mida and bool(mida.falla.any())) or c.get('pic_n', 0) > AULES_DISPONIBLES
        c['resposta'] = 'Cal ajustar el matí.' if c['falla'] else 'Sí, però just.'
    elif t.id in ('fora-torn', 'hores-aula'):
        cobertura = t if t.id == 'hores-aula' else altres.get('hores-aula')
        total = None
        if cobertura is not None and 'sessions_totals' in cobertura.taula and not cobertura.taula.empty:
            total = float(cobertura.taula.iloc[0].sessions_totals)
        n = extra.get('sessions_sense_aula') if t.id == 'hores-aula' else valor(t.xifra)
        c.update(proporcio=proporcio(n, total), sense_aula=numero(n) if n is not None else '—')
        if total and n is not None:
            c['percent'] = float(n) / total * 100
    elif t.id == 'marge-grau-nou':
        df = t.taula
        if {'llindar', 'seminaris', 'nou_hores', 'marge_hores'}.issubset(df.columns):
            base = df[(df.llindar == 0) & ~df.seminaris]
            if not base.empty:
                r = base.iloc[0]
                c.update(hores_noves=numero(r.nou_hores), hores_lliures=numero(r.marge_hores),
                         xifra=f'{numero(r.nou_hores)} h', marge_n=float(r.marge_hores), hores_noves_n=float(r.nou_hores))
                if r.marge_hores > 0:
                    c['percent'] = r.nou_hores / r.marge_hores * 100
        c['falla'] = not extra.get('cap_per_mida', False)
    return c


def text(t, altres=None):
    c = context(t, altres)
    plantilla = TEXTOS.get(t.id, dict(estat='ambre', etiqueta='Vigilar', titol=t.titol,
        frase='Resultat disponible: {xifra}.', proposem='Revisar el resultat amb Gestió Acadèmica.'))
    resultat = {k: v.format_map(c) for k, v in plantilla.items()}
    if c.get('falla'):
        resultat.update(estat='vermell', etiqueta='Cal actuar')
        if t.id == 'marge-grau-nou':
            resultat['frase'] = f"Necessita {c['hores_noves']} h d’aula a la setmana i en queden {c['hores_lliures']} h lliures. Algunes mides d’aula no cobreixen la demanda."
    resultat.update(c=c)
    return resultat


def abast(t):
    setmana = (t.extra or {}).get('setmana')
    return f'Detall de la setmana {setmana}' if setmana else 'Setmana no indicada'
