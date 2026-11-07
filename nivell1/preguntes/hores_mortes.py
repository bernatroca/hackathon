"""Buits dins del mateix torn per agenda d'alumnat."""
import pandas as pd
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'hores-mortes'
ORDRE = 7


def calcula(semestre=2, setmana=None):
    setmana = setmana or setmana_tipica(semestre)
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
    total = float(taula.hores.sum())
    xifra = f'{total:,.1f}'.translate(str.maketrans({',': '.', '.': ','}))
    return Troballa(ID, 'Hores mortes d’avui', f'{xifra} h',
        f'Buits acumulats de les agendes d’alumnat a {setmana}, desglossats per cohort.',
        'El SQL extreu totes les classes, inclosos PLAB i dobles; en pandas reunim cada subgrup amb les teories compatibles per cohort, línia o número, i sumem els buits dins del mateix torn, excloent la pausa entre torns. Les compartides compten un cop per agenda i unim intervals solapats; el total és d’hores de grup, no d’hores per estudiant.',
        sql, taula, list(dict.fromkeys(exemples))[:5], 'barres', extra={'setmana': setmana})
