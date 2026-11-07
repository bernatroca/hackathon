"""Graelles i exportació HTML, sense lectura de dades."""
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, timedelta
from html import escape
from statistics import median

from nivell2.base import fmt, hm
from nivell2.comprova_persones import parelles_dobles
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
    ubicacio_compartida: str = ''

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
    # Resolve hosts before the visible cohort/room filter; another group's
    # class may be outside this view. Use proposed dates and rooms for display.
    hosts, _ = parelles_dobles(base)
    positions = {}
    for sid, s in base.sessions.items():
        a = proposta.files[sid]
        if a.dia not in DIES:
            raise ValueError(f'Dia incorrecte a la sessió {sid}.')
        d = date.fromisoformat(a.data) if a.data else dilluns(s.data) + timedelta(days=DIES.index(a.dia))
        positions[sid] = d, hm(a.h_ini)
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
        shared_location = ''
        if s.sense_espai:
            candidates = [base.sessions[h] for h in hosts.get(sid, ())
                          if positions[h] == positions[sid] and proposta.files[h].aula]
            if candidates:
                host = min(candidates, key=lambda h: (h.grup != s.grup, h.id))
                shared_location = f'Amb el grup {host.num_grup} · Aula {proposta.files[host.id].aula}'
            else:
                shared_location = 'Classe compartida amb un altre grup'
        resultat.append(Cella(sid, a.dia, inici, inici + s.durada, a.aula,
            (noms or {}).get(s.codi, s.codi), TIPUS.get(s.tipus, s.tipus), s.grup,
            data != s.data or inici != s.ini,
            bool(s.aula and not a_traslladar(s.aula) and not s.sense_espai and a.aula != s.aula),
            tuple((relaxacions or {}).get(sid, ())),
            bool(not s.aula and a.aula and not s.sense_espai),
            s.compartida,
            f'Abans: {NOMS_DIES[s.data.weekday()].lower()} {fmt(s.ini)} · {s.aula or "aula no indicada"} ({s.data:%d/%m/%Y})',
            dilluns(data) != dilluns(s.data),
            ubicacio_compartida=shared_location))
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
    'totes': ('Totes', '#2a78d6', '#eef4fc', '#1d5fae'),
    'igual': ('Sense canvis', '#2a78d6', '#eef4fc', '#1d5fae'),
    'aula-nova': ('Aula assignada', '#2f8f46', '#edf6ef', '#1f6b33'),
    'canvi': ('Canvia', '#e8820c', '#fff4e5', '#8f4c00'),
    'relaxada': ('Cas especial', '#d03b3b', '#fdeeee', '#a12c2c'),
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
        f'<li><i aria-hidden="true" style="background:{color}"></i>{nom}</li>'
        for clau, (nom, color, _, _) in ESTATS.items() if clau != 'totes') + '</ul>'


# Estils compartits entre els botons Streamlit i la prova HTML inventada.
CSS_FILTRES = """
:is(.st-key-p2-filtres,.p2-filtres){display:flex;flex-wrap:wrap;gap:8px;min-width:0;}
.st-key-p2-filtres [data-testid="stHorizontalBlock"]{gap:8px;flex-wrap:wrap;}
.st-key-p2-filtres [data-testid="stColumn"]{width:auto!important;flex:0 0 auto!important;min-width:0!important;}
:is(.st-key-p2-filtres,.p2-filtres) button{display:inline-flex;align-items:center;gap:8px;background:#fff;color:#1a1a18;border:1px solid #e6e5e0;border-radius:999px;padding:5px 10px;min-height:32px;font:14px/1.35 system-ui;box-shadow:none;}
:is(.st-key-p2-filtres,.p2-filtres) button p{font-size:14px;white-space:nowrap;font-weight:inherit;}
:is(.st-key-p2-filtres,.p2-filtres) button::before{content:"";display:block;flex:none;width:10px;height:10px;border-radius:3px;background:var(--p2-filtre-color);}
:is(.st-key-p2-filtres,.p2-filtres) button:is([kind="primary"],[aria-pressed="true"]){background:#fff;color:#1a1a18;border-color:#1a1a18;font-weight:700;outline:none;}
:is(.st-key-p2-filtres,.p2-filtres) button:hover{background:#f7f7f4;color:#1a1a18;border-color:#1a1a18;}
:is(.st-key-p2-filtres,.p2-filtres) button:focus-visible{outline:2px solid #1a1a18;outline-offset:2px;}
""" + ''.join(
    f'.st-key-p2-filtre-{clau},.p2-filtre-{clau}' + '{--p2-filtre-color:' + color + ';}'
    for clau, (_, color, _, _) in ESTATS.items())


