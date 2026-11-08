"""Normalitza instruccions sense modificar els resultats documentats."""
import re
from nivell2.verificacio import OPCIONS, ordre, ordre_oficial
from nivell2.base import RESULTATS


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
    text = re.sub(r'/Users/[^\s`\"\']*', '.', text)
    return text.replace('des del worktree', 'des de l’arrel del repositori').replace('Des del worktree', 'Des de l’arrel del repositori')


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
