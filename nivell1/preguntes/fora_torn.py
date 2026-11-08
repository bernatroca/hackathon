"""Pregunta 3: torn nou i diferència amb les incidències heretades."""
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'fora-torn'
ORDRE = 3


def classes(semestre=2):
    """Classes que compten al resum semestral, sense duplicar compartides."""
    return consulta('fora_torn_classes', semestre=semestre)[0]


def _nombre(valor):
    return f'{int(valor):,}'.replace(',', '.')


def calcula(semestre=2, setmana=None):
    setmana = setmana if setmana is not None else setmana_tipica(semestre)
    dades, sql = consulta('fora_torn', semestre=semestre, setmana=setmana)
    total = dades[(dades.abast == 'semestre') & (dades.cohort == 'TOTAL')].iloc[0]
    taula = dades[(dades.abast == 'setmana') & (dades.cohort != 'TOTAL')].copy()
    return Troballa(
        id=ID, titol='Quantes sessions són fora del torn nou?',
        xifra=f'{int(total.sessions):,}'.replace(',', '.'),
        frase=f"{_nombre(total.sessions)} sessions del semestre computen a R1-TORN; {_nombre(total.heretades)} més són fora de torn però fixades heretades.",
        metode="Es compara el torn requerit amb l’hora d’inici (tall a les 14.30): el total del semestre inclou PLAB i dobles, però R1-TORN exclou les fixades sense moure, heretades segons el verificador. "
               "El gràfic cobreix el semestre per titulació i curs (una classe compartida pot aparèixer en diversos); les hores-aula exclouen PLAB i dobles i compten les compartides un sol cop.",
        sql=sql, taula=taula, exemples=list(total.exemples[:5]), grafic='barres',
        extra={'setmana': setmana, 'resum': dades[dades.cohort == 'TOTAL'].copy(),
               'per_cohort': dades[dades.cohort != 'TOTAL'].copy()})


def comprova():
    dades, _ = consulta('fora_torn', semestre=2, setmana=setmana_tipica(2))
    t = dades[(dades.abast == 'semestre') & (dades.cohort == 'TOTAL')].iloc[0]
    return [('R1-TORN no heretades', 2008, int(t.sessions)),
            ('comparació directa de torn', 3246, int(t.sessions_directes)),
            ('fixades heretades', 1238, int(t.heretades))]
