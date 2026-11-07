"""Contracte i errors de lliurament amb fitxers inventats."""
import csv
import json
import shlex
from pathlib import Path
from types import SimpleNamespace
import zipfile
from unittest.mock import patch

import pytest

from nivell2 import empaqueta, verificacio
from nivell2.base import Informe, CONTINGENCIES, GRAU_NOU
from nivell2.readmes import normalitza


def prepara(root):
    for q in verificacio.OPCIONS:
        out = root/q
        out.mkdir(parents=True)
        for name in empaqueta.OBLIGATORIS:
            (out/name).write_text('inventat\n')
        (out/'xifres.csv').write_text('xifra,abans,despres\nsessions,1,1\n')
        (out/'README.md').write_text(f'python -m nivell2.s{q.replace(".", "")} --temps 10 --llavor 0\n{verificacio.ordre(q)}\n{verificacio.ordre_oficial(q, root)}\n')


def test_opcions_compartides(tmp_path):
    prepara(tmp_path)
    for q in verificacio.OPCIONS:
        (tmp_path/q/'relaxacions.csv').write_text('restriccio,sessions,justificacio\n')
        with patch.object(verificacio, 'verifica') as verify:
            verificacio.verifica_pregunta(q, tmp_path)
        kw = verify.call_args.kwargs
        assert kw.get('nomes_aules', False) == (q == '5.1')
        assert kw.get('escenari') == {'5.3': CONTINGENCIES, '5.4': GRAU_NOU}.get(q)
        assert kw.get('referencia') == (tmp_path/'5.2/proposta.csv' if q == '5.3' else None)
        assert kw['relaxacions'] == tmp_path/q/'relaxacions.csv'
        assert verificacio.ordre(q) in (tmp_path/q/'README.md').read_text()


@pytest.mark.parametrize('sense_zip', [False, True])
def test_empaquetat(tmp_path, sense_zip):
    root, output = tmp_path/'font', tmp_path/'sortida'
    prepara(root)
    report = Informe({'veredicte': 'VALIDA AMB RELAXACIONS DECLARADES', 'restriccions': {}}, '')
    with patch.object(empaqueta, 'comprova_persones', return_value=True) as people, \
         patch.object(empaqueta, 'verifica_pregunta', return_value=report) as verify:
        assert empaqueta.empaqueta(output, arrel=root, sense_zip=sense_zip) == 0
        assert verify.call_count == 4
        people.assert_called_once_with(resultats=root)
    archive = output/'lliurament-nivell2.zip'
    assert archive.exists() != sense_zip
    if not sense_zip:
        with zipfile.ZipFile(archive) as z:
            assert len(z.namelist()) == 20


@pytest.mark.parametrize('failure', ['veredicte', 'contracte', 'error', 'persones'])
def test_cap_zip_si_falla(tmp_path, failure):
    root, output = tmp_path/'font', tmp_path/'sortida'
    prepara(root)
    output.mkdir()
    (output/'lliurament-nivell2.zip').write_text('vell')
    if failure == 'contracte':
        (root/'5.1/xifres.csv').unlink()
    report = Informe({'veredicte': 'NO VALIDA' if failure == 'veredicte' else 'VALIDA', 'restriccions': {}}, '')
    with patch.object(empaqueta, 'comprova_persones', return_value=failure != 'persones'), \
         patch.object(empaqueta, 'verifica_pregunta', return_value=report,
                      side_effect=RuntimeError('privat') if failure == 'error' else None):
        assert empaqueta.empaqueta(output, arrel=root) == 1
    assert not (output/'lliurament-nivell2.zip').exists()


@pytest.mark.parametrize('q', verificacio.OPCIONS)
def test_readme_relatiu(q):
    original = '''Llavor: 7. Temps total: 42 s. Veredicte: VALIDA.
```sh
/Users/antic/.venv/bin/python -m nivell2.s51 --temps 60 --llavor 7
```
```sh
cd /Users/antic/repte
python -m horaris check /Users/antic/resultats/proposta.csv
```
| indicador | 1 | 2 |
'''
    text = normalitza(original, q)
    assert normalitza(text, q) == text
    assert verificacio.ordre_oficial(q) in text
    assert '/Users/' not in text
    assert verificacio.ordre(q) in text
    assert 'Llavor: 7. Temps total: 42 s.' in text
    assert '| indicador | 1 | 2 |' in text


def test_xifres_51(tmp_path):
    from nivell2.comprova import escriu_csv
    from nivell2.test_xifres import base_petita
    from nivell2.base import Proposta
    from nivell2.xifres import compara
    b = base_petita()
    report = Informe({'veredicte': 'VALIDA', 'restriccions': {}, 'objectius': {}}, '')
    with patch('nivell2.xifres.verifica', return_value=report), \
         patch('nivell2.xifres.carrega_oficial', return_value=b):
        comparison = compara(Proposta.de_base(b), b, nomes_aules=True)
    path = tmp_path/'xifres.csv'
    escriu_csv(path, comparison.files)
    with path.open() as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ['xifra', 'abans', 'despres']
        assert all(r['abans'] == r['despres'] for r in reader)


@pytest.mark.parametrize('q', verificacio.OPCIONS)
@pytest.mark.parametrize('relaxacions', [False, True])
def test_ordre_readme_es_la_que_executa_verificacio(tmp_path, q, relaxacions):
    from nivell2 import base
    root = tmp_path/'resultats/nivell2'
    prepara(root)
    if relaxacions:
        (root/q/'relaxacions.csv').write_text('restriccio,sessions,justificacio\n')
    readme = normalitza('```sh\npython -m nivell2.verificacio ' + q + '\n```', q, root)
    command = verificacio.ordre_oficial(q, root)
    assert command in readme
    documented = shlex.split(command.splitlines()[1])
    path_flags = {'--json', '--violacions', '--referencia', '--relaxacions', '--escenari'}
    virtual_cwd = tmp_path/'repte/repte-horaris-escola'
    for i, token in enumerate(documented):
        if i == 4 or (i and documented[i-1] in path_flags):
            cwd = base.REPTE if documented[i-1] == '--escenari' else virtual_cwd
            documented[i] = str((cwd/token).resolve())
    def official(cmd, **kwargs):
        Path(cmd[cmd.index('--json')+1]).write_text(json.dumps({
            'veredicte': 'VALIDA', 'restriccions': {}, 'objectius': {}}))
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    with patch.object(base.subprocess, 'run', side_effect=official) as run:
        verificacio.verifica_pregunta(q, root)
    assert run.call_args.args[0][1:] == documented[1:]
    assert run.call_args.kwargs['cwd'] == base.REPTE


def test_persones_resultats_explicit(tmp_path):
    from nivell2.comprova_persones import escenaris
    prepara(tmp_path)
    scenarios = list(escenaris(tmp_path))
    assert {name for name, _, _ in scenarios} == {'avui', *verificacio.OPCIONS}
    assert all(path.parent.parent == tmp_path for _, path, _ in scenarios if path)
