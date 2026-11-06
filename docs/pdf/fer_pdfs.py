"""Genera els dos PDFs de l'equip per a UAB THE HACK! 2026.

Ús: python3 fer_pdfs.py <carpeta de sortida>
"""
import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

SORTIDA = sys.argv[1] if len(sys.argv) > 1 else "."
FONTS = "/System/Library/Fonts/Supplemental/"
pdfmetrics.registerFont(TTFont("Arial", FONTS + "Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", FONTS + "Arial Bold.ttf"))
MONO = "Courier"
if os.path.exists(FONTS + "Courier New.ttf"):
    pdfmetrics.registerFont(TTFont("CourierNew", FONTS + "Courier New.ttf"))
    MONO = "CourierNew"
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold")

BLAU = colors.HexColor("#1F3A5F")
BLAU_CLAR = colors.HexColor("#E8EEF5")
TARONJA = colors.HexColor("#C2541B")
TARONJA_CLAR = colors.HexColor("#FBEDE4")
GRIS = colors.HexColor("#5A6270")
GRIS_LINIA = colors.HexColor("#C9CFD8")

S = {
    "titol": ParagraphStyle("titol", fontName="Arial-Bold", fontSize=24, leading=29, textColor=BLAU),
    "subtitol": ParagraphStyle("subtitol", fontName="Arial", fontSize=12.5, leading=17, textColor=GRIS),
    "h2": ParagraphStyle("h2", fontName="Arial-Bold", fontSize=15, leading=19, textColor=BLAU,
                         spaceBefore=14, spaceAfter=6),
    "p": ParagraphStyle("p", fontName="Arial", fontSize=11, leading=15.5, spaceAfter=5, alignment=TA_LEFT),
    "petit": ParagraphStyle("petit", fontName="Arial", fontSize=9.5, leading=13, textColor=GRIS),
    "cel": ParagraphStyle("cel", fontName="Arial", fontSize=10, leading=13.5),
    "cel_b": ParagraphStyle("cel_b", fontName="Arial-Bold", fontSize=10, leading=13.5, textColor=colors.white),
    "codi": ParagraphStyle("codi", fontName=MONO, fontSize=9.3, leading=12.6),
    "caixa": ParagraphStyle("caixa", fontName="Arial", fontSize=11, leading=15.5),
}
AMPLE = A4[0] - 36 * mm


def p(text, estil="p"):
    return Paragraph(text, S[estil])


def h2(text):
    return p(text, "h2")


def llista(items, marca="•"):
    files = [[p(marca, "p"), p(t)] for t in items]
    t = Table(files, colWidths=[7 * mm, AMPLE - 7 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def numerada(items):
    files = [[p(f"<b>{i}.</b>"), p(t)] for i, t in enumerate(items, 1)]
    t = Table(files, colWidths=[8 * mm, AMPLE - 8 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def checklist(items):
    return llista(items, marca="□")


def taula(capcalera, files, amples, alt_fila=None):
    dades = [[p(c, "cel_b") for c in capcalera]] + [[p(c, "cel") for c in f] for f in files]
    alts = None if alt_fila is None else [None] + [alt_fila] * len(files)
    t = Table(dades, colWidths=[a * AMPLE for a in amples], rowHeights=alts, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLAU),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BLAU_CLAR]),
        ("GRID", (0, 0), (-1, -1), 0.5, GRIS_LINIA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def caixa(titol, linies, fons=TARONJA_CLAR, vora=TARONJA):
    contingut = [p(f"<b>{titol}</b>", "caixa")] + [p(l, "caixa") for l in linies]
    t = Table([[c] for c in contingut], colWidths=[AMPLE])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fons),
        ("LINEBEFORE", (0, 0), (0, -1), 3, vora),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 1),
    ]))
    return t


