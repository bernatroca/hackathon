"""Normalitza instruccions sense modificar els resultats documentats."""
import re
from nivell2.verificacio import ordre, ordre_oficial
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
