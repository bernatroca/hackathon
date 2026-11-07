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


def falta_mida(extra):
    """Descriu el dèficit amb les mateixes hores que retorna el mòdul de dades."""
    candidats = []
    coll = taula_extra(extra.get('coll_ampolla', []))
    if not coll.empty:
        candidats.append(coll)
    for nom in ('per_mida_setmanes', 'per_mida'):
        df = taula_extra(extra.get(nom, []))
        if 'variant' in df:
            df = df[df.variant == 'oficial']
        if {'demanda_h','oferta_h'}.issubset(df.columns):
            candidats.append(df[df.demanda_h > df.oferta_h])
    for df in candidats:
        if df.empty:
            continue
        for r in df.to_dict('records'):
            demanda, oferta = r.get('demanda_h'), r.get('oferta_h')
            if demanda is None or oferta is None or demanda <= oferta:
                continue
            torn = 'al matí' if r.get('torn', 'mati') in ('mati','matí') else 'a la tarda'
            setmana = r.get('setmana', extra.get('setmana', 'no indicada'))
            mida = r.get('llindar', 0)
            lloc = f'Per a grups de més de {numero(mida)} alumnes' if mida and mida > 0 else 'Per al torn en conjunt'
            return f'{lloc}, {torn}, la setmana {setmana}, calen {numero(demanda)} h d’aula i se n’ofereixen {numero(oferta)}: en falten {numero(demanda-oferta)} h.'
    return coll_ampolla(extra) or 'El balanç per mida indica un dèficit; el resultat encara no concreta les hores que falten.'


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
             hores_noves='—', hores_lliures='—', marge_semestre='—', etiqueta_setmana='a la setmana més plena', proporcio='una part de les', sense_aula='—',
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
        c['falla'] = bool(extra.get('falla_per_mida', False)) or ('falla' in mida and bool(mida.falla.any()))
        totes_mides = taula_extra(extra.get('per_mida_setmanes', []))
        if 'variant' in totes_mides:
            totes_mides = totes_mides[totes_mides.variant == 'oficial']
        c['falla'] = c['falla'] or ('falla' in totes_mides and bool(totes_mides.falla.any()))
        c['resposta'] = 'Falten aules d’algunes mides' if c['falla'] else 'Hi ha marge d’hores'
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
        total_semestre = extra.get('marge_semestre_h', extra.get('marge_h_semestre'))
        if total_semestre is not None:
            c['marge_semestre'] = numero(total_semestre)
        if {'llindar', 'seminaris', 'nou_hores', 'marge_hores'}.issubset(df.columns):
            base = df[(df.llindar == 0) & ~df.seminaris]
            if not base.empty:
                r = base.iloc[0]
                c.update(hores_noves=numero(r.nou_hores), hores_lliures=numero(r.marge_hores),
                         xifra=f'{numero(r.nou_hores)} h', marge_n=float(r.marge_hores), hores_noves_n=float(r.nou_hores))
                if r.marge_hores > 0:
                    c['percent'] = r.nou_hores / r.marge_hores * 100
        necessitat = extra.get('demanda_h_setmana', c.get('hores_noves_n'))
        lliures = extra.get('lliures_h_setmana', c.get('marge_n'))
        if necessitat is not None:
            c.update(hores_noves=numero(necessitat), hores_noves_n=float(necessitat), xifra=f'{numero(necessitat)} h')
        if lliures is not None:
            c.update(hores_lliures=numero(lliures), marge_n=float(lliures))
        if necessitat is not None and lliures is not None:
            c['percent'] = float(necessitat)/float(lliures)*100 if lliures > 0 else None
        c['falla'] = not extra.get('cap_per_mida', False)
    return c


def text(t, altres=None, *, setmana_triada=None):
    c = context(t, altres)
    if setmana_triada is not None:
        c['etiqueta_setmana'] = f'a la setmana seleccionada ({setmana_triada})'
    plantilla = TEXTOS.get(t.id, dict(estat='ambre', etiqueta='Vigilar', titol=t.titol,
        frase='Resultat disponible: {xifra}.', proposem='Revisar el resultat amb Gestió Acadèmica.'))
    resultat = {k: v.format_map(c) for k, v in plantilla.items()}
    if c.get('falla'):
        resultat.update(estat='vermell', etiqueta='Cal actuar')
        if t.id == 'marge-grau-nou':
            resultat['frase'] += " Algunes mides d’aula no cobreixen la demanda."
    if t.id == 'hi-cap-mati':
        resultat.update(etiqueta='Cal actuar' if c['falla'] else 'Pendent de validar',
            estat='vermell' if c['falla'] else 'ambre',
            frase=c['torns'] + (' ' + falta_mida(t.extra) if c['falla'] else ''))
        validacio = (t.extra or {}).get('validat_part2') or {}
        if validacio.get('valida') and not c['falla']:
            c['validat'] = True
            c['resposta'] = 'Sí, hi cap'
            resultat.update(etiqueta='Hi cap', estat='verd',
                frase=c['torns'].split('.')[0] + '. Confirmat amb l’horari proposat i el verificador oficial: '
                      'només queden fora de torn les classes que no es poden moure.')
    if t.id == 'marge-grau-nou':
        v = t.extra.get('validat_part2')
        v = v if isinstance(v, dict) else {}
        if v.get('valida') and v.get('resposta') == 1 and not c.get('falla'):
            c['validat'] = True
            mogudes = v.get('sessions_52_mogudes', 0)
            n = v.get('sessions_grau_nou_collocades', v.get('sessions_grau_nou'))
            resultat.update(etiqueta='Hi cap', estat='verd',
                proposem='Incorporar-lo a l’horari proposat: ja hi cap.', frase=(
                f"L’horari proposat hi col·loca {numero(n) + ' sessions' if n is not None else 'el grau nou'}"
                + (' sense moure cap classe' if not mogudes else f' movent {numero(mogudes)} classes')
                + ' (verificador oficial).'))
        elif v.get('resposta') in (2, 4):
            resultat.update(etiqueta='Cal actuar', estat='vermell', frase=(
                'No hi cap sense tocar l’horari proposat.' if v['resposta'] == 2 else 'Hem demostrat que no hi cap.')
                + ' Ho ha comprovat la part 2 amb el verificador oficial.')
        else:
            resultat.update(etiqueta='Pendent de validar', estat='ambre')
    resultat.update(c=c)
    return resultat


def abast(t):
    setmana = (t.extra or {}).get('setmana')
    return f'Detall de la setmana {setmana}' if setmana else 'Setmana no indicada'


def grup_estat(info):
    """El filtre groc també inclou els balanços pendents de validar."""
    return {'vermell':'Cal actuar', 'ambre':'Vigilar', 'verd':'Hi cap'}[info['estat']]


def ordena_respostes(resultat, infos):
    # totes() ja torna les preguntes segons ORDRE. L'ordenació estable conserva
    # aquest ordre d'especificació dins de cadascun dels tres grups d'urgència.
    prioritat = {'vermell':0, 'ambre':1, 'verd':2}
    return sorted(resultat,key=lambda t:prioritat[infos[t.id]['estat']])
