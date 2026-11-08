"""Connexió DuckDB amb les dades del repte i les vistes comunes a totes les preguntes.

Vistes:
- sessions: paquet/sessions.csv amb tipus correctes i columnes derivades (sem, ini_min, fi_min, torn_actual,
  unitat, demanda_aulari).
- aules: paquet/aules.csv (capacitat entera, ordinaria booleana).
- calendari: paquet/calendari.csv.
- grau_nou: escenaris/grau-nou-40/sessions_extra.csv, amb les mateixes columnes derivades que sessions.
- blocs: els 25 blocs de 30 minuts de 8.30 a 21.00 (bloc, ini_min, fi_min, etiqueta, franja).
- sessio_blocs: una fila per sessió i bloc que ocupa (id_sessio, bloc).
"""
from __future__ import annotations

import os
from contextlib import closing
from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd

REPTE_DIR = Path(os.environ.get('REPTE_DIR') or Path(__file__).resolve().parents[1] / 'repte' / 'repte-horaris-escola')
PAQUET = REPTE_DIR / 'paquet'
CONSULTES = Path(__file__).parent / 'consultes'

MATI_INI, MATI_FI, TARDA_FI = 8 * 60 + 30, 14 * 60 + 30, 21 * 60
AULES_DISPONIBLES = 19   # 21 aules docents menys les 2 de reserva (regla 8)


def _csv(path: Path) -> str:
    return f"read_csv('{path}', header=true, all_varchar=true)"


def _sessions_sql(origen: str) -> str:
    return f"""
    SELECT * REPLACE (
            CAST(data AS DATE) AS data,
            CAST(durada_min AS INTEGER) AS durada_min,
            COALESCE(TRY_CAST(alumnes AS INTEGER), 0) AS alumnes,
            TRY_CAST(capacitat_grup AS INTEGER) AS capacitat_grup,
            NULLIF(aula_partida, '') AS aula_partida,
            NULLIF(id_compartida, '') AS id_compartida),
        CASE WHEN month(CAST(data AS DATE)) >= 9 OR month(CAST(data AS DATE)) = 1 THEN 1 ELSE 2 END AS sem,
        CAST(split_part(h_ini, ':', 1) AS INTEGER) * 60 + CAST(split_part(h_ini, ':', 2) AS INTEGER) AS ini_min,
        CAST(split_part(h_ini, ':', 1) AS INTEGER) * 60 + CAST(split_part(h_ini, ':', 2) AS INTEGER)
            + CAST(durada_min AS INTEGER) AS fi_min,
        CASE WHEN CAST(split_part(h_ini, ':', 1) AS INTEGER) * 60 + CAST(split_part(h_ini, ':', 2) AS INTEGER)
            < {MATI_FI} THEN 'mati' ELSE 'tarda' END AS torn_actual,
        COALESCE(NULLIF(id_compartida, ''), id_sessio) AS unitat,
        COALESCE(sense_espai_txt, '') = '1' AS sense_espai,
        tipus <> 'PLAB' AND COALESCE(sense_espai_txt, '') <> '1' AS demanda_aulari
    FROM (SELECT *, {'sense_espai' if origen == 'sessions' else "''"} AS sense_espai_txt FROM {origen}_brut)
    """


@lru_cache(maxsize=1)
def connexio() -> duckdb.DuckDBPyConnection:
    """Connexió en memòria amb totes les vistes. Es crea una sola vegada per procés."""
    con = duckdb.connect()
    con.execute(f"CREATE TABLE sessions_brut AS SELECT * FROM {_csv(PAQUET / 'sessions.csv')}")
    con.execute(f"CREATE TABLE grau_nou_brut AS SELECT * FROM "
                f"{_csv(PAQUET / 'escenaris' / 'grau-nou-40' / 'sessions_extra.csv')}")
    con.execute("CREATE TABLE sessions AS " + _sessions_sql('sessions').replace(
        'SELECT * REPLACE', 'SELECT * EXCLUDE (sense_espai_txt, sense_espai) REPLACE', 1))
    con.execute("CREATE TABLE grau_nou AS " + _sessions_sql('grau_nou').replace(
        'SELECT * REPLACE', 'SELECT * EXCLUDE (sense_espai_txt) REPLACE', 1))
    con.execute(f"""CREATE TABLE aules AS SELECT * REPLACE (CAST(capacitat AS INTEGER) AS capacitat,
                    ordinaria = '1' AS ordinaria) FROM {_csv(PAQUET / 'aules.csv')}""")
    con.execute(f"CREATE TABLE calendari AS SELECT * REPLACE (CAST(data AS DATE) AS data) "
                f"FROM {_csv(PAQUET / 'calendari.csv')}")
    con.execute(f"""CREATE TABLE blocs AS
        SELECT i AS bloc, {MATI_INI} + 30 * i AS ini_min, {MATI_INI} + 30 * i + 30 AS fi_min,
               lpad(CAST(({MATI_INI} + 30 * i) // 60 AS VARCHAR), 2, '0') || ':' ||
               lpad(CAST(({MATI_INI} + 30 * i) % 60 AS VARCHAR), 2, '0') AS etiqueta,
               CASE WHEN {MATI_INI} + 30 * i < {MATI_FI} THEN 'mati' ELSE 'tarda' END AS franja
        FROM range(0, ({TARDA_FI} - {MATI_INI}) // 30) t(i)""")
    con.execute("""CREATE VIEW sessio_blocs AS
        SELECT s.id_sessio, b.bloc FROM sessions s JOIN blocs b
        ON b.ini_min < s.fi_min AND b.fi_min > s.ini_min""")
    return con


def sql(nom: str) -> str:
    """Text de nivell1/consultes/<nom>.sql."""
    return (CONSULTES / f'{nom}.sql').read_text(encoding='utf-8')


def consulta(nom: str, **params) -> tuple[pd.DataFrame, str]:
    """Executa nivell1/consultes/<nom>.sql amb paràmetres $nom i torna (taula, text SQL)."""
    text = sql(nom)
    with closing(connexio().cursor()) as cur:
        df = cur.execute(text, params or None).df()
    return df, text


def setmana_tipica(semestre: int) -> str:
    """Mediana de les setmanes amb almenys 200 classes; desempat per la primera.

    Si tot el semestre és més petit, conservem les setmanes disponibles.
    """
    with closing(connexio().cursor()) as cur:
        return cur.execute("""
        WITH recomptes AS (SELECT setmana, count(*) AS c FROM sessions WHERE sem = $s GROUP BY setmana),
        n AS (SELECT * FROM recomptes WHERE c >= 200 OR NOT EXISTS (
            SELECT 1 FROM recomptes WHERE c >= 200))
        SELECT setmana FROM n ORDER BY abs(c - (SELECT median(c) FROM n)), setmana LIMIT 1""",
                              {'s': semestre}).fetchone()[0]


def setmana_pitjor(semestre: int) -> str:
    """Setmana ISO amb el pic més alt de classes simultànies que demanen aulari (compartides un cop, per bloc)."""
    with closing(connexio().cursor()) as cur:
        return cur.execute("""
        SELECT s.setmana FROM sessions s JOIN sessio_blocs sb USING (id_sessio)
        WHERE s.sem = $s AND s.demanda_aulari
        GROUP BY s.setmana, s.data, sb.bloc
        ORDER BY count(DISTINCT s.unitat) DESC, s.setmana LIMIT 1""", {'s': semestre}).fetchone()[0]
