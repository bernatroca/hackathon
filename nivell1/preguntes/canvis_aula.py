"""Dispersió d'aules de l'agenda aproximada d'alumnat del verificador."""
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'canvis-aula'
ORDRE = 8


def calcula(semestre=2, setmana=None):
    setmana = setmana if setmana is not None else setmana_tipica(semestre)
    taula, sql = consulta('canvis_aula', semestre=semestre, setmana=setmana)
    total = int(taula.fora_passadis.sum())
    exemples = list(dict.fromkeys(x for xs in taula.exemples for x in xs))[:5]
    return Troballa(
        id=ID, titol='Canvis d’aula per grup', xifra=f'{total:,}'.replace(',', '.'),
        frase=f'{total:,} canvis fora del passadís en les agendes de grup de la setmana {setmana}.'.replace(',', '.'),
        metode='Per cohort, línia i subgrup, afegim la teoria als subgrups del dia i comptem les aules principals diferents de la setmana i els canvis entre sessions consecutives del mateix dia, encara que hi hagi buits o solapaments. Les compartides compten un cop per agenda; els passos sense alguna aula no compten com a canvi i el passadís és espina i planta.',
        sql=sql, taula=taula, exemples=exemples, grafic='taula',
        extra={'setmana': setmana, 'canvis_aula': int(taula.canvis_aula.sum()),
               'passos_solapats': int(taula.passos_solapats.sum())})


def comprova():
    t = calcula()
    return [('sortides de passadís incloses en els canvis', True,
             int(t.taula.fora_passadis.sum()) <= int(t.taula.canvis_aula.sum()))]
