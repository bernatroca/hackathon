"""Munta el vídeo «Com funciona l'app»: veu, línia de temps i (amb --render) el vídeo.

Cada escena dura el que dura la seva frase de veu, més una pausa, perquè el vídeo respiri.
Genera docs/demo/muntatge-app/escenes.js i docs/demo/muntatge-app/veu/veu.m4a.

Ús (des de l'arrel del repositori):
  python docs/demo/eines/munta_app.py              # veu + línia de temps
  python docs/demo/eines/render.py docs/demo/muntatge-app docs/demo/demo-app.mp4
"""
import json, os, subprocess, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(os.path.dirname(AQUI), 'muntatge-app')
VEU, VELOCITAT = 'Montse', 182
INICI_VEU, PAUSA, CARTA = 0.4, 0.8, 1.8
CAP1 = '<b>Nivell 1</b> · Anàlisi de dades'
CAP2 = '<b>Nivell 2</b> · Torns nous (5.2)'
CAP3 = '<b>Nivell 2</b> · Imprevistos (5.3)'
CAP4 = '<b>Nivell 2</b> · Grau nou (5.4)'
CAP5 = '<b>Nivell 3</b> · Assistent'
PLE = [0, 0, 1440, 900]

ESCENES = [
    dict(carta=dict(kicker='UAB The Hack! 2026 · Repte d’horaris i espais', h1='Hem fet una app',
                    p='Espais de l’Escola: l’horari 2027-28 de l’Escola d’Enginyeria, per a Gestió Acadèmica'),
         veu='Hem fet una app: Espais de l’Escola, per fer i entendre l’horari del curs vinent.'),
    dict(img='a01-portada', veu='Té tres parts: com estem avui, l’horari proposat, i un assistent.',
         cam=[[0, PLE]], marcs=[dict(t=0.9, fi=-1.6, r=[30, 50, 255, 255])],
         cursor=[[0.6, 700, 600], [1.3, 150, 97], [2.4, 150, 212], [3.4, 150, 250], [4.6, 1340, 805]],
         rotols=[dict(t=0.4, acte='L’app', gran='Espais de l’Escola',
                      petit='Com estem avui · Horari proposat · Resum per a la Junta · Imprevistos · Assistent')]),

    dict(carta=dict(kicker='Nivell 1 · Anàlisi de dades', h1='Com estem avui?',
                    p='Les preguntes de Gestió Acadèmica, cadascuna amb la xifra i com s’ha calculat'), fons='a02-respostes'),
    dict(img='a02-respostes', capitol=CAP1, veu='Primer, l’anàlisi: onze respostes, de la més urgent a la menys.',
         cam=[[0.3, PLE], [3.5, [341, 225, 1060, 320]]], maxS=1.3,
         cursor=[[2.2, 900, 700], [-0.9, 430, 499]], clics=[[-0.6, 430, 499]],
         rotols=[dict(t=0.5, acte='Nivell 1 · Anàlisi', gran='11 respostes, les urgents primer',
                      petit='Cada targeta porta l’estat, la xifra i «Com ho sabem →»')]),
    dict(img='a03-sense-aula', capitol=CAP1, veu='Avui, tres de cada quatre classes no tenen aula assignada.', minim=5.6,
         cam=[[0.2, PLE], [2.8, [330, 440, 700, 100]]], maxS=1.5,
         marcs=[dict(t=1.6, r=[340, 461, 668, 21]), dict(t=3.6, r=[340, 500, 665, 21])],
         rotols=[dict(t=0.4, acte='El problema', tipus='problema', gran='5.722 classes sense aula (74 %)',
                      petit='4.541 cal assignar-les de debò · 919 són laboratoris · 262, dobles sense aula pròpia')]),
    dict(img='a04-hi-cap', capitol=CAP1, veu='Si primer i segon passen al matí, hi cabem? Sí: quinze aules de dinou, a l’hora punta.',
         cam=[[0.2, PLE], [2.6, [330, 270, 760, 340]]], maxS=1.6,
         marcs=[dict(t=3.6, r=[340, 459, 232, 96]), dict(t=4.6, r=[340, 566, 595, 24])],
         rotols=[dict(t=0.4, acte='La pregunta clau', gran='1r i 2n al matí: hi cabem?', petit='El model nou de l’Escola'),
                 dict(t=3.4, acte='La resposta', tipus='solucio', gran='Sí, hi cap: 15 de 19 aules',
                      petit='A l’hora més plena del matí, i encara queden 2 aules de reserva')]),
    dict(img='a05-hi-cap-calcul', capitol=CAP1, veu='I cada xifra explica com s’ha calculat.', minim=4.6,
         cam=[[0, PLE], [3.0, [330, 90, 1080, 560]]], maxS=1.3,
         marcs=[dict(t=0.8, r=[340, 100, 270, 34])],
         rotols=[dict(t=0.4, acte='Nivell 1 · Anàlisi', gran='Cada xifra, amb el seu càlcul',
                      petit='En paraules planeres i, per a qui ho vulgui, la consulta SQL')]),

    dict(carta=dict(kicker='Nivell 2 · Torns nous (5.2)', h1='Com ho fem possible?',
                    p='Un horari nou: 1r i 2n al matí; 3r, 4t, dobles i màsters a la tarda'), fons='a07-p2-graella'),
    dict(img='a06-p2-grup', capitol=CAP2, veu='Amb els torns nous, tercer de Química passa del matí a la tarda.',
         cam=[[0.2, PLE], [3.0, [340, 160, 1060, 300]]], maxS=1.35,
         marcs=[dict(t=1.2, fi=-2.6, r=[357, 274, 679, 40]), dict(t=-2.4, r=[1036, 352, 85, 58])],
         rotols=[dict(t=0.4, acte='Nivell 2 · Torns nous', gran='3r de Química: del matí a la tarda',
                      petit='8 classes canvien d’hora aquesta setmana, i totes tenen aula')]),
    dict(img='a07-p2-graella', capitol=CAP2, veu='Cada classe diu on era abans.', minim=4.8,
         cam=[[0, [340, 0, 1060, 660]], [2.4, [760, 90, 460, 310]]], maxS=1.9,
         marcs=[dict(t=2.8, r=[1013, 226, 120, 20])],
         rotols=[dict(t=0.4, acte='Nivell 2 · Torns nous', gran='Cada canvi, a la vista',
                      petit='«Abans: dijous 09:30» · ara dijous a les 14:30, a la Q1/1011')]),
    dict(img='a08-verificador', capitol=CAP2,
         veu='El verificador oficial, el del jurat, la valida: totes les classes tenen aula, i les excepcions, declarades.',
         cam=[[0, PLE]],
         marcs=[dict(t=1.0, r=[22, 134, 935, 17]), dict(t=6.0, r=[22, 301, 1160, 17]), dict(t=4.4, r=[22, 614, 1160, 17])],
         rotols=[dict(t=0.6, acte='Verificador oficial', tipus='solucio', dreta=True, gran='VALIDA AMB RELAXACIONS DECLARADES',
                      petit='Classes sense aula: 4.541 → 0 · fora de torn: 2.008 → 0, amb 459 excepcions declarades')]),
    dict(img='a09-junta', capitol=CAP2, veu='La Junta ho té en una pàgina: quinze aules de dinou al matí, divuit a la tarda.',
         cam=[[0.2, PLE], [2.6, [340, 200, 1060, 290]]], maxS=1.35,
         marcs=[dict(t=3.0, r=[341, 212, 520, 260])],
         rotols=[dict(t=0.4, acte='Per a la Junta', gran='La Junta decideix amb una pàgina',
                      petit='Hora punta de matí i tarda, cursos afectats i excepcions · resum A4 descarregable')]),
    dict(img='a10-junta-excepcions', capitol=CAP2,
         veu='El cas més difícil: una classe de la setmana d’avaluació no té cap tarda lliure. Ho demostrem, i ho declarem.',
         cam=[[0.2, PLE], [2.4, [330, 90, 1080, 260]]], maxS=1.3,
         marcs=[dict(t=2.8, r=[340, 140, 1060, 50])],
         rotols=[dict(t=0.4, acte='El més difícil', tipus='dificil', gran='1 excepció nova, demostrada',
                      petit='S04526, divendres 9/4. Les altres 458 són classes fixades que ja són a la tarda')]),

    dict(carta=dict(kicker='Nivell 2 · Imprevistos (5.3) i grau nou (5.4)', h1='I si passa alguna cosa?',
                    p='Quatre imprevistos alhora, i un grau nou de 40 places'), fons='a11-imprevistos'),
    dict(img='a11-imprevistos', capitol=CAP3,
         veu='Quatre imprevistos alhora: aula reservada, grup que creix, avaria i classe cancel·lada. Es resol amb pocs canvis.',
         cam=[[0.2, PLE], [3.2, [341, 150, 1060, 600]]], maxS=1.3,
         marcs=[dict(t=-3.2, r=[361, 180, 261, 26])],
         rotols=[dict(t=0.4, acte='Imprevistos', gran='65 classes canvien d’aula, 1 de dia',
                      petit='Comprovat amb el verificador oficial · 28 segons de càlcul')]),
    dict(img='a12-grau-nou', capitol=CAP4,
         veu='I un grau nou de quaranta places hi cap, sense moure cap classe.',
         cam=[[0.2, PLE], [2.6, [860, 262, 290, 560]]], maxS=1.55, origen='dreta',
         marcs=[dict(t=3.2, r=[904, 438, 206, 132])],
         rotols=[dict(t=0.4, acte='Grau nou', tipus='solucio', gran='Un grau nou de 40 places hi cap',
                      petit='235 sessions noves · 0 classes del 5.2 mogudes · verificador oficial')]),

    dict(carta=dict(kicker='Nivell 3 · Intel·ligència artificial', h1='Pregunta-ho',
                    p='Un assistent que respon amb les dades de l’horari, i diu d’on ho treu'), fons='a13-assistent-16-resposta'),
    dict(capitol=CAP5, veu='I l’assistent: on té classe aquest grup, dijous?', minim=6.2,
         frames=[[0, 'a07-p2-graella'], [1.0, 'a13-assistent-00-obert']]
                + [[1.3 + 0.16 * i, f'a13-assistent-{i + 1:02d}-escriu'] for i in range(13)]
                + [[3.55, 'a13-assistent-14-pensant'], [5.3, 'a13-assistent-15-escrivint'], [5.7, 'a13-assistent-16-resposta']],
         cam=[[0, PLE]], cursor=[[0.1, 900, 600], [0.75, 1352, 806]], clics=[[0.8, 1352, 806]],
         rotols=[dict(t=1.2, acte='Nivell 3 · Assistent', gran='«On té classe el grup 21 de 3r de Química dijous?»',
                      petit='Sap què hi ha a la pantalla: proposta 5.2 · GEQ 3r · grup 21')]),
    dict(capitol=CAP5, img='a13-assistent-16-resposta', sensefosa=True,
         veu='Respon amb les dades, i diu quines sessions són, perquè ho puguis comprovar.',
         cam=[[0.2, PLE], [2.0, [740, 100, 700, 430]]], maxS=1.6, origen='dreta',
         marcs=[dict(t=2.4, r=[1244, 299, 134, 20])],
         rotols=[dict(t=0.4, acte='Nivell 3 · Assistent', gran='S00086 i S11829, a la Q1/1011',
                      petit='Cada resposta surt d’una consulta a les dades; avui eren al matí')]),

    dict(carta=dict(kicker='Espais de l’Escola', h1='Ho entens, ho decideixes, ho preguntes',
                    p='Anàlisi · horari proposat i verificat · resum per a la Junta · imprevistos · assistent'),
         veu='Espais de l’Escola: l’horari, comprovat i explicat.', minim=3.8),
]


