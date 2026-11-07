"""Balanç necessari d'hores-aula per mida; no és una prova d'horari viable."""
from nivell1.dades import consulta, setmana_pitjor
from nivell1.troballes import Troballa

ID = 'marge-grau-nou'
ORDRE = 11


def calcula(semestre=2, setmana=None):
    setmana = setmana or setmana_pitjor(semestre)
    df, sql = consulta('marge_grau_nou', semestre=semestre, setmana=setmana)
    sessions, sql_sessions = consulta('marge_grau_nou_sessions', semestre=semestre, setmana=setmana)
    ordinaries = df[~df.seminaris]
    global_ = ordinaries[ordinaries.llindar == 0].iloc[0]
    cap = bool((ordinaries.saldo_hores >= 0).all())
    resum, sql_resum = consulta('marge_grau_nou', semestre=semestre, setmana=None)
    marge_semestre = resum[(~resum.seminaris) & (resum.llindar == 0)].iloc[0].marge_hores
    marge = f'{marge_semestre:,.0f}'.translate(str.maketrans({',': '.', '.': ','}))
    return Troballa(ID, 'Marge per al grau nou', f'{global_.nou_hores:g} h',
        f"Necessita unes {global_.nou_hores:g} h d'aula a la setmana; a la setmana més plena en queden {global_.marge_hores:g} de lliures al matí ({marge} h de marge en tot el semestre). Falta validar-ho amb l'horari de la part 2." if setmana == setmana_pitjor(semestre) else
        f"Necessita unes {global_.nou_hores:g} h d'aula a la setmana; a la setmana seleccionada ({setmana}) en queden {global_.marge_hores:g} de lliures al matí ({marge} h de marge en tot el semestre). Falta validar-ho amb l'horari de la part 2.",
        'La xifra gran és la suma de les durades de les sessions del grau nou que necessiten aula al matí a la setmana més plena per defecte, o a la seleccionada; les hores lliures són l’oferta de les 19 aules ordinàries menys la demanda actual del torn de matí, abans d’afegir el grau nou. El marge del semestre suma aquest mateix balanç en totes les setmanes amb sessions, descomptant les aturades del calendari dels matins feiners; incloem sessions amb zero alumnes, excloem PLAB i dobles, i les compartides ocupen una sola aula i sumen alumnes: el balanç per mida, també amb la variant de seminaris, queda pendent de validar amb un horari.',
        sql_resum + '\n-- Detall setmanal\n' + sql,
        df, sessions.id_sessio.head(5).tolist(), 'taula',
        extra={'setmana': setmana, 'marge_semestre_h': float(marge_semestre), 'demanda_h_setmana': float(global_.nou_hores), 'lliures_h_setmana': float(global_.marge_hores), 'estat_provisional': True, 'nota': "Balanç d'hores: falta que la part 2 ho validi amb un horari", 'cap_per_mida': cap, 'hores_noves_aulari': float(global_.nou_hores), 'sql_exemples': sql_sessions})


def comprova():
    df, _ = consulta('marge_grau_nou_sessions', semestre=2, setmana=None)
    detall, _ = consulta('marge_grau_nou', semestre=2, setmana=setmana_pitjor(2))
    total = detall[(~detall.seminaris) & (detall.llindar == 0)].iloc[0]
    return [('sessions del grau nou al 2n semestre', 235, len(df)),
            ('demanda del grau nou a la pitjor setmana (hores)', 26.0, float(total.nou_hores)),
            ('marge abans del grau nou a la pitjor setmana (hores)', 181.0, float(total.marge_hores))]
