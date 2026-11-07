"""Pregunta 5: aforament amb la regla R3 del verificador."""
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'aforament'
ORDRE = 5


def calcula(semestre: int, setmana: str | None = None) -> Troballa:
    setmana = setmana if setmana is not None else setmana_tipica(semestre)
    taula, sql = consulta('aforament', semestre=semestre, setmana=setmana)
    incidencies = taula[taula.supera]
    resum, sql_resum = consulta('aforament', semestre=semestre, setmana=None)
    total = int((resum.supera & ~resum.heretada).sum())
    mostra = incidencies if not incidencies.empty else taula
    exemples = [sid for xs in mostra.exemples for sid in xs][:5]
    return Troballa(
        id=ID, titol='Grups amb més alumnes que places',
        xifra=f'{total:,}'.replace(',', '.'),
        frase=f'{total} incidències d’aforament computables al semestre, excloses les heretades de sessions fixades.',
        metode='La xifra és del semestre sencer i el detall és setmanal; com el R3-AFORAMENT oficial, sumem els alumnes de les sessions compartides dins de cada aula i comptem una incidència per classe i aula. La xifra exclou les incidències heretades amb totes les sessions fixades (la taula també les mostra); excloem dobles sense espai i aules fora de l’inventari; els alumnes sense dada compten com a zero, de manera que no permeten descartar excés d’aforament.',
        sql=sql_resum + '\n-- Detall setmanal\n' + sql, taula=incidencies.reset_index(drop=True), exemples=exemples, grafic='taula',
        extra={'setmana': setmana, 'classes_comprovades': len(taula),
               'classes_amb_alumnes_sense_dada': int((taula.sense_dada > 0).sum())})


def comprova() -> list[tuple[str, object, object]]:
    taula, _ = consulta('aforament', semestre=2, setmana=None)
    return [('R3-AFORAMENT del semestre', 43, int((taula.supera & ~taula.heretada).sum()))]
