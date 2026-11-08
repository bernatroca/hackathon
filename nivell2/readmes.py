"""Normalitza instruccions sense modificar els resultats documentats."""
import re
from nivell2.verificacio import OPCIONS, ordre, ordre_oficial
from nivell2.base import RESULTATS

PROVA_S04526 = '''## Prova de S04526

Prova documentada a l’auditoria D-5; no s’ha tornat a executar la reproducció.
El divendres 9/4/2027 és l’únic dia lectiu de la W14: del 5 al 8/4 és avaluació
i el verificador hi dona R2-CALENDARI. La sessió necessita aula d’informàtica.
Només n’hi ha dues, Q1/0007 i Q1/0019; totes dues estan ocupades de 15:00 a 19:00
per pràctiques fixades de GEI 1r (S15066, S15153, S15095 i S15124).
El docent D380 fa S04496, S04511 i S04526, de 60 minuts cadascuna i totes
d’informàtica. Només queden les 19:00 i les 20:00: hi caben dues sessions,
però no les tres sense solapar el docent. Per tant, almenys una ha de quedar
fora del torn de tarda. Es conserva S04526 al seu horari original.

Resultat del model registrat en la prova anterior: **R1 dura: INFEASIBLE**.
'''

NOTA_FIXADES = ('Les 458 sessions fixades declarades ja eren a la tarda. '
    'El verificador les compta perquè a la partida no tenien aula i la regla 5 obliga '
    'a posar-n’hi; sense aquesta declaració el veredicte és NO VALIDA.')

NOTA_GRAU_NOU = ('El grau nou hi cap a les seves franges originals: amb la regla oficial, '
    '0 sessions mogudes, segons la comprovació de l’auditoria D-10. N’hem mogut 41 '
    'per reduir 1.740 minuts d’hores mortes i per prudència amb els subgrups PAUL/91 '
    'i PAUL/92, que podrien compartir alumnes. El mínim demostrat pel model de l’equip '
    's’aplica a aquesta regla addicional; no és un mínim amb les regles oficials. '
    'El camp antic `minim_sessions_noves_fora_franja_demostrat` de `resum.json` '
    'té aquest mateix abast; les noves generacions el denominen '
    '`minim_sessions_noves_fora_franja_demostrat_amb_regla_equip`.')


def seccio(text, titol, contingut):
    text = re.sub(r'(?:\A|\n)## ' + re.escape(titol) + r'\n.*?(?=\n## |\Z)', '', text, flags=re.S)
    return text.rstrip() + '\n\n## ' + titol + '\n\n' + contingut.rstrip() + '\n'


def conserva_seccions(text, anterior):
    for titol in ('Com compta el verificador', 'Què empitjora i per què'):
        match = re.search(r'(?:\A|\n)## ' + re.escape(titol) + r'\n(.*?)(?=\n## |\Z)', anterior, flags=re.S)
        if match:
            text = seccio(text, titol, match[1].strip())
    return text


def documenta(pregunta, out, text):
    """Correccions documentals del lliurament, sense executar cap solver."""
    if pregunta == '5.2':
        diagnostic = out / 'diagnostic.md'
        anterior = diagnostic.read_text(encoding='utf-8') if diagnostic.exists() else '# Diagnòstic 5.2\n'
        diagnostic.write_text(seccio(anterior, 'Prova de S04526', PROVA_S04526.split('\n', 1)[1]), encoding='utf-8')
        text = text.replace('registra els intents i les proves R1', 'registra els intents')
        text = seccio(text, 'Justificació de les relaxacions',
                      NOTA_FIXADES + '\n\nLa prova de S04526 és a [diagnostic.md, «Prova de S04526»](diagnostic.md#prova-de-s04526).')
        text = re.sub(r'del (\d+[.,]\d+)\s*% de les sessions amb aula prèvia computable',
                      r'del \1 % de totes les sessions de la cohort', text)
        text = text.replace('sessions amb aula prèvia computable',
                            'sessions totals de la cohort (només el numerador exigeix aula prèvia computable)')
        text = seccio(text, 'Denominador dels canvis d’aula',
            'A GEQ,1r canvien d’aula 80 de 231 sessions (34,63 %), és a dir, totes les que ja '
            'tenien aula; les altres 151 no en tenien i ara se n’assignen. '
            'Els percentatges per cohort inclouen totes les seves sessions.')
    if pregunta == '5.4':
        text = text.replace('per encaixar el grau nou', 'per reduir esperes amb la regla addicional de l’equip')
        text = seccio(text, 'Abast de la regla d’alumnat', NOTA_GRAU_NOU)
    return text


