"""Pregunta 2: demanda per bloc i cobertura de l'aula de partida."""
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'hores-aula'
ORDRE = 2


def calcula(semestre: int, setmana: str | None = None) -> Troballa:
    setmana = setmana if setmana is not None else setmana_tipica(semestre)
    taula, sql = consulta('hores_aula', semestre=semestre, setmana=setmana)
    r = taula.iloc[0]
    percent = round(100 * r.sense_aula / r.sessions_totals) if r.sessions_totals else 0
    n = f'{r.sense_aula:,}'.replace(',', '.')
    return Troballa(
        id=ID, titol='Hores-aula necessàries i disponibles', xifra=f'{percent} %',
        frase=f'{n} sessions del semestre no tenen aula; la demanda es mostra per bloc de la setmana {setmana}.',
        metode='El percentatge compta les files del semestre sense aula, inclosos PLAB i dobles, per reproduir la cobertura de l’enunciat. La demanda setmanal compta compartides un cop i exclou PLAB i dobles sense espai; cada bloc són 0,5 hores-aula i l’oferta nominal és de 19 aules (27 amb seminaris), sense descomptar festius.',
        sql=sql, taula=taula.drop(columns=['exemples']), exemples=list(r.exemples[:5]), grafic='linia',
        extra={'setmana': setmana, 'hores_demanda': float(taula.hores_demanda.sum()),
               'hores_disponibles': float(taula.disponibles.sum() / 2),
               'sessions_sense_aula': int(r.sense_aula), 'dobles': int(r.dobles), 'plab': int(r.plab)})


def comprova() -> list[tuple[str, object, object]]:
    taula, _ = consulta('hores_aula', semestre=2, setmana=setmana_tipica(2))
    r = taula.iloc[0]
    return [('sessions sense aula', 5722, int(r.sense_aula)),
            ('percentatge sense aula arrodonit', 74, round(100 * r.sense_aula / r.sessions_totals)),
            ('dobles sense aula', 262, int(r.dobles)),
            ('PLAB sense aula', 919, int(r.plab))]
