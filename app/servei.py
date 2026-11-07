"""Accés al contracte de troballes i a la llista de setmanes."""
import importlib
from pathlib import Path
import streamlit as st
from nivell1 import troballes
from nivell1.dades import connexio, AULES_DISPONIBLES


def versio_registre():
    arrel = Path(troballes.__file__).parent
    return tuple((str(p), p.stat().st_mtime_ns) for carpeta, patro in [('preguntes', '*.py'), ('consultes', '*.sql')]
                 for p in sorted((arrel / carpeta).glob(patro)))


@st.cache_data(ttl=None, show_spinner=False)
def ids_registre(versio):
    """Descobreix els IDs sense executar cap calcula()."""
    importlib.invalidate_caches()
    return [modul.ID for modul in troballes.moduls()]


def totes(semestre, setmana, versio):
    # Reutilitza també les troballes ja calculades des de la portada.
    return [una(id_, semestre, setmana, versio) for id_ in ids_registre(versio)]


@st.cache_data(ttl=None, show_spinner=False)
def una(id_, semestre, setmana, versio):
    importlib.invalidate_caches()
    return troballes.una(id_, semestre, setmana)


@st.cache_data(ttl=None, show_spinner=False)
def setmanes(semestre):
    return [str(fila[0]) for fila in connexio().execute(
        'SELECT DISTINCT setmana FROM sessions WHERE sem = $semestre ORDER BY setmana',
        {'semestre': semestre}).fetchall()]

# Regla 8: es reserven dues de les aules docents disponibles a l'inventari.
AULES_RESERVA = 2
# Places de l'escenari del repte anomenat grau-nou-40.
PLACES_GRAU_NOU = 40


@st.cache_data(ttl=None, show_spinner=False)
def inventari():
    """Única lectura d'inventari autoritzada; no calcula ocupació."""
    return connexio().execute('SELECT aula, edifici, tipus, capacitat FROM aules').df()
