"""Graelles pures: cap dependència de Streamlit ni lectura de dades."""
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from statistics import median

from nivell2.base import fmt, hm
from horaris.model import a_traslladar

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

    aula_assignada: bool = False

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
            data != s.data or inici != s.ini,
            bool(s.aula and not a_traslladar(s.aula) and not s.sense_espai and a.aula != s.aula),
            tuple((relaxacions or {}).get(sid, ())),
            bool(not s.aula and a.aula and not s.sense_espai)))
    return sorted(resultat, key=lambda c: (DIES.index(c.dia), c.ini, c.id_sessio))


def celles_grup(base, proposta, setmana, titulacio, curs, grup, **kwargs):
    linia = grups(base)[titulacio][curs][grup]
    return celles(base, proposta, setmana, cohort=f'{titulacio}:{curs}', linia=linia, **kwargs)


def celles_aula(base, proposta, setmana, aula, **kwargs):
    return celles(base, proposta, setmana, aula=aula, **kwargs)


def resum_grup(base, proposta, actuals, noves):
    """Compara les sessions presents en qualsevol de les dues setmanes visibles."""
    ids = {c.id_sessio for c in actuals + noves}
    franja = aula = torn = assignades = 0
    for sid in ids:
        s, a = base.sessions[sid], proposta.files[sid]
        data = date.fromisoformat(a.data) if a.data else dilluns(s.data) + timedelta(days=DIES.index(a.dia))
        inici = hm(a.h_ini)
        franja += data != s.data or inici != s.ini
        aula += bool(s.aula and not a_traslladar(s.aula) and not s.sense_espai and a.aula != s.aula)
        assignades += bool(not s.aula and a.aula and not s.sense_espai)
        torn += (s.ini < 870) != (inici < 870)
    abans = len({c.aula for c in actuals if c.aula})
    despres = len({c.aula for c in noves if c.aula})
    return (f'{franja} classes canvien de dia o d’hora · {aula} canvien d’aula · '
            f'{assignades} amb aula assignada · {torn} canvien de torn · Aules diferents aquesta setmana: {abans} avui → {despres} a la proposta.')


CSS = ''' .horari-scroll{overflow:auto;min-width:0}.horari{border-collapse:collapse;table-layout:fixed;width:100%;min-width:580px;font:12px/1.35 system-ui;color:var(--tinta,#0b0b0b);background:white}.horari th,.horari td{border:1px solid #e6e5e0;padding:3px;vertical-align:top}.horari th{background:#f4f3ef}.horari tbody tr{height:32px}.horari .hora{width:78px}.classe{background:#cde2fb;border-left:3px solid #2a78d6;border-radius:4px;padding:5px;overflow-wrap:anywhere;height:100%;box-sizing:border-box}.classe.canvi{background:#fff5dc;border-color:#b67b00}.classe.relaxada{border:2px dashed #a12c2c}.classe small{display:block}.horari caption{text-align:left;font-size:16px;font-weight:600;padding:8px}.comparacio-horaris{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;container-type:normal}@container contingut (max-width:1180px){.comparacio-horaris{grid-template-columns:minmax(0,1fr)}}@media(max-width:900px){.comparacio-horaris{grid-template-columns:minmax(0,1fr)}}'''


def taula_html(celles, titol='Horari setmanal'):
    """Una cel·la amb rowspan per sessió; carrils paral·lels si se solapen.

    Arrodonim només l'espai visual a mitges hores. El text manté l'hora exacta.
    """
    carrils = {}
    for dia in DIES:
        ocupats = []
        entrades = []
        for c in sorted((c for c in celles if c.dia == dia), key=lambda c: (c.ini, c.fi, c.id_sessio)):
            inici = max(0, (c.ini - 510) // 30)
            final = min(len(FRANGES), (c.fi - 510 + 29) // 30)
            if final <= inici:
                continue
            carril = next((i for i, fi in enumerate(ocupats) if fi <= inici), len(ocupats))
            if carril == len(ocupats):
                ocupats.append(final)
            else:
                ocupats[carril] = final
            entrades.append((inici, final, carril, c))
        carrils[dia] = (max(1, len(ocupats)), entrades)
    html = f'<style>{CSS}</style><div class="horari-scroll"><table class="horari"><caption>{escape(titol)}</caption><colgroup><col class="hora">'
    for dia in DIES:
        n, _ = carrils[dia]
        html += ''.join(f'<col style="width:{18/n}%">' for _ in range(n))
    html += '</colgroup><thead><tr><th scope="col">Hora</th>'
    html += ''.join(f'<th scope="col" colspan="{carrils[d][0]}">{nom}</th>' for d, nom in zip(DIES, NOMS_DIES)) + '</tr></thead><tbody>'
    for fila, inici in enumerate(FRANGES):
        html += f'<tr><th scope="row">{fmt(inici)}–{fmt(inici+30)}</th>'
        for dia in DIES:
            n, entrades = carrils[dia]
            for carril in range(n):
                entrada = next((e for e in entrades if e[2] == carril and e[0] <= fila < e[1]), None)
                if entrada is None:
                    html += '<td></td>'
                    continue
                primera, final, _, c = entrada
                if primera != fila:
                    continue
                marques = (' canvi' if c.canvi else '') + (' relaxada' if c.relaxacions else '')
                detall = f'{fmt(c.ini)}–{fmt(c.fi)} · {c.tipus} · {c.grup} · {c.aula or "Sense aula assignada"}'
                avis = ('Canvi de franja. ' if c.canvi_franja else '') + ('Canvi d’aula. ' if c.canvi_aula else '')
                avis += 'Aula assignada. ' if c.aula_assignada else ''
                avis += ' '.join(c.relaxacions)
                html += f'<td rowspan="{final-primera}"><div class="classe{marques}" title="{escape(avis, quote=True)}"><b>{escape(c.assignatura)}</b><small>{escape(detall)}</small><small>{escape(avis)}</small></div></td>'
        html += '</tr>'
    return html + '</tbody></table></div>'


def exporta_aula_html(base, proposta, setmana, aula, **kwargs):
    titol = f'Aula {aula} · setmana del {dilluns(setmana):%d/%m/%Y}'
    contingut = taula_html(celles_aula(base, proposta, setmana, aula, **kwargs), titol)
    return '<!doctype html><html lang="ca"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>' + escape(titol) + '</title><body><h1>' + escape(titol) + '</h1><p>Groc: canvi de franja o aula. Vora discontínua: excepció declarada, amb el motiu.</p>' + contingut + '</body></html>'
