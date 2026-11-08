"""Docents amb matí i tarda en una mateixa data segons el torn requerit."""
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
        metode='La xifra compta docents únics de tot el semestre i el detall és setmanal; comptem els que tenen sessions de matí i de tarda en una mateixa data actual, segons torn_requerit, el torn que demana la regla 1 a cada sessió. Incloem PLAB, dobles, màsters i sessions anuals datades al semestre; excloem docents buits. És una projecció dels torns sobre els dies actuals, amb docents assignats al grup, no presència confirmada ni simulació dels horaris fixats.',
        sql=sql_resum + '\n-- Detall setmanal\n' + sql, taula=taula, exemples=exemples, grafic='taula',
        extra={'setmana': setmana, 'docents_a_cavall': len(taula), 'docents_mati_tarda': int((taula.dies_mati_tarda > 0).sum()), 'docents_semestre': n})


def comprova():
    t = calcula()
    resum, _ = consulta('docents_cavall', semestre=2, setmana=None)
    return [('docents de la taula amb matí i tarda en una mateixa data', True,
             bool((t.taula.dies_mati_tarda > 0).all())),
            ('docents amb matí i tarda al semestre, segons torn_requerit', 23,
             t.extra['docents_semestre']),
            ('dies docent amb matí i tarda al semestre', 355,
             int(resum.dies_mati_tarda.sum()))]
