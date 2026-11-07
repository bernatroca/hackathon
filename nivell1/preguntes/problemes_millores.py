"""Catàleg de problemes observables, amb una proposta concreta per categoria."""
import pandas as pd

from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'problemes-millores'
ORDRE = 6


def calcula(semestre=2, setmana=None):
    setmana = setmana if setmana is not None else setmana_tipica(semestre)
    taula, sql = consulta('problemes_millores', semestre=semestre, setmana=setmana)
    trobats = int((taula.xifra > 0).sum())
    exemples = list(dict.fromkeys(x for xs in taula.exemples if xs is not None for x in xs))[:5]
    taula['exemples'] = taula.exemples.map(lambda xs: list(xs[:5]) if xs is not None else [])
    taula['xifra'] = taula.xifra.map(lambda n: f'{int(n):,}'.replace(',', '.'))
    taula = pd.concat([taula, pd.DataFrame([{
        'problema': 'Dispersió d’aules per grup', 'xifra': 'Vegeu canvis-aula',
        'com_es_calcula': 'La pregunta canvis-aula dona les aules diferents de cada agenda i les sortides de passadís, sense llindar arbitrari de moltes aules.',
        'proposta': 'Prioritzar una aula base de teoria i agrupar les pràctiques compatibles al mateix passadís.',
        'exemples': []}])], ignore_index=True)
    return Troballa(
        id=ID, titol='Problemes i millores', xifra=f'{trobats} tipus',
        frase=f'{trobats} tipus de problemes detectats la setmana {setmana}, amb una proposta de millora per a cadascun.',
        metode='Comptem categories amb incidències a la setmana seleccionada; cada fila explica la seva unitat i exclusions, i les categories es poden solapar. Les compartides compten un cop, l’aforament suma els alumnes dels seus components i els solapaments segueixen el model aproximat de grups del verificador; no inferim assistència.',
        sql=sql, taula=taula, exemples=exemples, grafic='taula',
        extra={'setmana': setmana, 'tipus_detectats': trobats})


def comprova():
    t = calcula()
    return [('catàleg amb problemes únics', True, t.taula.problema.is_unique)]
