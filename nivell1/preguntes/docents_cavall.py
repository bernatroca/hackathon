"""Docents assignats a cursos inicials i superiors, segons els dies actuals."""
from nivell1.dades import consulta, setmana_tipica
from nivell1.troballes import Troballa

ID = 'docents-cavall'
ORDRE = 10


def calcula(semestre=2, setmana=None):
    setmana = setmana if setmana is not None else setmana_tipica(semestre)
    taula, sql = consulta('docents_cavall', semestre=semestre, setmana=setmana)
    resum, sql_resum = consulta('docents_cavall', semestre=semestre, setmana=None)
    n = int((resum.dies_mati_tarda > 0).sum())
    exemples = list(dict.fromkeys(x for xs in taula.exemples for x in xs))[:5]
    return Troballa(
        id=ID, titol='Docents a cavall', xifra=f'{n:,}'.replace(',', '.'),
        frase=f'{n} docents tindrien matí i tarda algun mateix dia del semestre amb el model nou.',
        metode='La xifra compta docents únics de tot el semestre i el detall és setmanal; comptem docents diferents assignats a sessions de cohorts de 1r o 2n i de 3r o 4t, i els que tenen les dues bandes el mateix dia actual de la setmana. Incloem PLAB i dobles; excloem docents buits i cursos diferents d’aquests quatre; és una projecció per curs, amb docents assignats al grup, no presència confirmada ni simulació dels horaris fixats.',
        sql=sql_resum + '\n-- Detall setmanal\n' + sql, taula=taula, exemples=exemples, grafic='taula',
        extra={'setmana': setmana, 'docents_a_cavall': len(taula), 'docents_mati_tarda': int((taula.dies_mati_tarda > 0).sum()), 'docents_semestre': n})


def comprova():
    t = calcula()
    return [('docents amb dues bandes inclosos en els docents a cavall', True,
             t.extra['docents_mati_tarda'] <= t.extra['docents_a_cavall'])]
