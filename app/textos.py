"""Textos per al coordinador. Les xifres s'interpolen des de les troballes."""
TEXTOS = {
    'hi-cap-mati': dict(estat='ambre', etiqueta='Pendent de validar', titol='Si 1r i 2n fan classe al matí, hi cabem?',
        frase='Al moment més ple ({dia}) calen {pic} aules de les {disponibles} disponibles. El matí queda ocupat al {ocupacio} %.',
        proposem='Repartir les classes grans entre els dies menys plens.'),
    'fora-torn': dict(estat='vermell', etiqueta='Cal actuar', titol='Classes al torn equivocat',
        frase="Cal canviar de matí a tarda o al revés aproximadament {proporcio}.",
        proposem="Moure-les amb la proposta d’horari."),
    'hores-aula': dict(estat='vermell', etiqueta='Cal actuar', titol='Classes sense aula',
        frase='Sense aula assignada a les dades: aproximadament {proporcio} ({sense_aula} classes).',
        proposem='Assignar-les automàticament.'),
    'marge-grau-nou': dict(estat='ambre', etiqueta='Pendent de validar', titol='Un grau nou de {places} places',
        frase="Necessita {hores_noves} h d’aula a la setmana i en queden {hores_lliures} h lliures al matí. El balanç d’hores i mides és favorable; cal validar l’horari.",
        proposem='Col·locar-lo sobre la proposta nova.'),
    'problemes-millores': dict(estat='ambre', etiqueta='Vigilar', titol="Altres problemes de l’horari",
        frase="Hi ha {xifra} de problemes al semestre: classes sense aula, professorat amb classes alhora i altres desajustos.",
        proposem='Una solució per a cadascun.'),
    'aforament': dict(estat='ambre', etiqueta='Vigilar', titol='Més alumnes que places',
        frase='En {xifra} classes del semestre cal revisar l’aula perquè no hi caben tots els alumnes.',
        proposem='Una aula més gran del mateix passadís.'),
    'ocupacio': dict(estat='ambre', etiqueta='Vigilar', titol='Com fem servir les aules?',
        frase='L’aula més ocupada arriba al {xifra} del temps disponible al semestre. Les aules que semblen buides poden tenir classes pendents d’assignar.',
        proposem='Assignar les classes sense aula abans de decidir on queda espai.'),
    'hores-mortes': dict(estat='ambre', etiqueta='Vigilar', titol='Temps entre classes',
        frase='Els grups acumulen {xifra} d’espera cada setmana de mitjana. És la suma dels grups, no el temps de cada estudiant.',
        proposem='Agrupar les classes de cada grup dins del seu torn.'),
    'canvis-aula': dict(estat='ambre', etiqueta='Vigilar', titol='Canvis de passadís',
        frase='Els grups fan {xifra} canvis de passadís per setmana de mitjana.',
        proposem='Mantenir les classes seguides al mateix passadís sempre que es pugui.'),
    'dobles-mati': dict(estat='ambre', etiqueta='Vigilar', titol='Dobles titulacions al matí',
        frase='Hi ha {xifra} classes de cursos superiors de doble titulació al matí per setmana de mitjana; els correspondria la tarda.',
        proposem='Revisar amb cada titulació quines classes es poden separar.'),
    'docents-cavall': dict(estat='ambre', etiqueta='Vigilar', titol='Professorat amb matí i tarda',
        frase='Amb el model nou, {xifra} docents tindrien classes al matí i a la tarda d’un mateix dia del semestre.',
        proposem='Concentrar les classes de cada docent quan sigui compatible amb els grups.'),
}

PROBLEMES = {
    'Sessions sense aula': 'Classes sense aula',
    'Solapaments de docent heretats': 'Professorat amb dues classes alhora',
    'Solapaments d’alumnat heretats': 'Alumnat amb dues classes alhora',
    'PAUL en laboratoris de Q6': 'Pràctiques d’aula en laboratoris',
    'Sessions fora de la finestra': 'Classes fora de l’horari permès',
    'Sessions a aules J': 'Classes a les aules J',
    'Sessions fora de l’inventari': 'Classes en espais no registrats',
    'Sessions sense dada d’alumnes': 'Classes sense nombre d’alumnes',
    'Més alumnes que places': 'Més alumnes que places',
    'Dispersió d’aules per grup': 'Grups amb classes en moltes aules',
}


# Mètodes de lectura general; les definicions exactes es conserven al desplegable tècnic.
METODES_PLANERS = {
    'hi-cap-mati': 'Comptem les classes de primer i segon que necessiten una aula i les hores disponibles, deixant aules de reserva. No hi entren els laboratoris ni les dobles titulacions sense espai propi. El resum cobreix el semestre i els dies del gràfic mostren la setmana indicada; això encara no garanteix un horari viable.',
    'fora-torn': 'Comparem l’hora actual de cada classe amb el torn que li correspondria. La xifra del semestre no inclou els canvis que ja venien fixats i que la proposta no pot moure. El gràfic mostra els grups de la setmana indicada.',
    'hores-aula': 'Comptem quantes classes del semestre no tenen una aula assignada a les dades, inclosos els laboratoris i les dobles titulacions sense aula pròpia. Per això no totes necessiten una nova assignació. El gràfic mostra les aules necessàries al moment més ple de cada dia de la setmana indicada.',
    'marge-grau-nou': 'Restem de les hores disponibles les que necessiten primer i segon, i les comparem amb les del grau nou. La targeta i el gràfic mostren hores d’una setmana, amb una comprovació de les mides d’aula. La proposta d’horari encara ha de confirmar que les classes poden encaixar.',
    'problemes-millores': 'La xifra principal compta els tipus de problemes que apareixen al semestre. Les quantitats i les propostes del detall corresponen a la setmana indicada, i una classe pot tenir més d’un problema. També es mostren recomanacions que no tenen una quantitat comparable al gràfic.',
    'aforament': 'Comparem els alumnes previstos amb les places de l’aula assignada, sumant els alumnes quan comparteixen classe. La xifra cobreix el semestre i no inclou els casos de classes que ja venien fixades i no es poden moure. El gràfic mostra exemples de la setmana indicada.',
    'ocupacio': 'Mirem quina part de l’horari disponible de cada aula té classes assignades. La xifra principal resumeix el semestre i el plànol mostra la setmana indicada. Les classes sense aula no omplen cap rajola, així que una aula clara no sempre representa espai lliure real.',
    'hores-mortes': 'Sumem els buits entre classes compatibles de cada grup dins del mateix torn, sense duplicar les classes que comparteix. La xifra és la mitjana setmanal del semestre i no representa les hores de cada estudiant. El gràfic mostra els grups de la setmana indicada.',
    'canvis-aula': 'Comptem els canvis de passadís entre classes consecutives de cada grup quan coneixem les dues aules. La xifra és la mitjana setmanal del semestre, incloses les setmanes sense canvis. El gràfic mostra els grups de la setmana indicada.',
    'dobles-mati': 'Comptem les classes de doble titulació de cursos superiors que avui es fan al matí i haurien d’anar a la tarda. La xifra és la mitjana setmanal del semestre i el gràfic mostra la setmana indicada. Cal revisar amb les titulacions si aquestes classes es poden separar.',
    'docents-cavall': 'Mirem quins docents farien classe al matí i a la tarda d’un mateix dia si s’apliquessin els torns nous als dies actuals. La xifra principal cobreix el semestre. El gràfic mostra els dies afectats de cada docent en la setmana indicada.',
}
for id_, metode in METODES_PLANERS.items():
    TEXTOS[id_]['metode_planer'] = metode