def filtres_html(celles, actiu='totes'):
    """Mateixes etiquetes i estils que els widgets, per a la prova inventada."""
    comptes = recomptes_estat(celles)
    return '<div class="p2-filtres" role="group" aria-label="Quines classes vols veure">' + ''.join(
        f'<button class="p2-filtre-{clau}" data-filtre="{clau}" aria-pressed="{str(clau == actiu).lower()}">'
        f'{nom} ({sum(comptes.values()) if clau == "totes" else comptes[clau]})</button>'
        for clau, (nom, *_) in ESTATS.items()) + '</div>'


# El prefix evita que l'HTML exportat alteri altres components de l'app.
CSS = """
.p2-horari{container:p2-graella / inline-size;width:100%;max-width:100%;min-width:0;color:#1a1a18;font:13px/1.35 system-ui}
.p2-horari .horari-scroll{width:100%;max-width:100%;min-width:0;overflow-x:auto;overscroll-behavior-x:contain;border:1px solid #e6e5e0;border-radius:16px;background:#fff;}
.p2-horari .horari-scroll:focus-visible{outline:3px solid #2a78d6;outline-offset:2px;}
.p2-horari .horari{position:relative;isolation:isolate;display:grid;column-gap:10px;row-gap:0;padding:14px 16px 16px;box-sizing:border-box;background:#fff;}
.p2-horari .horari-titol{grid-column:1/-1;margin:0 0 10px;font-size:16px;font-weight:600;}
.p2-horari .dia-cap{font-size:14px;font-weight:600;padding:4px 4px 10px;border-bottom:1px solid #e6e5e0;}
.p2-horari .hora-cap,.p2-horari .hores{position:sticky;left:0;z-index:2;background:#fff;box-shadow:-16px 0 #fff,10px 0 #fff;}
.p2-horari .hora-cap{font-size:12px;color:#52514e;}
.p2-horari .hores,.p2-horari .dia-horari{display:grid;grid-template-rows:var(--files);padding-top:6px;min-width:0;align-content:start;}
.p2-horari .hora{font-size:12px;color:#8a8984;font-weight:400;transform:translateY(-7px);font-variant-numeric:tabular-nums;}
.p2-horari .hora-plena{color:#3d3c39;font-weight:600;}
.p2-horari .dia-horari{column-gap:6px;background-image:var(--linies);background-position:0 6px;background-repeat:repeat;}
.p2-horari .classe{position:relative;z-index:1;color:#1a1a18;border:0;border-radius:10px;padding:8px 10px;margin:3px 0;min-width:0;min-height:0;box-sizing:border-box;word-break:normal;overflow-wrap:normal;hyphens:none;}
.p2-horari .classe b{display:block;color:#1a1a18;font-size:14px;font-weight:600;line-height:1.25;white-space:normal;word-break:normal;overflow-wrap:normal;hyphens:none;font-family:system-ui,sans-serif;font-variant-ligatures:none;letter-spacing:normal;word-spacing:normal;text-transform:none;}
.p2-horari .classe summary{display:flex;flex-direction:column;gap:3px;cursor:pointer;list-style:none;}
.p2-horari .classe summary::-webkit-details-marker{display:none;}
.p2-horari .classe small{display:block;font-size:12px;color:#52514e;}
.p2-horari .classe .ubicacio{color:#3d3c39;}
.p2-horari .classe .nota{font-size:12px;font-weight:500;}
.p2-horari .classe.apagada{opacity:.25;}
.p2-horari .classe summary:focus-visible{outline:3px solid #2a78d6;outline-offset:2px;}
/* El pressupost usa línies senceres: nom 17.5px, secundàries 16.2px i gap 3px.
   Només el resum tancat queda limitat; obrir recupera tot el contingut. */
.p2-horari .classe{padding-block:var(--padding-classe,8px);}
.p2-horari .classe:not([open]){overflow:hidden;}
.p2-horari .classe:not([open]) summary{min-width:0;}
.p2-horari .classe:not([open]) b{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:var(--linies-nom);max-height:calc(var(--linies-nom)*17.5px);overflow:hidden;text-overflow:ellipsis;}
.p2-horari .classe:not([open]) small{line-height:16.2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;}
.p2-horari .classe:not([open]) .ubicacio{display:var(--mostra-ubicacio);}
.p2-horari .classe:not([open]) summary>small:not([class]){display:var(--mostra-grup);}
.p2-horari .classe:not([open]) .nota{display:var(--mostra-nota);}
.p2-horari .classe[open] b,.p2-horari .classe[open] small{overflow-wrap:break-word;}
.p2-horari .classe[open]{z-index:3;align-self:start;min-height:calc(100% - 6px);box-shadow:0 4px 12px #0002;}
.p2-horari .classe .detall{padding-top:6px;border-top:1px solid #e6e5e0;margin-top:6px;}
.p2-llegenda{display:flex;flex-wrap:wrap;gap:8px;padding:0;list-style:none;font:13px/1.35 system-ui;color:#1a1a18;}
.p2-llegenda li{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border:1px solid #e6e5e0;border-radius:999px;background:#fff;}
.p2-llegenda i{display:inline-block;width:10px;height:10px;border-radius:3px;}
""" + ''.join(
    f'.p2-horari .classe.{clau}' + '{background:' + fons + ';}'
    + f'.p2-horari .classe.{clau} .nota' + '{color:' + text + ';}'
    for clau, (_, _, fons, text) in ESTATS.items() if clau != 'totes')

