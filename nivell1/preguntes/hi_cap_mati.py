"""Pregunta 4: pic actual i condicions necessàries de capacitat al matí."""
from nivell1.dades import consulta, setmana_pitjor
from nivell1.troballes import Troballa

ID = 'hi-cap-mati'
ORDRE = 4


def calcula(semestre=2, setmana=None):
    setmana = setmana if setmana is not None else setmana_pitjor(semestre)
    pic, a = consulta('hi_cap_mati_pic', semestre=semestre, setmana=setmana)
    ocupacio, b = consulta('hi_cap_mati_ocupacio', semestre=semestre, setmana=setmana)
    mida, c = consulta('hi_cap_mati_mida', semestre=semestre, setmana=setmana)
    resum, sql_resum = consulta('hi_cap_mati_pic', semestre=semestre, setmana=None)
    maxim = int(resum.classes.max()) if len(resum) else 0
    falla = mida[mida.falla]
    falla_sem = mida[mida.falla_amb_seminaris]
    pct = f'{ocupacio.iloc[0].ocupacio_pct:.2f}'.replace('.', ',')
    conclusio = (f"No hi cap per mida: falla per a grups de més de {int(falla.iloc[0].llindar)} alumnes."
                 if len(falla) else 'Les hores totals i els llindars de mida no descarten que hi càpiga; cal validar un horari.')
    conclusio += (' Els 8 seminaris tampoc resolen el dèficit.' if len(falla_sem)
                  else ' Amb els 8 seminaris no falla cap llindar de mida.')
    return Troballa(
        id=ID, titol='Hi cap el matí de 1r i 2n?', xifra=f'{maxim} de 19',
        frase=f'{maxim} de 19 aules necessàries al pic actual del semestre per a 1r i 2n al matí.',
        metode="La xifra és el pic de tot el semestre; els gràfics corresponen a la setmana seleccionada; es compten les cohorts explícites de 1r i 2n, sense PLAB ni dobles i amb les compartides un sol cop (sumant-ne els alumnes); el pic manté les hores actuals, però l’ocupació i la mida inclouen tota la durada que cal portar al matí. "
               "L’oferta és de cinc matins de sis hores, amb reserva flexible de dues aules petites: per llindar és una cota optimista; superar-la prova impossibilitat, complir-la no prova viabilitat.",
        sql=sql_resum+'\n-- capa a\n'+a+'\n-- capa b\n'+b+'\n-- capa c\n'+c,
        taula=pic, exemples=list(ocupacio.iloc[0].exemples[:5]), grafic='linia',
        extra={'setmana': setmana, 'pic': pic, 'ocupacio': ocupacio, 'per_mida': mida,
               'problemes': ['La setmana pitjor és la del pic global de demanda de setmana_pitjor(); no prova que sigui la pitjor per a cada llindar.',
                             'S’exclouen cohorts de curs desconegut encara que torn_requerit sigui mati.',
                             'L’oferta és nominal de cinc dies, sense descomptar aturades del calendari.']})


def comprova():
    t = calcula(2, None)
    pct = float(t.extra['ocupacio'].iloc[0].ocupacio_pct)
    return [('pic actual al matí', 15, int(t.extra['pic'].classes.max())),
            ('ocupació entre 67 % i 70 %', True, 67 <= pct <= 70)]
