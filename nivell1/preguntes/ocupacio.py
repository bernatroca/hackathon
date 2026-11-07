"""Pregunta 1: ocupació física de les aules de l'horari actual."""
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'ocupacio'
ORDRE = 1


def calcula(semestre: int, setmana: str | None = None) -> Troballa:
    setmana = setmana if setmana is not None else setmana_tipica(semestre)
    taula, sql = consulta('ocupacio', semestre=semestre, setmana=setmana)
    ranking = (taula[taula.aula != 'sense aula'][['aula', 'percent_ocupacio']]
               .drop_duplicates().reset_index(drop=True))
    primera = ranking.iloc[0]
    exemples = list(dict.fromkeys(
        sid for xs in taula.loc[taula.valor > 0, 'exemples'] for sid in xs))[:5]
    percent = f'{primera.percent_ocupacio:.1f}'.replace('.', ',')
    return Troballa(
        id=ID, titol='Ocupació per aula, dia i bloc', xifra=f'{percent} %',
        frase=f"{primera.aula} és l’aula més ocupada de la setmana {setmana}.",
        metode='Comptem classes físiques per aula i bloc de mitja hora, inclosos laboratoris i aules addicionals, amb les compartides un cop i les dobles sense espai excloses de les aules. El percentatge és el de blocs ocupats sobre els 125 de dilluns a divendres; la fila «sense aula» mostra totes les sessions sense aula, compartides un cop.',
        sql=sql, taula=taula, exemples=exemples, grafic='heatmap',
        extra={'setmana': setmana, 'ranking_aules': ranking.to_dict('records')})
