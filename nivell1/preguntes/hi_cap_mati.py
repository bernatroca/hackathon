"""Pregunta 4: condicions necessàries del model nou als dos torns."""
from nivell1.dades import consulta, setmana_pitjor
from nivell1.troballes import Troballa

ID = 'hi-cap-mati'
ORDRE = 4


def _percent(valor):
    return f'{valor:.0f} %'


def _coll(mida):
    # 0 hores contra 0 hores és un llindar buit, no un coll d'ampolla.
    candidats = mida[(mida.oferta_h > 0) | (mida.demanda_h > 0)]
    if candidats.empty:
        return {}
    fila = candidats.sort_values(
        ['marge_h', 'marge_pct', 'setmana', 'torn', 'llindar']).iloc[0]
    return {clau: (int(fila[clau]) if clau == 'llindar' else
                   float(fila[clau]) if clau.endswith(('_h', '_pct')) else fila[clau])
            for clau in ['torn', 'setmana', 'llindar', 'demanda_h', 'oferta_h',
                         'marge_h', 'marge_pct']}


def calcula(semestre=2, setmana=None):
    if semestre not in (1, 2):
        raise ValueError('El semestre ha de ser 1 o 2.')
    seleccionada = setmana if setmana is not None else setmana_pitjor(semestre)
    pic, a = consulta('hi_cap_mati_pic', semestre=semestre, setmana=seleccionada)
    resum_pic, a_resum = consulta('hi_cap_mati_pic', semestre=semestre, setmana=None)
    ocupacions, b = consulta('hi_cap_mati_ocupacio', semestre=semestre, setmana=None)
    mides, c = consulta('hi_cap_mati_mida', semestre=semestre, setmana=None)
    if seleccionada not in set(ocupacions.setmana):
        raise ValueError(f'La setmana {seleccionada} no pertany al semestre {semestre}.')
    oficial = ocupacions[ocupacions.variant == 'oficial']
    pitjors = oficial[oficial.ordre_pitjor == 1].copy()
    torns = pitjors.rename(columns={'setmana': 'setmana_pitjor'}).reset_index(drop=True)
    mati = torns[torns.torn == 'mati'].iloc[0]
    tarda = torns[torns.torn == 'tarda'].iloc[0]
    mida_oficial = mides[mides.variant == 'oficial']
    coll = _coll(mida_oficial)
    falla = bool(mida_oficial.falla.any())
    pct_m, pct_t = _percent(mati.ocupacio_pct), _percent(tarda.ocupacio_pct)
    if falla:
        balanc = 'No hi cap per mida'
    else:
        balanc = f'Hi ha marge d’hores al matí ({pct_m} d’ocupació) i a la tarda ({pct_t} d’ocupació)'
    if coll:
        marge = f"{coll['marge_h']:.1f}".replace('.', ',')
        balanc += (f"; el menor marge és al torn de {('matí' if coll['torn'] == 'mati' else 'tarda')}, "
                   f"la setmana {coll['setmana']}, per sobre de {coll['llindar']} places "
                   f"({marge} h de marge; demanda {coll['demanda_h']:g} h)")
    ocupacio = oficial[(oficial.setmana == seleccionada) & (oficial.torn == 'mati')].copy()
    mida = mida_oficial[(mida_oficial.setmana == seleccionada) & (mida_oficial.torn == 'mati')].copy()
    return Troballa(
        id=ID, titol='Hi cap el model nou, al matí i a la tarda?',
        xifra=f'{pct_m} i {pct_t}',
        frase=balanc+'. Que l’horari encaixi de debò ho valida la part 2.',
        metode='És una condició necessària: cada setmana es compten les hores d’aulari segons el torn requerit, incloses GEI:? i les de zero alumnes, sense PLAB ni dobles; les compartides ocupen una vegada i en sumem els alumnes. '
               'Es resten festius, dies no lectius i aturades del calendari (les avaluacions no es consideren aturades), amb dues aules petites de reserva flexible i la variant de 8 seminaris; complir els límits no valida els solapaments de docent i alumnat ni la reserva hora a hora.',
        sql='-- capa a: setmana seleccionada\n'+a+'\n-- capa a: semestre complet\n'+a_resum+
            '\n-- capa b: totes les setmanes i variants\n'+b+'\n-- capa c: totes les setmanes i variants\n'+c,
        taula=pic, exemples=list(mati.exemples[:5]), grafic='linia',
        extra={'setmana': seleccionada, 'pic': pic, 'ocupacio': ocupacio, 'per_mida': mida,
               'pic_semestre': int(resum_pic.classes.max()) if len(resum_pic) else 0,
               'torns': torns, 'coll_ampolla': coll, 'falla_per_mida': falla,
               'ocupacio_setmanes': ocupacions, 'per_mida_setmanes': mides,
               'torns_15_21': ocupacions[(ocupacions.variant == '15-21') &
                                       (ocupacions.ordre_pitjor == 1)].copy(),
               'coll_ampolla_15_21': _coll(mides[mides.variant == '15-21']),
               'falla_per_mida_amb_seminaris': bool(mida_oficial.falla_amb_seminaris.any()),
               'problemes': ['L’oferta per mida és una cota optimista amb reserva flexible; les mides desconegudes només entren a l’ocupació total.',
                             'El menor marge absolut pot correspondre a un llindar amb demanda zero; se n’explicita la demanda i s’exclouen només els llindars 0 contra 0.',
                             'Els registres avaluacio no es descompten: no indiquen una aturada docent; alguns contenen classes de partida.',
                             'Les referències 397 h de matí i 259 h de tarda corresponen a setmanes diferents (W06 i W09); les compartides es dedupliquen.']})


def comprova():
    t = calcula(2, None)
    torns = t.extra['torns']
    mati = torns[torns.torn == 'mati']
    tarda = torns[torns.torn == 'tarda']
    return [('pic actual al matí', 15, t.extra['pic_semestre']),
            ('ocupació entre 67 % i 70 %', True, 67 <= float(mati.iloc[0].ocupacio_pct) <= 70),
            ('existeix el torn de tarda', True, len(tarda) == 1),
            ('ocupació de tarda com a màxim 100 %', True,
             len(tarda) == 1 and float(tarda.iloc[0].ocupacio_pct) <= 100)]
