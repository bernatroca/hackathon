"""Buits dins del mateix torn per agenda d'alumnat."""
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'hores-mortes'
ORDRE = 7


def _detall(semestre, setmana):
    df, sql = consulta('hores_mortes', semestre=semestre, setmana=setmana)
    exemples = []
    for ids in df.exemples.dropna():
        exemples.extend(ids)
    return df.drop(columns='exemples'), sql, list(dict.fromkeys(exemples))[:5]


def calcula(semestre=2, setmana=None):
    setmana = setmana if setmana is not None else setmana_tipica(semestre)
    taula, sql, exemples = _detall(semestre, setmana)
    resum, sql_resum, _ = _detall(semestre, None)
    setmanes, sql_setmanes = consulta('semestre_setmanes', semestre=semestre, setmana=None)
    total = float(resum.hores.sum()) / max(int(setmanes.setmanes.iloc[0]), 1)
    xifra = f'{total:,.1f}'.translate(str.maketrans({',': '.', '.': ','}))
    return Troballa(ID, 'Hores mortes: mitjana setmanal', f'{xifra} h',
        f'{xifra} h mortes de mitjana setmanal al semestre, sumant les agendes d’alumnat.',
        'La xifra és la mitjana de totes les setmanes del semestre i el detall és setmanal; són hores de grup, no per estudiant. Incloem PLAB i dobles, en SQL reunim les teories compatibles amb cada subgrup i sumem buits dins del torn, unint solapaments i comptant compartides un cop per agenda.',
        sql_setmanes + '\n-- Resum del semestre\n' + sql_resum + '\n-- Detall setmanal\n' + sql, taula, exemples, 'barres',
        extra={'setmana': setmana, 'hores_semestre': float(resum.hores.sum())})


def comprova():
    resum, _, _ = _detall(2, None)
    return [('minuts d’hores mortes del semestre (verificador)', 72930, int(resum.minuts.sum()))]
