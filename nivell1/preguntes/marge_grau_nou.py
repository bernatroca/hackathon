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
    marge = f'{global_.marge_hores:,.1f}'.translate(str.maketrans({',': '.', '.': ','}))
    return Troballa(ID, 'Marge per al grau nou', f'{marge} h',
        f'A {setmana}, el grau nou demana {sessions.durada_min.sum()/60:g} hores totals; ' +
        ('passa el balanç per mida, pendent de trobar un horari.' if cap else 'el balanç per mida falla amb aules ordinàries.'),
        'Comparem les hores de totes les sessions de 1r i 2n, encara que avui siguin a la tarda, i del grau nou amb 30 hores setmanals per aula: excloem PLAB i dobles, i agrupem compartides amb la matrícula màxima coneguda. Per cada llindar estricte de places oferim com a màxim 19 aules ordinàries (reserva de les dues més petites), també amb la variant de seminaris; superar el balanç és necessari però no garanteix un horari viable.',
        sql,
        df, sessions.id_sessio.head(5).tolist(), 'taula',
        extra={'setmana': setmana, 'cap_per_mida': cap, 'hores_noves_aulari': float(global_.nou_hores), 'sql_exemples': sql_sessions})


def comprova():
    df, _ = consulta('marge_grau_nou_sessions', semestre=2, setmana=None)
    return [('sessions del grau nou al 2n semestre', 235, len(df))]
