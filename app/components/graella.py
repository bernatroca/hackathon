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
    'totes': ('▦', 'Totes', '#2a78d6', '#e8f1fc', '#1d5fae'),
    'aula-nova': ('✓', 'Aula assignada', '#2f8f46', '#e9f4ec', '#1f6b33'),
    'canvi': ('!', 'Canvia', '#e8820c', '#fff1e0', '#9a5200'),
    'relaxada': ('×', 'Cas especial', '#d03b3b', '#fbe9e9', '#a12c2c'),
    'igual': ('●', 'Sense canvis', '#2a78d6', '#e8f1fc', '#1d5fae'),
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


# Estils compartits entre els botons Streamlit i la prova HTML inventada.
CSS_FILTRES = """
:is(.st-key-p2-filtres,.p2-filtres){display:flex;flex-wrap:wrap;gap:8px;min-width:0;}
.st-key-p2-filtres [data-testid="stHorizontalBlock"]{gap:8px;flex-wrap:wrap;}
.st-key-p2-filtres [data-testid="stColumn"]{width:auto!important;flex:0 0 auto!important;min-width:0!important;}
:is(.st-key-p2-filtres,.p2-filtres) button{display:inline-flex;align-items:center;gap:8px;background:#fff;color:#1a1a18;border:1px solid #d4d3cd;border-radius:999px;padding:5px 10px;min-height:32px;font:14px/1.35 system-ui;box-shadow:none;}
:is(.st-key-p2-filtres,.p2-filtres) button p{font-size:14px;white-space:nowrap;font-weight:inherit;}
:is(.st-key-p2-filtres,.p2-filtres) button::before{content:"";display:block;flex:none;width:10px;height:10px;border-radius:3px;background:var(--p2-filtre-color);}
:is(.st-key-p2-filtres,.p2-filtres) button:is([kind="primary"],[aria-pressed="true"]){background:#fff;color:#1a1a18;border-color:#1a1a18;font-weight:700;outline:none;}
:is(.st-key-p2-filtres,.p2-filtres) button:hover{background:#f7f7f4;color:#1a1a18;border-color:#1a1a18;}
:is(.st-key-p2-filtres,.p2-filtres) button:focus-visible{outline:2px solid #1a1a18;outline-offset:2px;}
""" + ''.join(
    f'.st-key-p2-filtre-{clau},.p2-filtre-{clau}' + '{--p2-filtre-color:' + color + ';}'
    for clau, (_, _, color, _, _) in ESTATS.items())


def filtres_html(celles, actiu='totes'):
    """Mateixes etiquetes i estils que els widgets, per a la prova inventada."""
    comptes = recomptes_estat(celles)
    return '<div class="p2-filtres" role="group" aria-label="Quines classes vols veure">' + ''.join(
        f'<button class="p2-filtre-{clau}" data-filtre="{clau}" aria-pressed="{str(clau == actiu).lower()}">'
        f'{nom} ({sum(comptes.values()) if clau == "totes" else comptes[clau]})</button>'
        for clau, (_, nom, *_) in ESTATS.items()) + '</div>'


