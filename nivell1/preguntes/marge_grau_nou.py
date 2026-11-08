"""Balanç necessari d'hores-aula per mida; no és una prova d'horari viable."""
from nivell1.dades import consulta
from nivell1.troballes import Troballa

ID = 'marge-grau-nou'
ORDRE = 11


def calcula(semestre=2, setmana=None):
    per_defecte = setmana is None
    setmanes, _ = consulta('marge_grau_nou_setmanes', semestre=semestre)
    setmana = setmana or str(setmanes.iloc[0].setmana)
    df, sql = consulta('marge_grau_nou', semestre=semestre, setmana=setmana)
    sessions, sql_sessions = consulta('marge_grau_nou_sessions', semestre=semestre, setmana=setmana)
    ordinaries = df[~df.seminaris]
    global_ = ordinaries[ordinaries.llindar == 0].iloc[0]
    cap = bool((ordinaries.saldo_hores >= 0).all())
    etiqueta = 'amb més demanda de matí' if per_defecte else 'seleccionada'
    return Troballa(ID, 'Marge per al grau nou', f'{global_.nou_hores:g} h',
        f"Necessita {global_.nou_hores:g} h d'aula a la setmana {etiqueta}; en queden {global_.marge_hores:g} de lliures al matí abans d’incorporar-lo. Falta validar-ho amb l’horari proposat.",
        'Comparem les hores del grau nou amb les hores lliures de les 19 aules ordinàries al matí. Per defecte triem la setmana amb més hores-aula de demanda de matí de l’horari existent. Descomptem totes les aturades del calendari, inclosa l’avaluació; incloem sessions amb zero alumnes, excloem laboratoris i dobles sense espai propi, i les compartides ocupen una sola aula i sumen alumnes. El balanç per mida no prova per si sol que l’horari encaixi.',
        sql, df, sessions.id_sessio.head(5).tolist(), 'taula',
        extra={'setmana': setmana, 'criteri_setmana': 'demanda_mati',
               'demanda_h_setmana': float(global_.nou_hores), 'lliures_h_setmana': float(global_.marge_hores),
               'estat_provisional': True, 'cap_per_mida': cap,
               'hores_noves_aulari': float(global_.nou_hores), 'sql_exemples': sql_sessions})


def comprova():
    df, _ = consulta('marge_grau_nou_sessions', semestre=2, setmana=None)
    setmanes, _ = consulta('marge_grau_nou_setmanes', semestre=2)
    detall, _ = consulta('marge_grau_nou', semestre=2, setmana=str(setmanes.iloc[0].setmana))
    total = detall[(~detall.seminaris) & (detall.llindar == 0)].iloc[0]
    return [('sessions del grau nou al 2n semestre', 235, len(df)),
            ('demanda del grau nou a la setmana amb més demanda de matí (hores)', 27.0, float(total.nou_hores)),
            ('marge abans del grau nou a la setmana amb més demanda de matí (hores)', 173.0, float(total.marge_hores))]
