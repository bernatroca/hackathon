"""Dispersió d'aules de l'agenda aproximada d'alumnat del verificador."""
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'canvis-aula'
ORDRE = 8


def calcula(semestre=2, setmana=None):
    setmana = setmana if setmana is not None else setmana_tipica(semestre)
    taula, sql = consulta('canvis_aula', semestre=semestre, setmana=setmana)
    resum, sql_resum = consulta('canvis_aula', semestre=semestre, setmana=None)
    setmanes, sql_setmanes = consulta('semestre_setmanes', semestre=semestre, setmana=None)
    total = float(resum.fora_passadis.sum()) / max(int(setmanes.setmanes.iloc[0]), 1)
    xifra = f'{total:,.1f}'.translate(str.maketrans({',': '.', '.': ','}))
    exemples = list(dict.fromkeys(x for xs in taula.exemples for x in xs))[:5]
    return Troballa(
        id=ID, titol='Canvis de passadís: mitjana setmanal', xifra=xifra,
        frase=f'{xifra} canvis de passadís per setmana de mitjana al semestre, sumant les agendes de grup.',
        metode='La xifra és la mitjana setmanal del semestre, incloses les setmanes sense canvis; el detall correspon a la setmana seleccionada; per cohort, línia i subgrup, afegim la teoria als subgrups del dia i comptem les aules principals diferents de la setmana i els canvis entre sessions consecutives del mateix dia, encara que hi hagi buits o solapaments. Les compartides compten un cop per agenda; els passos sense alguna aula no compten com a canvi i el passadís és espina i planta.',
        sql=sql_setmanes + '\n-- Resum del semestre\n' + sql_resum + '\n-- Detall setmanal\n' + sql, taula=taula, exemples=exemples, grafic='taula',
        extra={'setmana': setmana, 'canvis_aula': int(taula.canvis_aula.sum()),
               'passos_solapats': int(taula.passos_solapats.sum())})


def comprova():
    t = calcula()
    return [('sortides de passadís incloses en els canvis', True,
             int(t.taula.fora_passadis.sum()) <= int(t.taula.canvis_aula.sum()))]