def arrodoneix_text(text):
    """Arrodoneix les xifres del document, preservant les ordres exactes."""
    code = False
    lines = []
    for line in text.splitlines(keepends=True):
        if line.startswith('```'):
            code = not code
        elif not code:
            line = re.sub(r'(?<![\w.])(\d+\.\d{4,})(?![\w.])',
                          lambda m: f'{float(m[0]):.2f}'.replace('.', ','), line)
            if line.startswith('|'):
                line = re.sub(r'(?<=\|)(\s*)(\d+\.\d+)(\s*)(?=\|)',
                              lambda m: m[1] + f'{float(m[2]):.2f}'.replace('.', ',') + m[3], line)
        lines.append(line)
    return ''.join(lines)


def normalitza(text, pregunta, arrel=RESULTATS):
    def bloc(match):
        content = match.group(1)
        lines = content.splitlines(keepends=True)
        kept = []
        found = False
        continuation = False
        legacy_python = False
        for line in lines:
            verification = (continuation or legacy_python or
                            'nivell2.verificacio' in line or 'horaris check' in line or
                            ('verifica(' in line and 'GRAU_NOU' in content))
            if verification:
                found = True
                continuation = line.rstrip().endswith('\\')
                legacy_python = legacy_python and line.strip() not in ('PY', 'EOF')
                continue
            if 'python' in line and '<<' in line and 'verifica(' in content:
                legacy_python = True
                found = True
                continue
            if re.match(r'^\s*cd\s+', line) and ('horaris check' in content or 'nivell2.verificacio' in content):
                continue
            kept.append(line)
        if found:
            return ('```sh\n' + ''.join(kept).rstrip() +
                    ('\n' if ''.join(kept).strip() else '') + ordre(pregunta) +
                    '\n```\n\nOrdre oficial del jurat, des de l’arrel del repositori:\n```sh\n' +
                    ordre_oficial(pregunta, arrel) + '\n```')
        return match.group(0)
    text = re.sub(r'\n\nOrdre oficial del jurat, des de l’arrel del repositori:\n```sh\n.*?```', '', text, flags=re.S)
    text = re.sub(r'```sh\n(.*?)```', bloc, text, flags=re.S)
    if ordre(pregunta) not in text:
        text = text.rstrip() + '\n\n```sh\n' + ordre(pregunta) + '\n```\n\nOrdre oficial del jurat, des de l’arrel del repositori:\n```sh\n' + ordre_oficial(pregunta, arrel) + '\n```\n'
    text = re.sub(r'/[^\s`\"\']*/(?:python(?:3(?:\.\d+)?)?)\b', 'python', text)
    text = re.sub(r'/Users/[^\s`\"\']*/resultats/', 'resultats/', text)
    text = re.sub(r'/Users/[^\s`\"\']*', '', text)
    text = re.sub(r'`(?:\.)?`\s*:', ':', text)
    text = text.replace('repositori :', 'repositori:')
    text = text.replace('des del worktree', 'des de l’arrel del repositori').replace('Des del worktree', 'Des de l’arrel del repositori')
    return text.replace('repositori :', 'repositori:')


def actualitza(out, pregunta):
    path = out / 'README.md'
    path.write_text(normalitza(path.read_text(encoding='utf-8'), pregunta, out.parent), encoding='utf-8')


def explica_comptatge(text, xifres, pregunta):
    """Substitueix la secció generada, sense acumular còpies."""
    text = re.sub(r'(?:\A|\n)## Com compta el verificador\n.*?(?=\n## |\Z)', '', text, flags=re.S)
    abans = 'referència 5.2' if OPCIONS[pregunta].get('referencia') else 'partida'
    punts = [
        '- `desplacaments_aula` també compta el pas entre dues classes del mateix grup '
        'que comencen alhora i tenen aules diferents: '
        f"{xifres['simultanis_proposta']} casos a la proposta i {xifres['simultanis_partida']} a la {abans}.",
        '- L’indicador «Aules extra de teoria per grup» (`r6_aules_te_extra_per_grup`) inclou '
        'classes de dobles titulacions que no necessiten aula: '
        f"{xifres['te_partida']} → {xifres['te_oficial']} segons el verificador, i "
        f"{xifres['te_partida_sense_dobles']} → {xifres['te_sense_dobles']} sense aquestes classes ({abans} → proposta).",
    ]
    if pregunta == '5.3':
        punts.append('- El verificador no compta el canvi d’aula de la classe cancel·lada que es recupera, '
                     'perquè no figura a la referència col·locada: '
                     f"{xifres['aula_csv']} canvis d’aula comparant els CSV i {xifres['aula_oficial']} d’oficials.")
    return text.rstrip() + '\n\n## Com compta el verificador\n\n' + '\n'.join(punts) + '\n'
