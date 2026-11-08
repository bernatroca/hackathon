"""Adapta dades ja calculades a textos i representacions senzilles."""
import re
from datetime import date, timedelta
import pandas as pd
from servei import AULES_DISPONIBLES, AULES_RESERVA, PLACES_GRAU_NOU
from textos import TEXTOS, TEXTOS_PORTADA
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


def dilluns_setmana(setmana):
    """Accepta el codi ISO i el registre del selector sense mostrar codis interns."""
    if isinstance(setmana, (tuple, list)):
        setmana = setmana[0] if setmana else None
    if setmana is None:
        return None
    match = re.fullmatch(r'(\d{4})-W(\d{2})', str(setmana))
    if not match:
        return None
    try:
        return date.fromisocalendar(int(match[1]), int(match[2]), 1)
    except ValueError:
        return None


def dates_setmana(setmana):
    dilluns = dilluns_setmana(setmana)
    if dilluns is None:
        return 'sense dades'
    divendres = dilluns + timedelta(days=4)
    return f'{dilluns.day}/{dilluns.month} – {divendres.day}/{divendres.month}'


def etiqueta_setmana(setmana, criteri='pic', seleccionada=False):
    data = dates_setmana(setmana)
    if seleccionada:
        return f'a la setmana seleccionada ({dates_setmana(setmana)})'
    nom = 'amb més demanda de matí' if criteri == 'demanda_mati' else 'amb més classes alhora'
    return f'a la setmana {nom} ({data})'


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
        return f'El més ajustat: {nom} en conjunt, la setmana del {dates_setmana(setmana)}{ocupacio}.'
    return f'El més ajustat: les aules de més de {numero(mida)} places, {torn}, la setmana del {dates_setmana(setmana)}.'


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
            return f'{lloc}, {torn}, la setmana del {dates_setmana(setmana)}, calen {numero(demanda)} h d’aula i se n’ofereixen {numero(oferta)}: en falten {numero(demanda-oferta)} h.'
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
             hores_noves='—', hores_lliures='—', marge_semestre='—', etiqueta_setmana=etiqueta_setmana(extra.get('setmana'), extra.get('criteri_setmana', 'pic')), proporcio='una part de les', sense_aula='—',
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
        c['torns'] = f"Matí ocupat al {c['ocupacio']} % de les hores d’aula. Cal comprovar que les classes encaixen a l’horari proposat."
        torns = taula_extra(extra.get('torns', []))
        if {'torn', 'ocupacio_pct'}.issubset(torns.columns):
            noms = torns.torn.astype(str).str.lower().str.replace('í', 'i', regex=False)
            valors = dict(zip(noms, torns.ocupacio_pct))
            parts = [f"{nom} {acord} al {numero(round(float(valors[torn])))} % de les hores d’aula" for torn, nom, acord in
                     [('mati', 'Matí', 'ocupat'), ('tarda', 'Tarda', 'ocupada')] if torn in valors]
            if parts:
                c['torns'] = ' · '.join(parts) + '. Cal comprovar que les classes encaixen a l’horari proposat.'
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
    if t.id == 'aforament':
        c.update(aforament_total=numero(extra.get('sessions_total', valor(t.xifra))),
                 aforament_heretades=numero(extra.get('sessions_heretades', 0)),
                 grups_afectats=numero(extra.get('grups_afectats', 0)))
    return c


