"""Buits dins del mateix torn per agenda d'alumnat."""
import pandas as pd
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'hores-mortes'
ORDRE = 7


def _detall(semestre, setmana):
    df, sql = consulta('hores_mortes', semestre=semestre, setmana=setmana)
    files, exemples = [], []
    for (cohort, data), dia in df.groupby(['cohort', 'data'], sort=True):
        # Cada subgrup rep les TE compatibles segons _alumnat_comparteix,
        # inclòs el cas TE/910 + PAUL/902.
        practiques = dia[dia.tipus != 'TE']
        agendes = []
        for num, grup in practiques.groupby('num_grup'):
            teoria = dia[(dia.tipus == 'TE') & ((dia.linia.isin(grup.linia)) | (dia.num_grup == num))]
            agendes.append(pd.concat([grup, teoria]))
        for linia, teoria in dia[dia.tipus == 'TE'].groupby('linia'):
            if not any(((practiques.linia == linia) | practiques.num_grup.isin(teoria.num_grup))):
                agendes.append(teoria)
        minuts = 0
        for agenda in agendes:
            agenda = agenda.sort_values(['ini_min', 'id_sessio']).drop_duplicates('unitat')
            # Unim els intervals solapats: no generen un buit fictici.
            fi = None
            anterior = None
            for s in agenda.itertuples():
                if fi is not None and s.ini_min > fi and ((fi <= 870) == (s.ini_min < 870)):
                    minuts += s.ini_min - fi
                    exemples.extend([anterior, s.id_sessio])
                if fi is None or s.fi_min > fi:
                    fi, anterior = s.fi_min, s.id_sessio
        files.append({'cohort': cohort, 'minuts': minuts})
    taula = pd.DataFrame(files, columns=['cohort', 'minuts']).groupby('cohort', as_index=False).sum()
    taula['hores'] = taula.minuts / 60
    return taula, sql, list(dict.fromkeys(exemples))[:5]


def calcula(semestre=2, setmana=None):
    setmana = setmana if setmana is not None else setmana_tipica(semestre)
    taula, sql, exemples = _detall(semestre, setmana)
    resum, sql_resum, _ = _detall(semestre, None)
    setmanes, sql_setmanes = consulta('semestre_setmanes', semestre=semestre, setmana=None)
    total = float(resum.hores.sum()) / max(int(setmanes.setmanes.iloc[0]), 1)
    xifra = f'{total:,.1f}'.translate(str.maketrans({',': '.', '.': ','}))
    return Troballa(ID, 'Hores mortes: mitjana setmanal', f'{xifra} h',
        f'{xifra} h mortes de mitjana setmanal al semestre, sumant les agendes d’alumnat.',
        'La xifra és la mitjana de totes les setmanes del semestre i el detall és setmanal; són hores de grup, no per estudiant. Incloem PLAB i dobles, reunim les teories compatibles amb cada subgrup i sumem buits dins del torn, unint solapaments i comptant compartides un cop per agenda.',
        sql_setmanes + '\n-- Resum del semestre\n' + sql_resum + '\n-- Detall setmanal\n' + sql, taula, exemples, 'barres',
        extra={'setmana': setmana, 'hores_semestre': float(resum.hores.sum())})