# La guia compartida encara invoca aquest punt d'entrada. Les línies ara són
# fons CSS de cada dia i no necessiten mesurar files ni observar redimensions.
LINIES_JS = "function preparaLiniesHorari() { return ()=>{}; }"

MIN_CARRIL = 120
AMPLE_HORES = 56


def pressupost_classe(durada, *, nota=False):
    """Alçades en px, compartides amb el CSS; vàlid per qualsevol ample de carril.

    Cada secundària ocupa una sola línia amb el·lipsi. Reservem fins a tres
    línies de nom abans del grup i la nota; el nom aprofita la resta d'espai.
    Els 6px de marge vertical es resten de l'àrea de la graella.
    """
    padding = 2 if durada <= 30 else 8
    caixa = durada * 1.6 - 6
    disponible = max(0, caixa - 2 * padding)
    nom = min(3, max(1, int((disponible - 19.2) // 17.5)))
    visible = nom * 17.5
    ubicacio = visible + 19.2 <= disponible
    visible += 19.2 if ubicacio else 0
    grup = ubicacio and visible + 19.2 <= disponible
    visible += 19.2 if grup else 0
    mostra_nota = nota and grup and visible + 19.2 <= disponible
    visible += 19.2 if mostra_nota else 0
    extra = max(0, int((disponible - visible) // 17.5))
    nom += extra
    visible += extra * 17.5
    return dict(padding=padding, nom=nom, ubicacio=ubicacio, grup=grup,
                nota=mostra_nota, visible=visible + 2 * padding, caixa=caixa)


def taula_html(celles, titol='Horari setmanal', *, originals=False, filtre='totes', estils=True):
    """Una setmana en CSS Grid: 48 px per mitja hora, minuts exactes i carrils.

    Només les classes amb coincidències ocupen un carril; les altres s'estenen
    per tot el dia, com a la referència de disseny.
    """
    celles = agrupa_compartides(celles)
    estil = f'<style>{CSS}</style>' if estils else ''
    if not celles:
        return estil + '<div class="p2-horari"><p class="p2-buit" role="status">No hi ha classes aquesta setmana.</p></div>'
    inici_dia = min(c.ini for c in celles) // 30 * 30
    final_dia = (max(c.fi for c in celles) + 29) // 30 * 30
    carrils = {}
    for dia in DIES:
        ocupats, entrades = [], []
        classes = sorted((c for c in celles if c.dia == dia), key=lambda c: (c.ini, c.fi, c.id_sessio))
        for c in classes:
            carril = next((i for i, fi in enumerate(ocupats) if fi <= c.ini), len(ocupats))
            if carril == len(ocupats):
                ocupats.append(c.fi)
            else:
                ocupats[carril] = c.fi
            coincideix = any(o is not c and o.ini < c.fi and c.ini < o.fi for o in classes)
            entrades.append((carril, coincideix, c))
        carrils[dia] = (max(1, len(ocupats)), entrades)
    columnes = '56px ' + ' '.join(f'minmax(0, {n}fr)' for n, _ in carrils.values())
    # Incloem el padding, els espais entre dies i entre carrils al mínim.
    ample = AMPLE_HORES + 32 + 5 * 10 + sum(n * MIN_CARRIL + (n - 1) * 6 for n, _ in carrils.values())
    primer = '#d9d8d2' if inici_dia % 60 == 0 else '#efeee9'
    segon = '#efeee9' if inici_dia % 60 == 0 else '#d9d8d2'
    linies = f'repeating-linear-gradient(to bottom,{primer} 0 1px,transparent 1px 48px,{segon} 48px 49px,transparent 49px 96px)'
    html = (estil + '<div class="p2-horari"><div class="p2-setmana">'
        f'<div class="horari-scroll" tabindex="0" role="region" aria-label="{escape(titol, quote=True)} · Dilluns – Divendres">'
        f'<div class="horari" style="min-width:{ample}px;grid-template-columns:{columnes};--files:repeat({final_dia-inici_dia},1.6px);--linies:{linies}">'
        f'<div class="horari-titol">{escape(titol)}</div><div class="dia-cap hora-cap">Hora</div>')
    html += ''.join(f'<div class="dia-cap" role="heading" aria-level="3">{nom}</div>' for nom in NOMS_DIES)
    html += '<div class="hores" aria-label="Hores">'
    for inici in range(inici_dia, final_dia, 30):
        plena = ' hora-plena' if inici % 60 == 0 else ''
        html += f'<div class="hora{plena}" data-minut="{inici}" style="grid-row:{inici-inici_dia+1}/span 30">{fmt(inici)}</div>'
    html += '</div>'
    for dia, (n, entrades) in carrils.items():
        html += (f'<section class="dia-horari" aria-label="{NOMS_DIES[DIES.index(dia)]}" '
                 f'data-carrils="{n}" style="grid-template-columns:repeat({n},minmax(0,1fr))">')
        for carril, coincideix, c in entrades:
            estat = estat_cella(c)
            nom, _, _, _ = ESTATS[estat]
            marques = estat + (' apagada' if filtre not in ('totes', estat) else '')
            columna = f'{carril+1}/span 1' if coincideix else f'1/span {n}'
            ubicacio = c.ubicacio_compartida or c.aula or ('Aula no indicada a les dades' if originals else 'Pendent d’assignar aula')
            grup = ' / '.join(c.grups_compartits) or nom_grup(c.grup, c.tipus)
            # El format antic de nom_grup es conserva als altres usos de la pàgina.
            grup = ' / '.join(g.split(' · ', 1)[0] for g in grup.split(' / '))
            tipus = TIPUS.get(c.tipus, c.tipus)
            avisos = list(c.relaxacions)
            if c.setmana_diferent:
                avisos.insert(0, 'Setmana diferent.')
            if c.canvi or c.aula_assignada:
                avisos.append(c.abans or ('Aula assignada.' if c.aula_assignada else 'Canvi de dia, hora o aula.'))
            avis = ' · '.join(avisos)
            nota = ''
            if estat == 'relaxada':
                nota = avisos[0]
            elif estat == 'canvi':
                nota = c.abans.split(' · ', 1)[0] if c.abans else 'Canvi de dia, hora o aula.'
            if len(nota) > 78:
                nota = nota[:75].rsplit(' ', 1)[0] + '…'
            etiqueta = f'{nom} · {c.assignatura} · {fmt(c.ini)}–{fmt(c.fi)} · {ubicacio} · {tipus} · {grup}'
            if avis:
                etiqueta += ' · ' + avis
            if c.compartida:
                etiqueta += ' · Classe compartida'
            nom_assignatura = escape(c.assignatura).replace('’', '&#8217;').replace('‘', '&#8216;')
            contingut = (f'<b>{nom_assignatura}</b><small class="ubicacio">{fmt(c.ini)}–{fmt(c.fi)} · {escape(ubicacio)}</small>'
                        f'<small>{escape(tipus)} · {escape(grup)}</small>')
            if nota:
                contingut += f'<small class="nota">{escape(nota)}</small>'
            pressupost = pressupost_classe(c.fi - c.ini, nota=bool(nota))
            ajust = (f'--padding-classe:{pressupost["padding"]}px;'
                     f'--linies-nom:{pressupost["nom"]};' + ''.join(
                         f'--mostra-{camp}:{"block" if pressupost[camp] else "none"};'
                         for camp in ('ubicacio', 'grup', 'nota')))
            html += (f'<details class="classe {marques}" data-estat="{estat}" '
                f'style="grid-row:{c.ini-inici_dia+1}/span {c.fi-c.ini};grid-column:{columna};{ajust}" '
                f'title="{escape(etiqueta, quote=True)}" aria-label="{escape(etiqueta, quote=True)}">'
                f'<summary>{contingut}</summary><small class="detall">{escape(avis or nom)}</small></details>')
        html += '</section>'
    return html + '</div></div></div></div>'


def exporta_aula_html(base, proposta, setmana, aula, **kwargs):
    titol = f'Aula {aula} · setmana del {dilluns(setmana):%d/%m/%Y}'
    contingut = taula_html(celles_aula(base, proposta, setmana, aula, **kwargs), titol)
    return '<!doctype html><html lang="ca"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>' + escape(titol) + '</title><body><h1>' + escape(titol) + '</h1>' + llegenda_html() + contingut + '</body></html>'
