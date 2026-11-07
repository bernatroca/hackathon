"""Adapta dades ja calculades a textos i representacions senzilles."""
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
    """Una expressió que no arrodoneix mai una proporció petita a zero."""
    if not total or n is None:
        return 'una part de les classes'
    pct = float(n) / float(total) * 100
    percent = numero(round(pct, 1)) if pct == 0 or pct >= .1 else 'menys del 0,1'
    if pct < 5:
        return f'gairebé cap ({percent} %)'
    inversa = float(total) / float(n)
    if inversa >= 2 and abs(inversa - round(inversa)) / inversa < .1:
        return f'1 de cada {numero(round(inversa))} classes'
    return f'el {percent} % de les classes'


def taula_extra(dades):
    if isinstance(dades, dict) and dades and all(pd.api.types.is_scalar(v) for v in dades.values()):
        return pd.DataFrame([dades])
    return pd.DataFrame(dades)


def primer(dades, *noms):
    return next((dades[nom] for nom in noms if nom in dades and dades[nom] is not None), None)


def coll_ampolla(extra):
    df = taula_extra(extra.get('coll_ampolla', []))
    if df.empty:
        return ''
    r = df.iloc[0].to_dict()
    mida = primer(r, 'llindar', 'places', 'capacitat', 'k')
    torn = primer(r, 'torn', 'franja')
    setmana = primer(r, 'setmana')
    if torn is None or setmana is None:
        return ''
    torn = {'mati': 'al matí', 'matí': 'al matí', 'tarda': 'a la tarda'}.get(str(torn), str(torn))
    if mida is None or pd.isna(mida) or str(mida).strip() == '' or float(mida) <= 0:
        pct = primer(r, 'ocupacio_pct', 'percentatge', 'percent')
        ocupacio = f' ({numero(round(float(pct)))} % ocupat)' if pct is not None and not pd.isna(pct) else ''
        nom = 'el matí' if torn == 'al matí' else 'la tarda' if torn == 'a la tarda' else torn
        return f'El més ajustat: {nom} en conjunt, la setmana {setmana}{ocupacio}.'
    return f'El més ajustat: les aules de més de {numero(mida)} places, {torn}, la setmana {setmana}.'


def desglos(extra):
    df = taula_extra(extra.get('desglos', []))
    if df.empty:
        return ''
    r = df.iloc[0].to_dict()
    pendents = primer(r, 'per_assignar', 'per_assignar_de_debo', 'pendents', 'sense_aula_real', 'aulari', 'demanda_aulari')
    laboratoris = primer(r, 'laboratoris', 'plab', 'PLAB')
    dobles = primer(r, 'dobles', 'sense_espai')
    if any(n is None for n in (pendents, laboratoris, dobles)):
        return ''
    return f'{numero(pendents)} per assignar de debò · {numero(laboratoris)} laboratoris (no es toquen) · {numero(dobles)} dobles (sense aula pròpia)'


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
        c['resposta'] = 'Hi ha marge d’hores'
        c['torns'] = f"Matí {c['ocupacio']} %. Que l’horari encaixi de debò ho valida la part 2."
        torns = taula_extra(extra.get('torns', []))
        if {'torn', 'ocupacio_pct'}.issubset(torns.columns):
            noms = torns.torn.astype(str).str.lower().str.replace('í', 'i', regex=False)
            valors = dict(zip(noms, torns.ocupacio_pct))
            parts = [f"{nom} {numero(round(float(valors[torn])))} %" for torn, nom, acord in
                     [('mati', 'Matí', 'ocupat'), ('tarda', 'Tarda', 'ocupada')] if torn in valors]
            if parts:
                c['torns'] = ' · '.join(parts) + '. Que l’horari encaixi de debò ho valida la part 2.'
        c['coll_ampolla'] = coll_ampolla(extra)
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
    if t.id == 'hi-cap-mati':
        resultat.update(etiqueta='Pendent de validar', estat='ambre', frase=c['torns'])
    if t.id == 'marge-grau-nou' and (t.extra.get('estat_provisional') or not t.extra.get('validat_part2', False)):
        resultat.update(etiqueta='Pendent de validar', estat='ambre')
    resultat.update(c=c)
    return resultat


def abast(t):
    setmana = (t.extra or {}).get('setmana')
    return f'Detall de la setmana {setmana}' if setmana else 'Setmana no indicada'