def codi(text):
    linies = text.strip("\n").split("\n")
    html = "<br/>".join(l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") or "&nbsp;" for l in linies)
    t = Table([[p(html, "codi")]], colWidths=[AMPLE])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
        ("BOX", (0, 0), (-1, -1), 0.5, GRIS_LINIA),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def peu_de_pagina(nom):
    def dibuixa(c, doc):
        c.saveState()
        c.setFont("Arial", 8.5)
        c.setFillColor(GRIS)
        c.drawString(18 * mm, 10 * mm, f"UAB THE HACK! 2026 · {nom}")
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Pàgina {doc.page}")
        c.setStrokeColor(GRIS_LINIA)
        c.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
        c.restoreState()
    return dibuixa


def enganxa_titols(historia):
    """Cada títol h2 va a la mateixa pàgina que el bloc que el segueix."""
    sortida, i = [], 0
    while i < len(historia):
        f = historia[i]
        if isinstance(f, Paragraph) and f.style.name == "h2" and i + 1 < len(historia):
            sortida.append(KeepTogether([f, historia[i + 1]]))
            i += 2
        else:
            sortida.append(f)
            i += 1
    return sortida


def construeix(fitxer, nom, historia):
    historia = enganxa_titols(historia)
    doc = SimpleDocTemplate(
        os.path.join(SORTIDA, fitxer), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=20 * mm,
        title=nom, author="Equip UAB THE HACK! 2026",
    )
    doc.build(historia, onFirstPage=peu_de_pagina(nom), onLaterPages=peu_de_pagina(nom))


# ---------------------------------------------------------------- PDF 1
def pdf_abans():
    h = [
        p("Abans del hackató", "titol"),
        p("UAB THE HACK! 2026 · Llegeix-ho abans de dissabte. Són 10 minuts.", "subtitol"),
        Spacer(1, 10),
        caixa("En una frase", [
            "No guanya l'equip que programa més. Guanya l'equip que resol un problema concret "
            "d'una persona concreta i ho ensenya amb una demo que funciona.",
        ], fons=BLAU_CLAR, vora=BLAU),

        h2("1. Quan i on"),
        taula(["Què", "Detall"], [
            ["Quan", "Dissabte 7 de novembre a les 8:00 fins a diumenge 8 a les 15:00. Són 31 hores seguides."],
            ["On", "Escola d'Enginyeria de la UAB, Carrer de les Sitges, Bellaterra."],
            ["Equip", "3 o 4 persones."],
            ["Reptes", "Els presenten les empreses dissabte al matí. Tots els equips els descobreixen alhora."],
            ["Empreses", "Deloitte (ciberseguretat i IA), Estrella Damm (recursos humans), "
                         "Servei d'Activitat Física de la UAB (salut, enquestes, mapes de calor) i l'Escola d'Enginyeria."],
            ["Ho posen ells", "Menjar, wifi, espai de treball amb endolls i un lloc per dormir."],
            ["Crèdits", "2 crèdits ECTS (estudiants de l'Escola) si l'equip lliura el projecte i el presenta diumenge."],
        ], [0.2, 0.8]),

        h2("2. Les 5 regles d'or"),
        numerada([
            "<b>Una persona, un problema.</b> Escriviu «per a la Marta, tècnica de recursos humans, que perd 3 hores "
            "cada setmana fent X». No escriviu «per a empreses».",
            "<b>Poques funcionalitats.</b> Amb 3 funcionalitats que funcionen n'hi ha prou. Només afegiu un extra "
            "si la demo ja funciona.",
            "<b>Primer el pla, després el codi.</b> No programeu fins que l'especificació (el document que diu què "
            "farem) estigui escrita.",
            "<b>La demo mana.</b> Cada 4 hores, comproveu si podríeu ensenyar la demo ara mateix. Diumenge a les "
            "2:00 congelem: a partir d'aquí no afegim res nou.",
            "<b>Apunteu-ho tot a la bitàcola.</b> Els problemes que trobeu i com els resoleu són la meitat de la "
            "presentació.",
        ]),

        PageBreak(),
        h2("3. Els 6 passos del cap de setmana"),
        taula(["Pas", "Quan", "Què fem", "Resultat"], [
            ["0. Preparació", "Avui i ds 8:00", "Motxilla, eines i preguntes a l'organització.", "Equip a punt."],
            ["1. La idea", "Ds fins a 10:30", "Triem repte, persona i problema.", "Fitxa de la idea omplerta."],
            ["2. Prompt", "Ds 10:30-11:30", "Claude ens entrevista fins que la idea queda clara.", "Especificació escrita."],
            ["3. Construir", "Ds 11:30 - dg 2:00", "Programem en paral·lel i publiquem la web aviat.", "Demo que funciona."],
            ["4. Bitàcola", "Tot el cap de setmana", "Apuntem idees, problemes i solucions.", "docs/BITACOLA.md"],
            ["5. Presentació", "Dg 8:00 - entrega", "Diapositives, demo, vídeo de reserva i assajos.", "Presentació de 3-5 min."],
        ], [0.18, 0.2, 0.37, 0.25]),
        p("Són hores orientatives. Quan sapiguem l'hora d'entrega, les ajustarem.", "petit"),
    ]
    h += [
        h2("4. Què heu de fer avui"),
        checklist([
            "Entreu a <b>uabthehack.cat/participants/acces</b> amb el correu de la inscripció. "
            "Comproveu el vostre equip i baixeu el <b>QR d'accés</b>.",
            "Entreu al <b>Discord</b> de l'event. L'enllaç és a l'àrea de participants o al correu de confirmació.",
            "Instal·leu <b>Claude Code</b> al vostre portàtil i proveu que funciona.",
            "Instal·leu els plugins de l'equip (ordres de sota).",
            "Demaneu al Bernat accés al repositori <b>github.com/bernatroca/hackathon</b> i cloneu-lo.",
            "Llegiu el codi de conducta: no hi ha alcohol i no es pot fer fotos a ningú sense permís.",
            "Dormiu bé aquesta nit.",
        ]),
        Spacer(1, 4),
        p("Ordres per instal·lar els plugins (una per una, al terminal):"),
        codi("""
claude plugin marketplace add 23jmo/jmo-skills
claude plugin install jmo-workflow@jmo-skills
claude plugin marketplace add anthropics/skills
claude plugin install example-skills@anthropic-agent-skills
"""),

        h2("5. Motxilla"),
        checklist([
            "DNI i QR d'accés",
            "Portàtil i <b>carregador</b> (els endolls són de tipus F, els normals d'aquí)",
            "Sac de dormir i coixí",
            "Ampolla d'aigua reutilitzable",
            "Roba còmoda",
            "Allargador i auriculars",
        ]),

        h2("6. Rols de l'equip"),
        taula(["Rol", "Què fa", "Qui"], [
            ["Producte i presentació", "Escriu la fitxa de la idea, busca dades del problema, fa les diapositives i presenta.", ""],
            ["Frontend", "Fa les pantalles i la demo amb Claude.", ""],
            ["Backend i dades", "Fa la part del servidor i les dades. Passa feina a Codex.", ""],
            ["Integració", "Fa els commits, publica la web i revisa la bitàcola cada 4 hores.", ""],
        ], [0.25, 0.55, 0.2]),
        p("Si l'equip és de 3, la persona de Backend també fa Integració.", "petit"),

        h2("7. Preguntes per a l'organització (dissabte al matí)"),
        checklist([
            "A quina hora s'entrega el projecte i a quina hora es presenta?",
            "On s'entrega (per exemple, Devpost) i què cal entregar: codi, diapositives, vídeo?",
            "Quant dura la presentació? Hi ha preguntes del jurat?",
            "Quins criteris fa servir el jurat? Quins premis hi ha?",
            "Podem fer servir IA (Claude, Codex)? L'hem de declarar?",
            "Els reptes donen dades o una API? Tenen límits?",
        ]),
    ]
    h += [
        CondPageBreak(110 * mm),
        h2("8. Paraules que sortiran"),
        taula(["Paraula", "Què vol dir"], [
            ["Agent", "Un programa d'IA que escriu codi i fa tasques per nosaltres. Claude i Codex són agents."],
            ["Claude", "L'agent principal. Fa la planificació, les pantalles i la integració."],
            ["Codex", "Un altre agent (d'OpenAI). Li passem tasques tancades de backend que tenen una prova per "
                      "comprovar-les."],
            ["Skill", "Unes instruccions que l'agent llegeix per fer bé una tasca concreta. Per exemple, "
                      "/jmo-workflow:interview fa que Claude ens entrevisti."],
            ["Especificació (spec)", "El document que diu què farem, per a qui i com sabrem que funciona. "
                                     "Es desa a la carpeta .plans/ del repositori."],
            ["Worktree", "Una còpia del repositori on un agent treballa sol. Així dos agents no toquen els mateixos "
                         "fitxers alhora."],
            ["Desplegar", "Publicar la web perquè s'obri amb un enllaç. Ho fem a Cloudflare."],
            ["Congelació", "El moment (dg 2:00) a partir del qual no afegim funcionalitats noves. Només corregim i polim."],
            ["Bitàcola", "El fitxer docs/BITACOLA.md on apuntem idees, decisions, problemes i solucions. "
                         "Claude l'omple quan li diem «apunta-ho a la bitàcola»."],
            ["Demo", "La part de la presentació on ensenyem el producte funcionant, en directe."],
        ], [0.24, 0.76]),

        h2("9. El que diuen els guanyadors"),
        llista([
            "<b>Johnathan Mo</b> (5 de 5 hackatons): «Imagineu que ja heu guanyat. Quina demo va veure el jurat?» "
            "Comenceu per la idea més espectacular i retalleu-la fins que sigui possible fer-la a temps.",
            "<b>Johnathan Mo</b>: van planificar 2-3 hores amb Claude, van repartir el pla en tasques i van "
            "guanyar un hackató de 24 hores treballant-ne 8 o 9.",
            "<b>Zahur</b> (11 de 15 hackatons): «No demaneu idees a la IA. Feu que investigui el problema.»",
            "<b>Zahur</b>: «Sou enginyers per resoldre un problema, no per programar.»",
        ]),
        Spacer(1, 10),
        caixa("Guia completa", [
            "Tot això i més detall és a la guia de l'equip, amb una pestanya per a cada pas: "
            "claude.ai/artifact/VeteakMwu7Rejbfu4uDqzL",
        ], fons=BLAU_CLAR, vora=BLAU),
    ]
    construeix("1-Abans-del-hackato.pdf", "Abans del hackató", h)


# ---------------------------------------------------------------- PDF 2
def pdf_idea():
    h = [
        p("Ja tenim la idea", "titol"),
        p("UAB THE HACK! 2026 · Què fem des que triem la idea fins a la presentació.", "subtitol"),
        Spacer(1, 10),
        caixa("Ordre de treball", [
            "1. Comproveu la idea.  2. Ompliu la fitxa.  3. Claude us entrevista.  "
            "4. Dividiu la feina en tasques.  5. Construïu.  6. Apunteu-ho tot.  7. Prepareu la presentació.",
        ], fons=BLAU_CLAR, vora=BLAU),

        h2("1. La idea és bona si..."),
        checklist([
            "Es pot explicar en una frase a algú que no sap programar.",
            "Té una persona concreta, i sabem com treballa avui.",
            "Podem demostrar el problema amb una xifra o una notícia.",
            "La demo ensenya el canvi en menys de 2 minuts: abans X, ara Y.",
            "La podem fer amb les dades que tenim avui, sense esperar ningú.",
            "Encaixa amb el que demana l'empresa del repte.",
            "No és només un xat sobre una IA: hi afegim dades, passos o decisions pròpies.",
        ]),

        h2("2. Fitxa de la idea"),
        p("Ompliu-la entre tot l'equip. Després l'enganxareu sencera a l'entrevista amb Claude."),
        taula(["Camp", "Resposta"], [
            ["Repte i empresa", ""],
            ["Persona (nom, feina, context)", ""],
            ["Problema en una frase", ""],
            ["Prova que existeix (xifra o notícia + enllaç)", ""],
            ["Què fa avui i per què no funciona", ""],
            ["La nostra solució en una frase", ""],
            ["Funcionalitat 1 (la clau de la demo)", ""],
            ["Funcionalitat 2", ""],
            ["Funcionalitat 3", ""],
            ["Moment «uau» de la demo", ""],
            ["Abans → després (hores, diners, errors)", ""],
            ["Dades o API que farem servir", ""],
        ], [0.38, 0.62], alt_fila=10.5 * mm),
    ]
    h += [
        PageBreak(),
        h2("3. Claude us entrevista (1 hora)"),
        p("L'entrevista converteix la idea en una <b>especificació</b>: el document que diu què farem, per a qui "
          "i com sabrem que funciona. Tots els agents treballaran a partir d'aquest document."),
        numerada([
            "Obriu una sessió nova de Claude Code a la carpeta del repositori.",
            "Escriviu el prompt de sota amb la fitxa de la idea enganxada.",
            "Responeu les preguntes entre tot l'equip. Si dubteu, trieu l'opció més simple.",
            "Claude desa l'especificació a <b>.plans/</b>. Llegiu-la tots i corregiu el que no quadri.",
        ]),
        codi("""
/jmo-workflow:interview
Estem a UAB THE HACK! (31 h, equip de [3/4], entrega diumenge a les [hora]).
Repte: [empresa i enunciat literal].
Aquí tens la fitxa de la idea:
[enganxa la fitxa]
Entrevista'ns fins que tinguem clar: l'usuari i el seu recorregut pantalla per
pantalla; les 3 funcionalitats imprescindibles i què en queda fora; les dades i
d'on surten; l'stack més simple que podem publicar avui; el moment «uau» de la
demo; i els riscos que ens poden deixar sense demo, amb un pla B per a cadascun.
Fes preguntes que no siguin òbvies. Quan acabis, escriu l'especificació en
català, amb criteris per comprovar cada funcionalitat.
"""),

        h2("4. Dividiu la feina en tasques"),
        p("Una <b>tasca</b> és un tros de feina que una sola persona (amb el seu agent) pot fer sense tocar els "
          "fitxers dels altres."),
        codi("""
Llegeix l'especificació de .plans/ i divideix-la en tasques independents que
es puguin fer en paral·lel sense tocar els mateixos fitxers. Per a cada tasca:
objectiu, fitxers, com es comprova que està feta, i si és millor per a Claude
(pantalles) o per a Codex (lògica amb proves). Ordena-les perquè en 6 hores
tinguem la demo bàsica. Desa-ho a .plans/tasques.md.
"""),

        h2("5. Horari de construcció"),
        taula(["Hora", "Què", "Control"], [
            ["Ds 11:30", "Esquelet del projecte i primera publicació a Cloudflare", "La web s'obre amb un enllaç"],
            ["Ds 11:30-15:00", "Funcionalitat 1, la de la demo (amb dades de prova si cal)", "15:00: podem fer la demo bàsica?"],
            ["Ds 15:00-19:00", "Funcionalitats 2 i 3 i dades reals", "19:00: la demo funciona de principi a fi?"],
            ["Ds 19:00-23:00", "Ho connectem tot i fem el primer polit", "23:00: la podríem ensenyar ja?"],
            ["Dg 23:00-2:00", "Corregim errors i estats de càrrega o d'error", "<b>2:00: congelació</b>"],
            ["Dg 2:00-8:00", "Polim i dormim per torns (3-4 h cadascú)", "Gravem el vídeo de reserva"],
        ], [0.2, 0.47, 0.33]),
        p("A les 4 de la matinada és quan costa més: mengeu alguna cosa i feu torns.", "petit"),
    ]
    h += [
        PageBreak(),
        h2("6. Qui fa què"),
        taula(["Feina", "Qui", "Com"], [
            ["Pantalles, disseny i polit", "Claude", "Skills frontend-design, shadcn i /jmo-workflow:better-ui"],
            ["Lògica, servidor i dades amb proves", "Codex", "Model gpt-6.1-sol, effort medium. Si es bloqueja, effort high."],
            ["Revisar la feina d'un altre agent", "Codex", "Mode només lectura"],
            ["Provar la web al navegador", "Claude", "Skill webapp-testing"],
            ["Publicar la web", "Claude", "Cloudflare. Claude demana permís abans de publicar."],
            ["Commits i unir la feina", "Una persona", "Codex no pot fer commits"],
        ], [0.36, 0.17, 0.47]),

        h2("7. Regles per treballar amb agents"),
        llista([
            "<b>Una tasca, una sessió.</b> Dues sessions no toquen mai els mateixos fitxers. Si ho fan, perdreu hores "
            "arreglant conflictes.",
            "<b>Doneu sempre una prova.</b> Cada encàrrec diu com es comprova: una ordre, un enllaç o una captura.",
            "<b>Si l'agent s'encalla</b> després de dues correccions, comenceu una conversa nova (/clear) o torneu a "
            "l'últim commit que funcionava.",
            "<b>Ensenyeu-li un model.</b> Els agents copien millor que no pas inventen: passeu-li una web que us agradi.",
            "<b>Dades de prova primer.</b> Si l'API del repte falla, la demo no s'ha d'aturar.",
            "<b>Cap clau al codi.</b> Les claus van al fitxer .env, que no es puja a GitHub.",
        ]),
        Spacer(1, 4),
        p("Prompt per a cada tasca:"),
        codi("""
Llegeix l'especificació de .plans/ i fes la tasca [n] de .plans/tasques.md.
Només pots tocar aquests fitxers: [llista].
Està feta quan: [prova o ordre que ho demostra].
Quan acabis, comprova-ho, explica què has canviat en 3 línies i apunta a la
bitàcola qualsevol problema o decisió.
"""),

        h2("8. Bitàcola: apunteu-ho mentre passa"),
        p("Digueu-li a Claude, amb paraules normals:"),
        llista([
            "«Apunta a la bitàcola que hem descartat la idea X perquè no tenim dades.»",
            "«Hem tingut un problema: [què passa]. Apunta-ho.» I quan el resolgueu: «Apunta la solució.»",
            "«Apunta aquesta dada per a la presentació: [xifra + enllaç].»",
            "Diumenge al matí: «Fes el resum de la bitàcola per a la presentació.»",
        ]),
    ]
    h += [
        PageBreak(),
        h2("9. La presentació comença dissabte"),
        p("Una persona de l'equip pensa des del primer dia com s'ensenyarà cada funcionalitat. "
          "Dissabte a la tarda, aquesta persona busca dades del problema amb aquest prompt:"),
        codi("""
Busca notícies, informes i estadístiques recents (2024-2026, millor d'Espanya
o Catalunya) sobre [problema] per a [persona]. Vull 3-5 xifres o titulars amb
la font i la data, i el cost del problema en hores, diners o errors. Obre les
pàgines. Apunta cada dada a la bitàcola com a DADA.
"""),
        h2("10. Les 3 preguntes que respon la presentació"),
        taula(["Pregunta", "Què hi posem"], [
            ["Quin problema resolem i per a qui?", "La persona amb nom i el seu problema en una frase."],
            ["Com sabem que és real?", "1-2 xifres o notícies amb la font, i quant costa el problema."],
            ["Per què funciona la nostra solució?", "La demo en directe i l'abans → després amb números."],
        ], [0.4, 0.6]),

        h2("11. Ordre de la presentació (3-5 minuts)"),
        numerada([
            "<b>Problema i persona</b> (20 s). Comenceu amb una pregunta al públic: «Qui ha hagut de...?»",
            "<b>Prova</b> (20 s): la xifra o la notícia, amb la font.",
            "<b>Cost</b> (15 s): quant es perd avui.",
            "<b>Solució</b> (15 s): una frase sense paraules tècniques.",
            "<b>Demo en directe</b> (90-120 s): el recorregut de la persona, començant per la funcionalitat clau.",
            "<b>Abans → després</b> (15 s): «de 3 hores a 10 minuts».",
            "<b>Com ho hem fet</b> (20 s): el problema més difícil, com el vam resoldre i com vam fer servir la IA.",
            "<b>Següents passos i equip</b> (10 s).",
        ]),
        Spacer(1, 6),
        caixa("Davant del jurat", [
            "Escolteu cada pregunta sencera. No discutiu.",
            "Si una cosa no està feta, digueu-ho: «No ens ha donat temps. És el següent pas.» El jurat penalitza "
            "molt les mentides.",
            "Tingueu un vídeo de reserva d'1-2 minuts per si la demo falla.",
        ]),
    ]
    construeix("2-Ja-tenim-la-idea.pdf", "Ja tenim la idea", h)


if __name__ == "__main__":
    os.makedirs(SORTIDA, exist_ok=True)
    pdf_abans()
    pdf_idea()
    print("fet")
