"""Accés al contracte de troballes i a la llista de setmanes."""
import importlib
from pathlib import Path
import streamlit as st
from nivell1 import troballes
from nivell1.dades import connexio


def versio_registre():
    arrel = Path(troballes.__file__).parent
    return tuple((str(p), p.stat().st_mtime_ns) for carpeta, patro in [('preguntes', '*.py'), ('consultes', '*.sql')]
                 for p in sorted((arrel / carpeta).glob(patro)))


@st.cache_data(show_spinner=False)
def totes(semestre, setmana, versio):
    importlib.invalidate_caches()
    return troballes.totes(semestre, setmana)


@st.cache_data(show_spinner=False)
def una(id_, semestre, setmana, versio):
    importlib.invalidate_caches()
    return troballes.una(id_, semestre, setmana)


@st.cache_data(show_spinner=False)
def setmanes(semestre):
    return [str(fila[0]) for fila in connexio().execute(
        'SELECT DISTINCT setmana FROM sessions WHERE sem = $semestre ORDER BY setmana',
        {'semestre': semestre}).fetchall()]
