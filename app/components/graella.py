"""Graelles i exportació HTML, sense lectura de dades."""
from collections import Counter
from dataclasses import dataclass, replace
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
    compartida: str = ''
    abans: str = ''
    setmana_diferent: bool = False
    grups_compartits: tuple[str, ...] = ()

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
            bool(not s.aula and a.aula and not s.sense_espai),
            s.compartida,
            f'Abans: {NOMS_DIES[s.data.weekday()].lower()} {fmt(s.ini)} · {s.aula or "aula no indicada"} ({s.data:%d/%m/%Y})',
            dilluns(data) != dilluns(s.data)))
    return sorted(resultat, key=lambda c: (DIES.index(c.dia), c.ini, c.id_sessio))


def celles_grup(base, proposta, setmana, titulacio, curs, grup, **kwargs):
    linia = grups(base)[titulacio][curs][grup]
    return celles(base, proposta, setmana, cohort=f'{titulacio}:{curs}', linia=linia, **kwargs)


def celles_aula(base, proposta, setmana, aula, **kwargs):
    return celles(base, proposta, setmana, aula=aula, **kwargs)


def canvis_grup(base, proposta, actuals, noves):
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
    return {'franja': franja, 'aula': aula, 'torn': torn, 'assignades': assignades}


def resum_grup(base, proposta, actuals, noves):
    canvis = canvis_grup(base, proposta, actuals, noves)
    franja, aula, torn, assignades = (canvis[k] for k in ('franja', 'aula', 'torn', 'assignades'))
    abans = len({c.aula for c in actuals if c.aula})
    despres = len({c.aula for c in noves if c.aula})
    return (f'{franja} classes canvien de dia o d’hora · {aula} canvien d’aula · '
            f'{assignades} amb aula assignada · {torn} canvien de torn · Aules diferents aquesta setmana: {abans} avui → {despres} a la proposta.')


def nom_grup(grup, tipus):
    numero = grup.rsplit('/', 1)[-1]
    nom_tipus = TIPUS.get(tipus, tipus).lower()
    return f'{"Grup" if nom_tipus == "teoria" else "Subgrup"} {numero} · {nom_tipus}'


# Un únic estat per bloc: els casos especials prevalen sobre els altres canvis.
ESTATS = {
    'totes': ('▦', 'Totes', 'var(--blau,#2a78d6)', 'var(--blau-fons,#eef5fd)', 'var(--blau-text,#205c9e)'),
    'aula-nova': ('✓', 'Aula assignada', 'var(--verd,#2f8f46)', 'var(--verd-fons,#e9f4ec)', 'var(--verd-text,#1f6b33)'),
    'canvi': ('!', 'Canvia', 'var(--p2-taronja,#e8820c)', 'var(--p2-taronja-fons,#fff1e0)', 'var(--p2-taronja-text,#9a5200)'),
    'relaxada': ('×', 'Cas especial', 'var(--vermell,#d03b3b)', 'var(--vermell-fons,#fbe9e9)', 'var(--vermell-text,#a12c2c)'),
    'igual': ('●', 'Sense canvis', 'var(--blau,#2a78d6)', 'var(--blau-fons,#eef5fd)', 'var(--blau-text,#205c9e)'),
}


def estat_cella(c):
    return ('relaxada' if c.relaxacions or c.setmana_diferent else
            'canvi' if c.canvi else 'aula-nova' if c.aula_assignada else 'igual')


def agrupa_compartides(celles):
    """Una classe física compartida ocupa un sol carril, també a la vista d'aula."""
    grups = {}
    for c in celles:
        clau = ((c.compartida, c.dia, c.ini, c.fi, c.aula) if c.compartida else ('sessio', c.id_sessio))
        grups.setdefault(clau, []).append(c)
    resultat = []
    for cs in grups.values():
        c = cs[0]
        resultat.append(replace(c,
            assignatura=' / '.join(dict.fromkeys(x.assignatura for x in cs)),
            canvi_franja=any(x.canvi_franja for x in cs),
            canvi_aula=any(x.canvi_aula for x in cs),
            aula_assignada=any(x.aula_assignada for x in cs),
            setmana_diferent=any(x.setmana_diferent for x in cs),
            relaxacions=tuple(dict.fromkeys(r for x in cs for r in x.relaxacions)),
            abans='; '.join(dict.fromkeys(x.abans for x in cs if x.abans)),
            grups_compartits=tuple(dict.fromkeys(nom_grup(x.grup, x.tipus) for x in cs))))
    return resultat


def recomptes_estat(celles):
    return Counter(estat_cella(c) for c in agrupa_compartides(celles))


def llegenda_html():
    return '<ul class="p2-llegenda">' + ''.join(
        f'<li style="color:{text}">{icona} {nom}</li>'
        for clau, (icona, nom, color, fons, text) in ESTATS.items() if clau != 'totes') + '</ul>'