def durada(f):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]))


def main():
    tmp = tempfile.mkdtemp(prefix='veu-app-')
    t, linies = 0.0, []
    for n, e in enumerate(ESCENES):
        if e.get('veu'):
            f = os.path.join(tmp, f'{n:02d}.aiff')
            for intent in range(4):  # «say» de vegades es queda encallat: torna-ho a provar
                try:
                    subprocess.run(['say', '-v', VEU, '-r', str(VELOCITAT), '-o', f, e['veu'].replace('’', "'")], check=True, timeout=30)
                    break
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                    if intent == 3:
                        raise
            d = durada(f)
            linies.append((t + INICI_VEU, f))
            dur = max(INICI_VEU + d + PAUSA, e.get('minim', 0))
        else:
            dur = e.get('minim', CARTA)
        e['ini'], e['fi'] = round(t, 3), round(t + dur, 3)
        e.pop('veu_text', None)
        t += dur
    total = round(t, 3)
    os.makedirs(os.path.join(DIR, 'veu'), exist_ok=True)
    ent, filtres = [], []
    for i, (ini, f) in enumerate(linies):
        ent += ['-i', f]
        ms = int(ini * 1000)
        filtres.append(f'[{i}:a]aresample=48000,adelay={ms}|{ms}[a{i}]')
    mix = ''.join(f'[a{i}]' for i in range(len(linies)))
    filtres.append(f'{mix}amix=inputs={len(linies)}:normalize=0,loudnorm=I=-16:TP=-1.5,apad,atrim=0:{total}[sortida]')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *ent, '-filter_complex', ';'.join(filtres),
                    '-map', '[sortida]', '-ac', '2', '-c:a', 'aac', '-b:a', '160k', os.path.join(DIR, 'veu', 'veu.m4a')], check=True)
    with open(os.path.join(DIR, 'escenes.js'), 'w') as f:
        f.write('// Generat per docs/demo/eines/munta_app.py: no ho editis a mà.\n')
        f.write(f'window.DURADA = {total};\n')
        f.write('window.ESCENES = ' + json.dumps(ESCENES, ensure_ascii=False, indent=1) + ';\n')
    for e in ESCENES:
        print(f"{e['ini']:6.2f}–{e['fi']:6.2f}  {(e.get('img') or (e.get('carta') or {}).get('h1') or 'assistent')[:38]:38}  {e.get('veu', '')[:70]}")
    print('durada total:', total, 's')


if __name__ == '__main__':
    main()
