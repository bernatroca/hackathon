"""Pregunta 2: demanda per bloc i cobertura de l'aula de partida."""
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'hores-aula'
ORDRE = 2


def classes(semestre=2):
    """Classes pendents d'assignació; mateix abast que la xifra principal."""
    return consulta('hores_aula_classes', semestre=semestre)[0]


def calcula(semestre: int, setmana: str | None = None) -> Troballa:
    setmana = setmana if setmana is not None else setmana_tipica(semestre)
    taula, sql = consulta('hores_aula', semestre=semestre, setmana=setmana)
    r = taula.iloc[0]
    percent = round(100 * r.sense_aula / r.sessions_totals) if r.sessions_totals else 0
    n = f'{r.sense_aula:,}'.replace(',', '.')
    pendents = f'{r.per_assignar:,}'.replace(',', '.')
    desglos = {'total': int(r.sense_aula), 'per_assignar': int(r.per_assignar),
               'plab': int(r.plab), 'dobles': int(r.dobles)}
    return Troballa(
        id=ID, titol='Hores-aula necessàries i disponibles', xifra=f'{percent} %',
        frase=f'{percent} % de les classes no tenen aula a les dades ({n}). '
              f'Les que cal assignar de debò són {pendents}: la resta són laboratoris, '
              'que no es toquen, i dobles titulacions, que no necessiten aula.',
        metode='El percentatge compta les files del semestre sense aula, inclosos PLAB i dobles, per reproduir la cobertura de l’enunciat; el desglossament separa les que cal assignar, excloent PLAB i dobles sense espai. La demanda setmanal compta compartides un cop i exclou PLAB i dobles sense espai; cada bloc són 0,5 hores-aula i l’oferta nominal és de 19 aules (27 amb seminaris), sense descomptar festius.',
        sql=sql, taula=taula.drop(columns=['exemples']), exemples=list(r.exemples[:5]), grafic='linia',
        extra={'hores_per_torn': taula.groupby('franja', as_index=False).agg(
                   demanda_h=('hores_demanda', 'sum'), oferta_h=('disponibles', lambda x: x.sum()/2)),
               'desglos': desglos, 'setmana': setmana, 'hores_demanda': float(taula.hores_demanda.sum()),
               'hores_disponibles': float(taula.disponibles.sum() / 2),
               'sessions_sense_aula': int(r.sense_aula), 'dobles': int(r.dobles), 'plab': int(r.plab)})


def comprova() -> list[tuple[str, object, object]]:
    taula, _ = consulta('hores_aula', semestre=2, setmana=setmana_tipica(2))
    r = taula.iloc[0]
    return [('sessions sense aula', 5722, int(r.sense_aula)),
            ('percentatge sense aula arrodonit', 74, round(100 * r.sense_aula / r.sessions_totals)),
            ('dobles sense aula', 262, int(r.dobles)),
            ('PLAB sense aula', 919, int(r.plab)),
            ('sessions per assignar (R5-SENSE-AULA)', 4541, int(r.per_assignar)),
            ('desglossament complet de sessions sense aula', int(r.sense_aula),
             int(r.per_assignar + r.plab + r.dobles))]