# El prefix evita que l'HTML exportat alteri altres components de l'app.
CSS = """
.p2-horari{width:100%;max-width:100%;min-width:0;color:var(--tinta,#1a1a18);font:13px/1.35 system-ui}
.p2-horari .horari-scroll{overflow:auto;width:100%;max-width:100%;min-width:0;contain:inline-size;border:1px solid var(--linia,#e6e5e0);border-radius:14px;background:var(--targeta,#fff)}
.p2-horari .horari{border-collapse:collapse;table-layout:fixed;width:100%;background:var(--targeta,#fff)}
.p2-horari .horari th,.p2-horari .horari td{border:1px solid var(--linia,#e6e5e0);padding:4px;vertical-align:top}
.p2-horari .horari th{background:var(--fons,#f4f3ef);font-weight:600}
.p2-horari .horari tbody tr{height:32px}
.p2-horari .horari .hora{width:90px}
.p2-horari .horari caption{text-align:left;font-size:16px;font-weight:600;padding:10px 12px}
.p2-horari .classe{background:var(--targeta,#fff);border:1px solid var(--linia,#e6e5e0);border-left:5px solid var(--blau,#2a78d6);border-radius:8px;padding:7px;min-width:140px;height:100%;box-sizing:border-box;word-break:normal;overflow-wrap:normal;hyphens:auto}
.p2-horari .classe.aula-nova{border-left-color:var(--verd,#2f8f46)}
.p2-horari .classe.canvi{border-left-color:var(--p2-taronja,#e8820c)}
.p2-horari .classe.relaxada{border-left-color:var(--vermell,#d03b3b)}
.p2-horari .classe small{display:block;margin-top:3px}
.p2-horari .classe .estat{display:inline-flex;align-items:center;gap:4px;white-space:normal;font-size:12px;font-weight:600;border-radius:999px;padding:2px 7px;margin-top:5px}
.p2-horari .classe.aula-nova .estat{background:var(--verd-fons,#e9f4ec);color:var(--verd-text,#1f6b33)}
.p2-horari .classe.canvi .estat{background:var(--p2-taronja-fons,#fff1e0);color:var(--p2-taronja-text,#9a5200)}
.p2-horari .classe.relaxada .estat{background:var(--vermell-fons,#fbe9e9);color:var(--vermell-text,#a12c2c)}
.p2-horari .classe .estat svg{width:14px;height:14px;flex:none}
.p2-horari .classe.apagada{opacity:.25}
.p2-horari .classe summary:focus-visible{outline:3px solid var(--blau,#2a78d6);outline-offset:2px}
.p2-horari .classe summary{cursor:pointer;list-style:none}
.p2-horari .classe summary::-webkit-details-marker{display:none}
.p2-horari .classe .detall{padding-top:6px;border-top:1px solid var(--linia,#e6e5e0);margin-top:6px}
"""