# El prefix evita que l'HTML exportat alteri altres components de l'app.
CSS = """
.p2-horari{container:p2-graella / inline-size;width:100%;max-width:100%;min-width:0;color:#1a1a18;font:13px/1.35 system-ui}
.p2-horari .horari-scroll{width:100%;max-width:100%;min-width:0;overflow-x:auto;overscroll-behavior-x:contain;border-radius:14px;background:#fff;}
.p2-horari .horari-scroll:focus-visible{outline:3px solid #2a78d6;outline-offset:2px;}
.p2-horari .horari{position:relative;isolation:isolate;border-collapse:separate;border-spacing:0;table-layout:fixed;width:100%;background:#fff;}
.p2-horari .horari th,.p2-horari .horari td{box-sizing:border-box;border:1px solid #e6e5e0;border-width:0 1px 0 0;padding:4px;vertical-align:top;}
.p2-horari .horari th{background:#f4f3ef;font-weight:600;}
.p2-horari .horari tbody{background-color:#fff;background-repeat:no-repeat;}
.p2-horari .horari tbody tr{height:32px;}
.p2-horari .horari tbody tr.mitja-hora{background-image:linear-gradient(#e6e5e0,#e6e5e0);background-size:100% 1px;background-repeat:no-repeat;}
.p2-horari .horari tbody tr.hora-plena{background-image:linear-gradient(#c9c8c2,#c9c8c2);background-size:100% 2px;background-repeat:no-repeat;}
.p2-horari .horari tbody th,.p2-horari .horari thead th:first-child{position:sticky;left:0;z-index:2;background:#f4f3ef;}
.p2-horari .horari thead th{border-bottom:1px solid #e6e5e0;}

.p2-horari .horari .hora{width:72px;}
.p2-horari .horari tbody th{font-size:11px;color:#52514e;font-weight:400;}
.p2-horari .horari caption{text-align:left;font-size:16px;font-weight:600;padding:10px 12px;}
.p2-horari .classe{position:relative;z-index:1;color:#1a1a18;background:#fff;border:1px solid #e6e5e0;border-left:5px solid #2a78d6;border-radius:8px;padding:6px;min-width:0;height:100%;box-sizing:border-box;word-break:normal;overflow-wrap:normal;hyphens:none;}
.p2-horari .classe.aula-nova{border-left-color:#2f8f46;}
.p2-horari .classe.canvi{border-left-color:#e8820c;}
.p2-horari .classe.relaxada{border-left-color:#d03b3b;}
.p2-horari .classe b{display:block;color:#1a1a18;font-size:14px;font-weight:700;white-space:normal;word-break:normal;overflow-wrap:normal;hyphens:none;font-family:system-ui,sans-serif;font-variant-ligatures:none;letter-spacing:normal;word-spacing:normal;text-transform:none;}
.p2-horari .classe small{display:block;margin-top:3px;color:#52514e;font-size:12px;}
.p2-horari .classe .estat{display:inline-flex;align-items:center;gap:4px;white-space:normal;font-size:12px;line-height:1.25;font-weight:600;border-radius:999px;padding:2px 7px;margin-top:5px;background:#e8f1fc;color:#1d5fae;}
.p2-horari .classe.aula-nova .estat{background:#e9f4ec;color:#1f6b33;}
.p2-horari .classe.canvi .estat{background:#fff1e0;color:#9a5200;}
.p2-horari .classe.relaxada .estat{background:#fbe9e9;color:#a12c2c;}
.p2-horari .classe .estat svg{width:14px;height:14px;flex:none;}
.p2-horari .classe.apagada{opacity:.25;}
.p2-horari .classe summary:focus-visible{outline:3px solid #2a78d6;outline-offset:2px;}
.p2-horari .classe summary{cursor:pointer;list-style:none;}
.p2-horari .classe summary::-webkit-details-marker{display:none;}
.p2-horari .classe .detall{padding-top:6px;border-top:1px solid #e6e5e0;margin-top:6px;}
"""

# El fons del tbody travessa també les cel·les amb rowspan. Mesurem les files
# perquè un nom llarg o un límit parcial pot alterar-ne l'alçada. No s'afegeix
# cap element (ni pseudo-element) al model de columnes de la taula.
LINIES_JS = """
function preparaLiniesHorari(arrel, host) {
  const cossos=[...arrel.querySelectorAll('table.horari tbody')].filter(c=>c.rows);
  if(!cossos.length)return ()=>{};
  let frame,acabat=false;
  const dibuixa=()=>{
    if(acabat)return;
    for(const cos of cossos){
      const rect=cos.getBoundingClientRect();
      if(!rect.height)continue;
      const imatges=[],mides=[],posicions=[];
      const linia=(y,color,gruix)=>{
        imatges.push(`linear-gradient(${color},${color})`);
        mides.push(`100% ${gruix}px`);posicions.push(`0 ${y}px`);
      };
      for(const fila of cos.rows){
        const plena=fila.classList.contains('hora-plena');
        if(plena||fila.classList.contains('mitja-hora')){
          linia(fila.getBoundingClientRect().top-rect.top,
                plena?'#c9c8c2':'#e6e5e0',plena?2:1);
        }
      }
      linia(rect.height-1,'#e6e5e0',1);
      cos.style.backgroundImage=imatges.join(',');
      cos.style.backgroundSize=mides.join(',');
      cos.style.backgroundPosition=posicions.join(',');
    }
  };
  const programa=()=>{
    if(acabat)return;
    host.cancelAnimationFrame(frame);frame=host.requestAnimationFrame(dibuixa);
  };
  const observer=new host.ResizeObserver(programa);
  cossos.forEach(cos=>observer.observe(cos));
  host.document.fonts?.ready.then(programa);
  programa();
  return ()=>{acabat=true;observer.disconnect();host.cancelAnimationFrame(frame);};
}
"""


def script_linies_html():
    return '<script>' + LINIES_JS + 'preparaLiniesHorari(document,window);</script>'


MIN_CARRIL = 150
AMPLE_HORES = 72


def amplada_bloc(carrils, dies):
    return AMPLE_HORES + MIN_CARRIL * sum(carrils[d][0] for d in dies)


