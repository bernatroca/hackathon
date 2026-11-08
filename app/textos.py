"""Textos per al coordinador. Les xifres s'interpolen des de les troballes."""
# Resums de portada; les explicacions i les propostes es conserven al detall.
TEXTOS_PORTADA = {
    'hi-cap-mati': dict(titol='Si 1r i 2n fan classe al matí, hi cabem?',
        frase='El balanç d’hores deixa marge; falta validar l’horari.'),
    'fora-torn': dict(titol='Classes fora de torn',
        frase='Classes del semestre que cal revisar de torn.'),
    'hores-aula': dict(titol='Classes sense aula',
        frase='Classes del semestre sense cap aula assignada.'),
    'marge-grau-nou': dict(titol='Un grau nou de {places} places',
        frase='Hores setmanals necessàries; l’horari encara s’ha de validar.'),
    'problemes-millores': dict(titol='Altres problemes',
        frase='Casos del semestre amb desajustos que cal revisar.'),
}

TEXTOS = {
    'hi-cap-mati': dict(estat='ambre', etiqueta='Pendent de validar', titol='Si 1r i 2n fan classe al matí, hi cabem?',
        frase='Al moment més ple ({dia}) calen {pic} aules de les {disponibles} disponibles. El matí queda ocupat al {ocupacio} %.',
        proposem='Repartir les classes grans entre els dies menys plens.'),
    'fora-torn': dict(estat='vermell', etiqueta='Cal actuar', titol='Classes al torn equivocat',
        frase="Cal canviar de matí a tarda o al revés {proporcio}.",
        proposem="Revisar els canvis de torn amb la proposta d’horari."),
    'hores-aula': dict(estat='vermell', etiqueta='Cal actuar', titol='Classes sense aula',
        frase='Sense aula assignada a les dades: {proporcio} ({sense_aula} classes).',
        proposem='Assignació automàtica prevista a la proposta d’horari.'),
    'marge-grau-nou': dict(estat='ambre', etiqueta='Pendent de validar', titol='Un grau nou de {places} places',
        frase="{hores_noves} h a la setmana que necessita; {hores_lliures} h lliures {etiqueta_setmana}. Cal validar l’horari.",
        proposem='Comprovar si es pot incorporar a la proposta nova.'),
    'problemes-millores': dict(estat='ambre', etiqueta='Vigilar', titol="Altres problemes de l’horari",
        frase="Hi ha {xifra} de problemes al semestre: classes sense aula, professorat amb classes alhora i altres desajustos.",
        proposem='Revisar una possible millora per a cadascun.'),
    'aforament': dict(estat='ambre', etiqueta='Vigilar', titol='Més alumnes que places',
        frase='En {aforament_total} classes del semestre ({grups_afectats} grups) no hi caben tots els alumnes: {xifra} es poden corregir canviant l’aula; {aforament_heretades} són de grups fixats.',
        proposem='Una aula més gran del mateix passadís.'),
    'ocupacio': dict(estat='ambre', etiqueta='Vigilar', titol='Com fem servir les aules?',
        frase='L’aula més ocupada arriba al {xifra} del temps disponible a les setmanes lectives del semestre. Les aules que semblen buides poden tenir classes pendents d’assignar.',
        proposem='Assignar les classes sense aula abans de decidir on queda espai.'),
    'hores-mortes': dict(estat='ambre', etiqueta='Vigilar', titol='Temps entre classes',
        frase='Els grups acumulen {xifra} d’espera per setmana lectiva de mitjana. És la suma dels grups, no el temps de cada estudiant.',
        proposem='Agrupar les classes de cada grup dins del seu torn.'),
    'canvis-aula': dict(estat='ambre', etiqueta='Vigilar', titol='Canvis de passadís',
        frase='Els grups fan {xifra} canvis de passadís per setmana lectiva de mitjana.',
        proposem='Mantenir les classes seguides al mateix passadís sempre que es pugui.'),
    'dobles-mati': dict(estat='ambre', etiqueta='Vigilar', titol='Dobles titulacions al matí',
        frase='Hi ha {xifra} classes de cursos superiors de doble titulació al matí per setmana lectiva de mitjana; els correspondria la tarda.',
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
    'fora-torn': 'Comparem l’hora actual de cada classe amb el torn que li correspondria. La xifra del semestre no inclou els canvis que ja venien fixats i que la proposta no pot moure. El gràfic mostra el desglossament del semestre per titulació i curs; una classe compartida pot comptar en més d’un grup.',
    'hores-aula': 'Comptem quantes classes del semestre no tenen una aula assignada a les dades, inclosos els laboratoris i les dobles titulacions sense aula pròpia. Per això no totes necessiten una nova assignació. El gràfic mostra les aules necessàries al moment més ple de cada dia de la setmana indicada.',
    'marge-grau-nou': 'Comparem les hores que necessita el grau nou amb les que queden lliures després de primer i segon a la setmana indicada. Per defecte triem la setmana amb més hores-aula de demanda de matí de l’horari existent. Aquest balanç encara s’ha de confirmar amb un horari viable.',
    'problemes-millores': 'La xifra principal compta els tipus de problemes que apareixen al semestre. Les quantitats i les propostes del detall corresponen a la setmana indicada, i una classe pot tenir més d’un problema. També es mostren recomanacions que no tenen una quantitat comparable al gràfic.',
    'aforament': 'Comparem els alumnes previstos amb les places de l’aula assignada, sumant els alumnes quan comparteixen classe. La xifra principal compta els casos del semestre que es poden corregir canviant l’aula. També indiquem el total, els grups afectats i les classes de grups fixats. El gràfic mostra exemples de la setmana indicada.',
    'ocupacio': 'Mirem quina part de l’horari disponible de cada aula té classes assignades. La xifra principal compta només les setmanes lectives (les que tenen almenys la meitat de classes de la setmana més plena) i el plànol mostra la setmana indicada. Les classes sense aula no omplen cap rajola, així que una aula clara no sempre representa espai lliure real.',
    'hores-mortes': 'Sumem els buits entre classes compatibles de cada grup dins del mateix torn, sense duplicar les classes que comparteix. Repartim el total del semestre entre les setmanes lectives; són hores de grup, no de cada estudiant. El gràfic mostra els grups de la setmana indicada.',
    'canvis-aula': 'Comptem els canvis de passadís entre classes consecutives de cada grup quan coneixem les dues aules. Repartim el total del semestre entre les setmanes lectives. El gràfic mostra els grups de la setmana indicada.',
    'dobles-mati': 'Comptem les classes de doble titulació de cursos superiors que avui es fan al matí i haurien d’anar a la tarda. Repartim el total del semestre entre les setmanes lectives i el gràfic mostra la setmana indicada. Cal revisar amb les titulacions si aquestes classes es poden separar.',
    'docents-cavall': 'Mirem quins docents farien classe al matí i a la tarda d’un mateix dia si s’apliquessin els torns nous als dies actuals. La xifra principal cobreix el semestre. El gràfic agrupa el recompte de docents pel nombre de dies amb matí i tarda de la setmana indicada, sense mostrar identificadors.',
}
for id_, metode in METODES_PLANERS.items():
    TEXTOS[id_]['metode_planer'] = metode

for id_ in ('hores-mortes', 'canvis-aula', 'dobles-mati'):
    TEXTOS[id_]['metode_planer'] += ' Considerem lectives les setmanes amb almenys la meitat de classes de la setmana més plena del semestre.'
