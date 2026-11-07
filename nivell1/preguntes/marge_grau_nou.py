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
    marge = f'{marge_semestre:,.1f}'.translate(str.maketrans({',': '.', '.': ','}))
    return Troballa(ID, 'Marge per al grau nou', f'{marge} h',
        f'{marge} h d’aula ordinària queden al semestre després de reservar matins per a 1r i 2n, abans del grau nou.',
        'La xifra és el marge total del semestre, amb 30 hores per aula i setmana amb sessions; el detall per mida és setmanal; comparem les hores de totes les sessions de 1r i 2n, encara que avui siguin a la tarda, i del grau nou amb 30 hores setmanals per aula: excloem PLAB i dobles, i agrupem compartides amb la matrícula màxima coneguda. Per cada llindar estricte de places oferim com a màxim 19 aules ordinàries (reserva de les dues més petites), també amb la variant de seminaris; superar el balanç és necessari però no garanteix un horari viable.',
        sql_resum + '\n-- Detall setmanal\n' + sql,
        df, sessions.id_sessio.head(5).tolist(), 'taula',
        extra={'setmana': setmana, 'cap_per_mida': cap, 'hores_noves_aulari': float(global_.nou_hores), 'sql_exemples': sql_sessions})


def comprova():
    df, _ = consulta('marge_grau_nou_sessions', semestre=2, setmana=None)
    return [('sessions del grau nou al 2n semestre', 235, len(df))]
