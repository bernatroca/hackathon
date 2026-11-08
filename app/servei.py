"""Accés al contracte de troballes i a la llista de setmanes."""
import importlib
import hashlib
import json
from contextlib import closing
from pathlib import Path
import streamlit as st
from nivell1 import troballes
from nivell1.dades import connexio, consulta, AULES_DISPONIBLES
from nivell2.base import RESULTATS_PRINCIPAL as RESULTATS_PART2


def actualitza_dades():
    """Torna a llegir tant les taules de DuckDB com els càlculs de Streamlit."""
    connexio.cache_clear()
    st.cache_data.clear()


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
def _una(id_, semestre, setmana, versio):
    importlib.invalidate_caches()
    return troballes.una(id_, semestre, setmana)


def una(id_, semestre, setmana, versio):
    t = _una(id_, semestre, setmana, versio)
    # «Hi cap el matí?» es dona per validat quan la proposta de la part 2 (5.2) passa el verificador oficial.
    if t is not None and id_ != 'marge-grau-nou' and semestre == 2:
        t.extra = dict(t.extra or {}, validat_part2=validacio_part2('5.2'))
    # El grau nou es dona per validat amb el 5.4 (proposta amb el grau nou que passa el verificador).
    if t is not None and id_ == 'marge-grau-nou' and semestre == 2:
        t.extra = dict(t.extra or {}, validat_part2=validacio_part2('5.4'))
    return t


# Buidar la memòria cau d'una() buida la de _una().
una.clear = _una.clear


@st.cache_data(ttl=None, show_spinner=False)
def classes_detall(id_, semestre, versio):
    """Carrega la llista només quan s'obre el detall, mai a la portada."""
    modul = importlib.import_module('nivell1.preguntes.' + {
        'hores-aula': 'hores_aula', 'fora-torn': 'fora_torn'}[id_])
    return modul.classes(semestre)


@st.cache_data(ttl=None, show_spinner=False)
def _classes_sense_aula_proposta(proposta, sha):
    """Mateix criteri de demanda d'aula que al nivell 1; només torna el recompte."""
    df, _ = consulta('hores_aula_proposta', semestre=2, proposta=proposta)
    return int(df.pendents.iloc[0])


VEREDICTES_VALIDS = ('VALIDA', 'VALIDA AMB RELAXACIONS DECLARADES')


def validacio_part2(apartat):
    """Només el veredicte i el recompte d'incompliments que compten; cap fila de dades."""
    carpeta = RESULTATS_PART2 / apartat
    try:
        informe = json.loads((carpeta / 'informe.json').read_text(encoding='utf-8'))
        veredicte = informe['veredicte']
        sha = hashlib.sha256((carpeta / 'proposta.csv').read_bytes()).hexdigest()
        if informe.get('context', {}).get('proposta_sha256') != sha:
            return None
        resum = json.loads((carpeta / 'resum.json').read_text(encoding='utf-8'))
    except (OSError, KeyError, ValueError):
        return None
    incompliments = int(resum.get('incompliments_no_declarats', 0) or 0)
    resultat = dict(veredicte=veredicte, incompliments=incompliments,
                    valida=veredicte in VEREDICTES_VALIDS and incompliments == 0)
    # Només agregats de l'informe comprovat; mai files ni identificadors.
    resultat['restriccions'] = {
        clau: {camp: int(v.get(camp, 0) or 0) for camp in ('compten', 'declarades', 'heretades')}
        for clau, v in informe.get('restriccions', {}).items()}
    resultat['objectius'] = {k: v for k, v in informe.get('objectius', {}).items()
                            if isinstance(v, (int, float))}
    if apartat == '5.2' and resultat['valida']:
        resultat['classes_sense_aula'] = _classes_sense_aula_proposta(str(carpeta / 'proposta.csv'), sha)
    # Només recomptes: resposta del 5.4 (1 hi cap, 2 no sense tocar el 5.2, 3 no trobada, 4 demostrat que no).
    for clau in ('resposta', 'sessions_grau_nou', 'sessions_grau_nou_collocades', 'sessions_grau_nou_fora_franja', 'sessions_52_mogudes'):
        if clau in resum:
            resultat[clau] = int(resum[clau])
    return resultat


@st.cache_data(ttl=None, show_spinner=False)
def setmanes(semestre):
    """Setmana ISO, dilluns i recompte; exclou les setmanes residuals."""
    with closing(connexio().cursor()) as cur:
        return cur.execute("""
        SELECT setmana, CAST(date_trunc('week', min(data)) AS DATE), count(*)
        FROM sessions WHERE sem = $semestre
        GROUP BY setmana HAVING count(*) >= 200 ORDER BY setmana
        """, {'semestre': semestre}).fetchall()

# Regla 8: es reserven dues de les aules docents disponibles a l'inventari.
AULES_RESERVA = 2
# Places de l'escenari del repte anomenat grau-nou-40.
PLACES_GRAU_NOU = 40


@st.cache_data(ttl=None, show_spinner=False)
def inventari():
    """Única lectura d'inventari autoritzada; no calcula ocupació."""
    with closing(connexio().cursor()) as cur:
        return cur.execute('SELECT aula, edifici, tipus, capacitat FROM aules').df()