def taula_html(celles, titol='Horari setmanal', *, originals=False, filtre='totes', estils=True):
    """Una cel·la amb rowspan per sessió; carrils paral·lels si se solapen.

    Les files parcials respecten els minuts exactes: dues classes consecutives
    no creen carrils perquè comparteixin una mitja hora visual.
    """
    from components.vistes import estat as pastilla_estat

    celles = agrupa_compartides(celles)
    # Conservem el dia sencer si hi ha matí i tarda; un únic torn comença
    # a la primera mitja hora ocupada, mantenint sempre el final a les 21 h.
    torns = {c.ini < 870 for c in celles}
    inici_dia = max(510, min((c.ini for c in celles), default=510) // 30 * 30) if len(torns) == 1 else 510
    franges = tuple(range(inici_dia, 1260, 30))
    # Afegim límits exactes a les mitges hores, sense alterar-ne els rètols.
    limits = sorted({*franges, 1260} | {
        max(inici_dia, min(1260, minut)) for c in celles for minut in (c.ini, c.fi)})
    files = {minut: i for i, minut in enumerate(limits)}
    carrils = {}
    for dia in DIES:
        ocupats = []
        entrades = []
        for c in sorted((c for c in celles if c.dia == dia), key=lambda c: (c.ini, c.fi, c.id_sessio)):
            inici = files[max(inici_dia, min(1260, c.ini))]
            final = files[max(inici_dia, min(1260, c.fi))]
            if final <= inici:
                continue
            carril = next((i for i, fi in enumerate(ocupats) if fi <= inici), len(ocupats))
            if carril == len(ocupats):
                ocupats.append(final)
            else:
                ocupats[carril] = final
            entrades.append((inici, final, carril, c))
        carrils[dia] = (max(1, len(ocupats)), entrades)
    # Una classe sense altres subgrups simultanis aprofita tot el dia.
    # Reservem cada espai que ocupa, inclosos els colspans, per no emetre
    # cel·les buides que desplacin les columnes de les files següents.
    cobertes = {}
    inicis = {}
    for dia, (n, entrades) in carrils.items():
        for primera, final, carril, c in entrades:
            ample = 1
            while carril + ample < n:
                seguent = carril + ample
                if any(i < final and primera < f and k == seguent for i, f, k, _ in entrades):
                    break
                ample += 1
            inicis[dia, primera, carril] = (final, ample, c)
            for fila in range(primera, final):
                for columna in range(carril, carril + ample):
                    cobertes[dia, fila, columna] = True
    # Cada carril disposa de 150 px: 140 de bloc i el marge de la cel·la.
    total = sum(n for n, _ in carrils.values())
    amplada = 90 + 150 * total
    html = (f'<style>{CSS}</style>' if estils else '') + f'<div class="p2-horari"><div class="horari-scroll" tabindex="0" role="region" aria-label="{escape(titol, quote=True)}"><table class="horari"><caption>{escape(titol)}</caption><colgroup><col class="hora">'
    for dia in DIES:
        n, _ = carrils[dia]
        html += ''.join('<col style="width:150px">' for _ in range(n))
    html = html.replace('<table class="horari">', f'<table class="horari" style="min-width:{amplada}px">')
    html += '</colgroup><thead><tr><th scope="col">Hora</th>'
    html += ''.join(f'<th scope="col" colspan="{carrils[d][0]}">{nom}</th>' for d, nom in zip(DIES, NOMS_DIES)) + '</tr></thead><tbody>'
    for fila, inici in enumerate(limits[:-1]):
        alt = (limits[fila + 1] - inici) / 30 * 32
        html += f'<tr style="height:{alt:g}px">'
        if inici in franges:
            html += f'<th scope="row" rowspan="{files[min(inici+30, 1260)]-fila}">{fmt(inici)}–{fmt(inici+30)}</th>'
        for dia in DIES:
            n, entrades = carrils[dia]
            carril = 0
            while carril < n:
                entrada = inicis.get((dia, fila, carril))
                if entrada is None:
                    if (dia, fila, carril) in cobertes:
                        carril += 1
                        continue
                    ample_buit = 1
                    while (carril + ample_buit < n
                           and (dia, fila, carril + ample_buit) not in cobertes):
                        ample_buit += 1
                    html += f'<td colspan="{ample_buit}"></td>'
                    carril += ample_buit
                    continue
                final, ample, c = entrada
                estat = estat_cella(c)
                marques = (' ' + estat if estat != 'igual' else '')
                if filtre != 'totes' and filtre != estat:
                    marques += ' apagada'
                ubicacio = c.aula or ('Aula no indicada a les dades' if originals else 'Pendent d’assignar aula')
                grup = ' / '.join(c.grups_compartits) or nom_grup(c.grup, c.tipus)
                detall = f'{fmt(c.ini)}–{fmt(c.fi)} · {grup} · {ubicacio}'
                avis = ' '.join(c.relaxacions)
                if c.setmana_diferent:
                    avis = 'Setmana diferent. ' + avis
                if c.canvi or c.aula_assignada:
                    abans = c.abans or ('Aula assignada.' if c.aula_assignada else 'Canvi de dia, hora o aula.')
                    avis = abans + (' · ' + avis if avis else '')
                icona, nom, *_ = ESTATS[estat]
                color_estat = {'aula-nova': 'verd', 'canvi': 'ambre', 'relaxada': 'vermell'}.get(estat)
                pastilla = pastilla_estat({'estat': color_estat, 'etiqueta': nom}) if color_estat else ''
                compartida = '<small>Classe compartida</small>' if c.compartida else ''
                contingut = f'<b>{escape(c.assignatura)}</b><small>{escape(detall)}</small>{compartida}{pastilla}'
                # Details ofereix el mateix detall amb clic, teclat o en passar el ratolí.
                classe = (f'<details class="classe{marques}" data-estat="{estat}" title="{escape(avis, quote=True)}">'
                    f'<summary>{contingut}</summary><small class="detall">{escape(avis or "Es manté la classe de les dades originals.")}</small></details>')
                html += f'<td rowspan="{final-fila}" colspan="{ample}">{classe}</td>'
                carril += ample
        html += '</tr>'
    return html + '</tbody></table></div></div>'


def exporta_aula_html(base, proposta, setmana, aula, **kwargs):
    titol = f'Aula {aula} · setmana del {dilluns(setmana):%d/%m/%Y}'
    contingut = taula_html(celles_aula(base, proposta, setmana, aula, **kwargs), titol)
    return '<!doctype html><html lang="ca"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>' + escape(titol) + '</title><body><h1>' + escape(titol) + '</h1>' + llegenda_html() + contingut + '</body></html>'
