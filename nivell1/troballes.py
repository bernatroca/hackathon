"""Registre de troballes: el contracte entre les preguntes (nivell1/preguntes/) i l'app (app/).

Cada pregunta és un mòdul de nivell1/preguntes/ amb:
    ID: str                                         # 'ocupacio', 'hi-cap-mati'…
    ORDRE: int                                      # número de la pregunta a l'especificació (1-11)
    def calcula(semestre: int, setmana: str | None) -> Troballa
    def comprova() -> list[tuple[str, object, object]]   # opcional: (què, esperat, obtingut)
El registre els troba sols: afegir una pregunta no toca cap fitxer compartit.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from types import ModuleType

import pandas as pd

from nivell1 import preguntes

PORTADA: list[str] = ['hi-cap-mati', 'fora-torn', 'hores-aula', 'aforament', 'ocupacio']


@dataclass
class Troballa:
    id: str
    titol: str
    xifra: str
    frase: str
    metode: str
    sql: str
    taula: pd.DataFrame
    exemples: list[str] = field(default_factory=list)
    grafic: str = 'taula'          # 'heatmap' | 'barres' | 'linia' | 'taula'
    extra: dict = field(default_factory=dict)   # dades addicionals per al gràfic (p. ex. línia de 19 aules)


def moduls() -> list[ModuleType]:
    out = []
    for m in pkgutil.iter_modules(preguntes.__path__):
        if not m.name.startswith('_'):
            out.append(importlib.import_module(f'nivell1.preguntes.{m.name}'))
    return sorted(out, key=lambda m: getattr(m, 'ORDRE', 99))


def totes(semestre: int = 2, setmana: str | None = None) -> list[Troballa]:
    return [m.calcula(semestre, setmana) for m in moduls()]


def una(id: str, semestre: int = 2, setmana: str | None = None) -> Troballa:
    for m in moduls():
        if m.ID == id:
            return m.calcula(semestre, setmana)
    raise KeyError(id)
