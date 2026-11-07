"""Graelles pures: cap dependència de Streamlit ni lectura de dades."""
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from statistics import median

from nivell2.base import fmt, hm

DIES = ('L', 'M', 'X', 'J', 'V')
NOMS_DIES = ('Dilluns', 'Dimarts', 'Dimecres', 'Dijous', 'Divendres')
TIPUS = {'TE': 'Teoria', 'PAUL': 'Problemes', 'SEM': 'Seminari', 'PLAB': 'Laboratori'}
FRANGES = tuple(range(510, 1260, 30))


def dilluns(data):
    return data - timedelta(days=data.weekday())


def setmana_tipica(base):
    recomptes = Counter(dilluns(s.data) for s in base.sessions.values())
    if not recomptes:
        raise ValueError('No hi ha sessions al segon semestre.')
    mig = median(recomptes.values())
    return min(recomptes, key=lambda d: (abs(recomptes[d] - mig), d))


def grups(base):
    """Titulació → curs → grup de teoria, amb la línia oficial del verificador."""
    resultat = {}
    for s in base.sessions.values():
        if s.tipus == 'TE':
            for cohort in s.cohorts:
                titulacio, curs = cohort.rsplit(':', 1)
                resultat.setdefault(titulacio, {}).setdefault(curs, {})[s.num_grup] = s.linia
    return resultat


@dataclass(frozen=True)
class Cella:
    id_sessio: str
    dia: str
    ini: int
    fi: int
    aula: str
    assignatura: str
    tipus: str
    grup: str
    canvi_franja: bool
    canvi_aula: bool
    relaxacions: tuple[str, ...] = ()

    @property
    def canvi(self):
        return self.canvi_franja or self.canvi_aula


def celles(base, proposta, setmana, *, cohort=None, linia=None, aula=None,
           noms=None, relaxacions=None):
    """Sessions de la setmana real (dilluns), amb canvis respecte de la partida.

    Una data explícita de recuperació preval sobre la setmana original.
    Les propostes incompletes es rebutgen: no s'omplen en silenci.
    """
    setmana = dilluns(setmana)
    falten = base.sessions.keys() - proposta.files.keys()
    desconegudes = proposta.files.keys() - base.sessions.keys()
    if falten or desconegudes:
        raise ValueError(f'La proposta té {len(falten)} sessions absents i {len(desconegudes)} desconegudes.')
    resultat = []
    for sid, s in base.sessions.items():
        a = proposta.files[sid]
        if a.dia not in DIES:
            raise ValueError(f'Dia incorrecte a la sessió {sid}.')
        data = date.fromisoformat(a.data) if a.data else dilluns(s.data) + timedelta(days=DIES.index(a.dia))
        if dilluns(data) != setmana:
            continue
        if cohort is not None and (cohort not in s.cohorts or s.linia != linia or s.tipus not in ('TE', 'PAUL', 'SEM')):
            continue
        if aula is not None and a.aula != aula:
            continue
        inici = hm(a.h_ini)
        if not 0 <= inici < 1440:
            raise ValueError(f'Hora incorrecta a la sessió {sid}.')
        resultat.append(Cella(sid, a.dia, inici, inici + s.durada, a.aula,
            (noms or {}).get(s.codi, s.codi), TIPUS.get(s.tipus, s.tipus), s.grup,
            data != s.data or inici != s.ini, a.aula != s.aula,
            tuple((relaxacions or {}).get(sid, ()))))
    return sorted(resultat, key=lambda c: (DIES.index(c.dia), c.ini, c.id_sessio))


def celles_grup(base, proposta, setmana, titulacio, curs, grup, **kwargs):
    linia = grups(base)[titulacio][curs][grup]
    return celles(base, proposta, setmana, cohort=f'{titulacio}:{curs}', linia=linia, **kwargs)


def celles_aula(base, proposta, setmana, aula, **kwargs):
    return celles(base, proposta, setmana, aula=aula, **kwargs)


CSS = '''.horari-scroll{overflow:auto}.horari{border-collapse:collapse;width:100%;min-width:580px;font:12px/1.35 system-ui;color:#0b0b0b;background:white}.horari th,.horari td{border:1px solid #e6e5e0;padding:5px;vertical-align:top;width:18%}.horari th{background:#f4f3ef}.horari th:first-child{width:10%}.classe{background:#cde2fb;border-left:3px solid #2a78d6;border-radius:4px;padding:5px;margin:2px 0;overflow-wrap:anywhere}.classe.canvi{background:#fff5dc;border-color:#b67b00}.classe.relaxada{border:2px dashed #a12c2c}.classe small{display:block}.horari caption{text-align:left;font-size:16px;font-weight:600;padding:8px}'''


def taula_html(celles, titol='Horari setmanal'):
    """Cada sessió ocupa totes les mitges hores que intersecta; conserva l'hora exacta."""
    html = f'<style>{CSS}</style><div class="horari-scroll"><table class="horari"><caption>{escape(titol)}</caption><thead><tr><th scope="col">Hora</th>'
    html += ''.join(f'<th scope="col">{d}</th>' for d in NOMS_DIES) + '</tr></thead><tbody>'
    for inici in FRANGES:
        html += f'<tr><th scope="row">{fmt(inici)}–{fmt(inici+30)}</th>'
        for dia in DIES:
            html += '<td>'
            for c in celles:
                if c.dia != dia or c.ini >= inici + 30 or c.fi <= inici:
                    continue
                marques = (' canvi' if c.canvi else '') + (' relaxada' if c.relaxacions else '')
                detall = f'{fmt(c.ini)}–{fmt(c.fi)} · {c.tipus} · {c.grup} · {c.aula or "Sense aula assignada"}'
                avis = ('Canvi de franja. ' if c.canvi_franja else '') + ('Canvi d’aula. ' if c.canvi_aula else '')
                avis += ' '.join(c.relaxacions)
                html += f'<div class="classe{marques}"><b>{escape(c.assignatura)}</b><small>{escape(detall)}</small><small>{escape(avis)}</small></div>'
            html += '</td>'
        html += '</tr>'
    return html + '</tbody></table></div>'


def exporta_aula_html(base, proposta, setmana, aula, **kwargs):
    titol = f'Aula {aula} · setmana del {dilluns(setmana):%d/%m/%Y}'
    contingut = taula_html(celles_aula(base, proposta, setmana, aula, **kwargs), titol)
    return '<!doctype html><html lang="ca"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>' + escape(titol) + '</title><body><h1>' + escape(titol) + '</h1><p>Groc: canvi de franja o aula. Vora discontínua: excepció declarada, amb el motiu.</p>' + contingut + '</body></html>'
