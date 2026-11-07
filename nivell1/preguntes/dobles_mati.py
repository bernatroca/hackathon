"""Dobles de cursos superiors que avui són al matí."""
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'dobles-mati'
ORDRE = 9


def calcula(semestre=2, setmana=None):
    setmana = setmana or setmana_tipica(semestre)
    df, sql = consulta('dobles_mati', semestre=semestre, setmana=setmana)
    df['hores_separacio'] = df.hores_separacio.where(~df.unitat.duplicated(), 0)
    taula = df.groupby('cohort', as_index=False).agg(sessions=('id_sessio', 'size'), hores_separacio=('hores_separacio', 'sum'))
    return Troballa(ID, 'Dobles de cursos superiors al matí', str(len(df)),
        f'{len(df)} sessions a {setmana}; separar-les requeriria {df.hores_separacio.sum():.1f} hores-aula addicionals.'.replace('.0 ', ',0 '),
        'Comptem les dobles sense espai propi, de cursos superiors, amb R1-TORN al matí; no hi ha cap clau que acrediti que assisteixin amb 1r o 2n (248 al semestre, excloses 27 dobles fixades de GEI:2n). El cost hipotètic de separar-les és la durada sense PLAB, amb compartides un sol cop; no acredita una aula disponible ni la mida necessària.',
        sql, taula, df.id_sessio.head(5).tolist(), 'barres',
        extra={'setmana': setmana, 'sessions_semestre': len(consulta('dobles_mati', semestre=semestre, setmana=None)[0])})


def comprova():
    df, _ = consulta('dobles_mati', semestre=2, setmana=None)
    torn, _ = consulta('dobles_mati_comprova', semestre=2, setmana=None)
    return [('dobles de cursos superiors al matí (aproximació de l’enunciat)', 248, len(df)),
            ('R1-TORN totals', 2008, int(torn.fora_torn.iloc[0]))]
