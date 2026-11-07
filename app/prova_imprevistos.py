"""Prova autònoma: streamlit run app/prova_imprevistos.py, sense dades reals."""
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import sys
from types import SimpleNamespace as NS

ARREL = Path(__file__).resolve().parent
for carpeta in (ARREL.parent, ARREL):
    if str(carpeta) not in sys.path:
        sys.path.insert(0, str(carpeta))

from nivell2.imprevistos import calcula


def dades_inventades():
    """Tots els noms, espais, grups i dies d'aquest exemple són inventats."""
    dilluns = date(2027, 2, 15)

    def sessio(sid, dies=0, *, tipus='TE', grup='TE/81', aula='Q9/0001', inici=510):
        data = dilluns + timedelta(days=dies)
        return NS(id=sid, codi='codi-inventat-' + sid, tipus=tipus, grup=grup,
                  data=data, dia='LMXJV'[data.weekday()], ini=inici, durada=60,
                  alumnes=28, aula=aula, sense_espai=False)

    sessions = [sessio('reserva-inventada'),
                sessio('creix-inventada', 1, aula='Q9/0002'),
                sessio('creix-setmana-inventada', 8, aula='Q9/0002'),
                sessio('avaria-inventada', 2, tipus='SEM', grup='SEM/811', aula='Q9/0003'),
                sessio('recuperacio-inventada', 3, tipus='PAUL', grup='PAUL/812', aula='Q9/0002'),
                sessio('suport-inventada', aula='Q9/1003', inici=630)]
    # Dues sessions del mateix grup en setmanes diferents.
    sessions[2].codi = sessions[1].codi
    base = NS(sessions={s.id: s for s in sessions}, tancaments=[], cancellades={})
    contingencies = deepcopy(base)
    contingencies.tancaments = [
        NS(aula='Q9/0001', data_ini=dilluns, data_fi=dilluns + timedelta(days=4), ini=0, fi=1440),
        NS(aula='Q9/0003', data_ini=dilluns + timedelta(days=2),
           data_fi=dilluns + timedelta(days=2), ini=0, fi=1440)]
    for sid in ('creix-inventada', 'creix-setmana-inventada'):
        contingencies.sessions[sid].alumnes = 64
    contingencies.cancellades = {'recuperacio-inventada': dilluns + timedelta(days=4)}
    abans = NS(files={s.id: NS(dia=s.dia, h_ini=f'{s.ini//60:02}:{s.ini%60:02}',
                              aula=s.aula, data='') for s in sessions})
    despres = deepcopy(abans)
    for sid in ('reserva-inventada', 'creix-inventada', 'creix-setmana-inventada', 'avaria-inventada'):
        despres.files[sid].aula = 'Q9/1003'
    despres.files['avaria-inventada'].h_ini = '10:30'
    despres.files['recuperacio-inventada'].data = (dilluns + timedelta(days=4)).isoformat()
    despres.files['recuperacio-inventada'].dia = 'V'
    despres.files['suport-inventada'].aula = 'Q9/0002'
    relaxacions = [{'restriccio': 'R1-FIXADA', 'sessions': 'reserva-inventada',
                   'justificacio': 'L’aula està tancada; canviem l’aula d’una classe fixada i conservem el dia i l’hora.'}]
    noms = {s.codi: f'Assignatura Inventada {i + 1}' for i, s in enumerate(sessions)}
    return calcula(base, contingencies, abans, despres, relaxacions,
                   resum={'temps_s': 1.24}, informe={'veredicte': 'VALIDA AMB RELAXACIONS DECLARADES'}, noms=noms)


if __name__ == '__main__':
    import streamlit as st
    from pagines import imprevistos

    st.set_page_config(page_title='Imprevistos · prova inventada', page_icon='▦', layout='wide')
    st.markdown('<style>' + (ARREL / 'estil.css').read_text() + '</style>', unsafe_allow_html=True)
    st.title('Imprevistos')
    st.caption('MOSTRA · Totes les dades són inventades; no són resultats del repte.')
    imprevistos.mostra(dades_inventades())