def taula_html(celles, titol='Horari setmanal', *, originals=False, filtre='totes', estils=True):
    """Una cel·la amb rowspan per sessió; carrils paral·lels si se solapen.

    Les files parcials respecten els minuts exactes: dues classes consecutives
    no creen carrils perquè comparteixin una mitja hora visual.
    """
    celles = agrupa_compartides(celles)
    if not celles:
        return (f'<style>{CSS}</style>' if estils else '') + '<div class="p2-horari"><p class="p2-buit" role="status">No hi ha classes aquesta setmana.</p></div>'
    # El rang pertany a tota la setmana visible i es conserva en cada bloc.
    inici_dia = min(c.ini for c in celles) // 30 * 30
    final_dia = (max(c.fi for c in celles) + 29) // 30 * 30
    franges = tuple(range(inici_dia, final_dia, 30))
    # Els límits exactes eviten solapaments inventats per l'arrodoniment.
    limits = sorted({*franges, final_dia} | {
        minut for c in celles for minut in (c.ini, c.fi)})
    files = {minut: i for i, minut in enumerate(limits)}
    carrils = {}
    for dia in DIES:
        ocupats = []
        entrades = []
        for c in sorted((c for c in celles if c.dia == dia), key=lambda c: (c.ini, c.fi, c.id_sessio)):
            inici = files[c.ini]
            final = files[c.fi]
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
    def bloc(dies, *, carril_unic=None):
        # En una pantalla més estreta que un dia, els subgrups també s'apilen.
        # Cada classe ampla es mostra només al primer dels seus carrils.
        ample_bloc = (AMPLE_HORES + MIN_CARRIL if carril_unic is not None
                      else amplada_bloc(carrils, dies))
        noms = ' – '.join(NOMS_DIES[DIES.index(d)] for d in (dies[0], dies[-1])) if len(dies) > 1 else NOMS_DIES[DIES.index(dies[0])]
        etiqueta = f'{titol} · {noms}'
        if carril_unic is not None:
            etiqueta += f' · Carril {carril_unic + 1}'
        html = (f'<div class="horari-scroll" tabindex="0" role="region" aria-label="{escape(etiqueta, quote=True)}">'
                f'<table class="horari" style="min-width:{ample_bloc}px"><caption>{escape(etiqueta)}</caption>'
                '<colgroup><col class="hora">')
        for dia in dies:
            n = 1 if carril_unic is not None else carrils[dia][0]
            html += '<col class="carril">' * n
        html += '</colgroup><thead><tr><th scope="col">Hora</th>'
        html += ''.join(f'<th scope="col" colspan="{1 if carril_unic is not None else carrils[d][0]}">{NOMS_DIES[DIES.index(d)]}</th>' for d in dies)
        html += '</tr></thead><tbody>'
        for fila, inici in enumerate(limits[:-1]):
            alt = (limits[fila + 1] - inici) / 30 * 32
            linia = 'hora-plena' if inici % 60 == 0 else 'mitja-hora' if inici % 30 == 0 else 'fraccio'
            html += f'<tr class="{linia}" data-minut="{inici}" style="height:{alt:g}px">'
            if inici in franges:
                html += f'<th scope="row" rowspan="{files[min(inici+30, final_dia)]-fila}">{fmt(inici)}–{fmt(inici+30)}</th>'
            for dia in dies:
                n = carrils[dia][0] if carril_unic is None else carril_unic + 1
                carril = 0 if carril_unic is None else carril_unic
                while carril < n:
                    entrada = inicis.get((dia, fila, carril))
                    if entrada is None:
                        coberta = (dia, fila, carril) in cobertes
                        if carril_unic is not None:
                            # Només ometem els rowspans que comencen en aquest carril.
                            coberta = any(d == dia and k == carril and primera < fila < final
                                          for (d, primera, k), (final, _, _) in inicis.items())
                        if coberta:
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
                    if carril_unic is not None:
                        ample = 1
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
                    pastilla = f'<span class="estat"><span aria-hidden="true">{icona}</span>{nom}</span>'
                    compartida = '<small>Classe compartida</small>' if c.compartida else ''
                    nom_assignatura = escape(c.assignatura).replace('’', '&#8217;').replace('‘', '&#8216;')
                    contingut = f'<b>{nom_assignatura}</b><small>{escape(detall)}</small>{compartida}{pastilla}'
                    classe = (f'<details class="classe{marques}" data-estat="{estat}" title="{escape(avis, quote=True)}">'
                        f'<summary>{contingut}</summary><small class="detall">{escape(avis or "Es manté la classe de les dades originals.")}</small></details>')
                    html += f'<td rowspan="{final-fila}" colspan="{ample}">{classe}</td>'
                    carril += ample
            html += '</tr>'
        return html + '</tbody></table></div>'

    # Una sola setmana seguida, també quan falta amplada a la pantalla.
    return (f'<style>{CSS if estils else ""}</style><div class="p2-horari">'
            '<div class="p2-setmana">' + bloc(DIES) + '</div></div>')


def exporta_aula_html(base, proposta, setmana, aula, **kwargs):
    titol = f'Aula {aula} · setmana del {dilluns(setmana):%d/%m/%Y}'
    contingut = taula_html(celles_aula(base, proposta, setmana, aula, **kwargs), titol)
    return '<!doctype html><html lang="ca"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>' + escape(titol) + '</title><body><h1>' + escape(titol) + '</h1>' + llegenda_html() + contingut + script_linies_html() + '</body></html>'