def text(t, altres=None, *, setmana_triada=None):
    c = context(t, altres)
    extra = t.extra or {}
    if setmana_triada is not None:
        c['etiqueta_setmana'] = etiqueta_setmana(setmana_triada, seleccionada=True)
    plantilla = TEXTOS.get(t.id, dict(estat='gris', etiqueta='Per saber-ho', titol=t.titol,
        frase='Resultat disponible: {xifra}.', proposem='Revisar el resultat amb Gestió Acadèmica.'))
    resultat = {k: v.format_map(c) for k, v in plantilla.items()}
    v = extra.get('validat_part2')
    v = v if isinstance(v, dict) else {}
    validada = bool(v.get('valida'))
    resultat.update(estat='gris' if t.id in ('ocupacio', 'canvis-aula', 'docents-cavall') else 'ambre',
        etiqueta='Per saber-ho' if t.id in ('ocupacio', 'canvis-aula', 'docents-cavall') else 'Cal decidir')
    c['comparacio'] = ''
    if t.id == 'hi-cap-mati':
        c['validat'] = validada and not c['falla']
        c['resposta'] = 'Sí' if c['validat'] else 'No' if c['falla'] else 'Per comprovar'
        c['xifra'] = c['resposta']
        resultat['frase'] = (f"A l’hora més plena del matí fem servir {c['pic']} de les {c['disponibles']} aules; "
            f"{numero(AULES_RESERVA)} més queden de reserva.")
        if c['falla']:
            resultat['frase'] = 'Falta espai per a algunes mides d’aula. ' + falta_mida(extra)
        elif not c['validat']:
            resultat['frase'] += ' Cal comprovar que les classes encaixen en un horari.'
        resultat['proposem'] = 'Aplicar l’horari proposat.' if c['validat'] else 'Revisar el repartiment de les classes.'
    elif t.id == 'hores-aula':
        des = taula_extra(extra.get('desglos', []))
        n = primer(des.iloc[0].to_dict(), 'per_assignar', 'per_assignar_de_debo', 'pendents') if not des.empty else None
        n = n if n is not None else extra.get('sessions_sense_aula')
        c['xifra'] = f'{numero(n)} classes' if n is not None else 'Sense recompte disponible'
        resultat['frase'] = 'Són classes que avui no tenen cap aula assignada. No hi comptem els laboratoris ni les dobles titulacions, que no en necessiten.'
    elif t.id == 'fora-torn':
        c['xifra'] = f'{t.xifra} classes'
        resultat['frase'] = 'Són classes al matí que haurien de ser a la tarda, o al revés. No hi comptem les que ja estan fixades i no es poden moure.'
    elif t.id == 'marge-grau-nou':
        c['validat'] = validada and v.get('resposta') == 1 and not c['falla']
        c['xifra'] = 'Sí' if c['validat'] else 'No' if v.get('resposta') in (2, 4) else 'Per comprovar'
        resultat['frase'] = (f"El grau necessita {c['hores_noves']} h a la setmana; hi ha {c['hores_lliures']} h lliures {c['etiqueta_setmana']}.")
        if c['validat']:
            mogudes = v.get('sessions_52_mogudes', 0)
            n = v.get('sessions_grau_nou_collocades', v.get('sessions_grau_nou'))
            fora = v.get('sessions_grau_nou_fora_franja')
            resta = ('sense moure cap classe de la resta de l’horari' if mogudes == 0 else
                     f'movent {numero(mogudes)} classes de la resta de l’horari')
            noves = f'les {numero(n)} classes del grau nou' if n is not None else 'el grau nou'
            canvi = (f'; {numero(fora)} classes noves queden en una hora diferent de la que demanaven per reduir esperes'
                     if fora is not None and fora > 0 else
                     '; totes les classes noves conserven l’hora que demanaven' if fora == 0 else '')
            resultat.update(proposem='Incorporar-lo a l’horari proposat: ja hi cap.',
                frase=f'L’horari proposat col·loca {noves} {resta}{canvi}.')
        elif v.get('resposta') in (2, 4):
            resultat['frase'] = 'No hi cap sense tocar l’horari proposat.' if v['resposta'] == 2 else 'Hem demostrat que no hi cap.'
    elif t.id == 'problemes-millores':
        n = extra.get('tipus_detectats', valor(t.xifra))
        c['xifra'] = f'{numero(n)} tipus de problemes' if n is not None else t.xifra
        noms = t.taula
        if {'problema', 'xifra'}.issubset(noms.columns):
            from textos import PROBLEMES
            noms = noms.assign(quantitat=noms.xifra.map(valor)).dropna(subset=['quantitat'])
            principals = noms[noms.quantitat > 0].sort_values('quantitat', ascending=False).head(3).problema
            resultat['frase'] = 'Els més freqüents aquesta setmana: ' + ', '.join(PROBLEMES.get(n, n).lower() for n in principals) + '.' if len(principals) else 'Mira tots els problemes i les possibles millores ordenats al detall.'
    elif t.id == 'aforament':
        c['xifra'] = f'{t.xifra} classes'
    elif t.id == 'ocupacio':
        c['xifra'] = f'{t.xifra} del temps de l’aula més ocupada'
    elif t.id == 'hores-mortes':
        c['xifra'] = f'{t.xifra} per setmana'
        resultat['frase'] = 'Suma de les esperes de tots els grups, no el temps de cada estudiant.'
    elif t.id == 'canvis-aula':
        c['xifra'] = f'{t.xifra} canvis de passadís per setmana'
        resultat['frase'] = 'És la suma de tots els grups. Comptem un canvi quan dues classes seguides són en passadissos diferents.'
    elif t.id == 'dobles-mati':
        c['xifra'] = f'{t.xifra} classes per setmana'
    elif t.id == 'docents-cavall':
        c['xifra'] = f'{t.xifra} docents'
    if c.get('validat'):
        resultat.update(estat='verd', etiqueta='Resolt amb la proposta')
        c['proposta_validada'] = True
        metode = resultat.get('metode_planer', '').split('; això encara')[0]
        if t.id == 'marge-grau-nou':
            metode = metode.rsplit('. ', 1)[0]
        resultat['metode_planer'] = metode.rstrip('.') + '. L’horari proposat ho confirma: comprovat.'
    if validada and t.id in ('hores-aula', 'fora-torn', 'aforament', 'ocupacio'):
        c['proposta_validada'] = True
        resultat['proposem'] = {
            'hores-aula': 'Aplicar la proposta: les classes que necessiten aula ja en tenen.',
            'fora-torn': 'Aplicar la proposta i revisar les excepcions de les classes que no es poden moure.',
            'aforament': f'Aplicar la proposta: corregeix les {t.xifra} classes; les {c.get("aforament_heretades", "—")} de grups fixats es queden igual.',
            'ocupacio': 'Consultar l’ocupació amb l’horari proposat.'}[t.id]
        regla = {'hores-aula': 'R5-SENSE-AULA', 'fora-torn': 'R1-TORN', 'aforament': 'R3-AFORAMENT'}.get(t.id)
        r = v.get('restriccions', {}).get(regla)
        if t.id == 'hores-aula' and 'classes_sense_aula' in v:
            r = {'compten': v['classes_sense_aula']}
        if r is not None:
            despres = r.get('compten', 0) + r.get('declarades', 0)
            c['comparacio'] = f"Avui {c['xifra']} → {numero(despres)} classes amb la proposta"
            resolt = despres == 0 or t.id == 'fora-torn'
            resultat.update(estat='verd' if resolt else 'ambre',
                etiqueta='Resolt amb la proposta' if resolt else 'Cal decidir')
            if t.id == 'fora-torn' and despres:
                resultat['frase'] = (f'{numero(despres)} classes queden com a excepcions declarades al torn; '
                    'les classes que ja estaven fixades es compten a part al detall tècnic.')
        elif t.id in ('hores-aula', 'fora-torn', 'aforament'):
            resultat.update(estat='verd', etiqueta='Resolt amb la proposta')
    if t.id == 'hores-mortes' and validada:
        minuts = v.get('objectius', {}).get('hores_mortes_min')
        setmanes = extra.get('setmanes_lectives')
        if minuts is not None and setmanes:
            despres = minuts / 60 / setmanes
            c['comparacio'] = f"Avui {c['xifra']} → {numero(round(despres, 1))} h per setmana amb la proposta"
    if t.id in ('hores-mortes', 'canvis-aula', 'dobles-mati') and 'setmanes_lectives' in extra:
        resultat['metode_planer'] += f" En aquest semestre comptem {numero(extra['setmanes_lectives'])} setmanes lectives."
    resultat.update(c=c)
    return resultat


def abast(t):
    setmana = (t.extra or {}).get('setmana')
    return f'Detall de la setmana del {dates_setmana(setmana)}' if setmana else 'Setmana no indicada'


def text_portada(t, info):
    """Les targetes comparteixen pregunta, unitat i estat amb el detall."""
    return dict(info)


def grup_estat(info):
    return {'vermell': 'Cal decidir', 'ambre': 'Cal decidir', 'verd': 'Resolt amb la proposta',
            'gris': 'Per saber-ho'}[info['estat']]


def ordena_respostes(resultat, infos):
    prioritat = {'Cal decidir': 0, 'Resolt amb la proposta': 1, 'Per saber-ho': 2}
    return sorted(resultat, key=lambda t: prioritat[grup_estat(infos[t.id])])
