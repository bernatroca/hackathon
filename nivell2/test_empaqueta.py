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
        assert kw.get('referencia') == (tmp_path/'5.2/proposta.csv' if q in ('5.3', '5.4') else None)
        assert kw['relaxacions'] == tmp_path/q/'relaxacions.csv'
        assert verificacio.ordre(q) in (tmp_path/q/'README.md').read_text()


@pytest.mark.parametrize('sense_zip', [False, True])
def test_empaquetat(tmp_path, sense_zip):
    root, output = tmp_path/'font', tmp_path/'sortida'
    prepara(root)
    (output/'graelles').mkdir(parents=True)
    (output/'graelles/index.html').write_text('<a href="aula-000.html">A</a>')
    (output/'graelles/aula-000.html').write_text('<!doctype html><title>A</title>')
    report = Informe({'veredicte': 'VALIDA AMB RELAXACIONS DECLARADES', 'restriccions': {}}, '')
    with patch.object(empaqueta, 'genera'), \
         patch.object(empaqueta, 'graelles', return_value=output/'graelles'), \
         patch.object(empaqueta, 'comprova_persones', return_value=True) as people, \
         patch.object(empaqueta, 'verifica_pregunta', return_value=report) as verify:
        assert empaqueta.empaqueta(output, arrel=root, sense_zip=sense_zip) == 0
        assert verify.call_count == 4
        people.assert_called_once_with(resultats=root)
    archive = output/'lliurament-nivell2.zip'
    assert archive.exists() != sense_zip
    if not sense_zip:
        with zipfile.ZipFile(archive) as z:
            assert len(z.namelist()) == 22
            assert 'graelles/index.html' in z.namelist()
            assert 'graelles/aula-000.html' in z.namelist()


@pytest.mark.parametrize('failure', ['veredicte', 'contracte', 'error', 'persones'])
def test_cap_zip_si_falla(tmp_path, failure):
    root, output = tmp_path/'font', tmp_path/'sortida'
    prepara(root)
    output.mkdir()
    (output/'lliurament-nivell2.zip').write_text('vell')
    if failure == 'contracte':
        (root/'5.1/xifres.csv').unlink()
    report = Informe({'veredicte': 'NO VALIDA' if failure == 'veredicte' else 'VALIDA', 'restriccions': {}}, '')
    with patch.object(empaqueta, 'genera'), \
         patch.object(empaqueta, 'graelles', return_value=output/'graelles'), \
         patch.object(empaqueta, 'comprova_persones', return_value=failure != 'persones'), \
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
    (root/q/'proposta.csv').write_text('id_sessio,dia,h_ini,aula\n')
    def official(cmd, **kwargs):
        import hashlib
        Path(cmd[cmd.index('--json')+1]).write_text(json.dumps({
            'veredicte': 'VALIDA', 'restriccions': {}, 'objectius': {},
            'context': {'proposta_sha256': hashlib.sha256((root/q/'proposta.csv').read_bytes()).hexdigest()}}))
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


@pytest.mark.parametrize('code', [-9, 2, 3, 0, 1])
def test_rebutja_informe_antic(tmp_path, code):
    from nivell2 import base
    proposal = tmp_path/'p.csv'
    proposal.write_text('id_sessio,dia,h_ini,aula\n')
    report = tmp_path/'informe.json'
    report.write_text('{"veredicte":"VALIDA"}')
    with patch.object(base.subprocess, 'run', return_value=SimpleNamespace(returncode=code)):
        with pytest.raises(RuntimeError):
            base.verifica(proposal, json_path=report)
    assert not report.exists()


@pytest.mark.parametrize('digest,verdict,code,ok', [
    ('correcte', 'VALIDA', 0, True),
    ('correcte', 'NO VALIDA', 1, True),
    ('fals', 'VALIDA', 0, False),
    ('correcte', 'VALIDA', 1, False),
])
def test_empremta_i_codi(tmp_path, digest, verdict, code, ok):
    import hashlib
    from nivell2 import base
    proposal = tmp_path/'p.csv'
    proposal.write_text('id_sessio,dia,h_ini,aula\n')
    def run(cmd, **kwargs):
        value = hashlib.sha256(proposal.read_bytes()).hexdigest() if digest == 'correcte' else digest
        Path(cmd[cmd.index('--json')+1]).write_text(json.dumps({
            'veredicte': verdict, 'context': {'proposta_sha256': value}}))
        return SimpleNamespace(returncode=code, stdout='')
    with patch.object(base.subprocess, 'run', side_effect=run):
        if ok:
            assert base.verifica(proposal).veredicte == verdict
        else:
            with pytest.raises(RuntimeError):
                base.verifica(proposal)


def test_graelles_autonomes(tmp_path):
    from nivell2 import xifres_lliurament as delivery
    from nivell2.test_xifres import base_petita
    from nivell2.base import Proposta
    b = base_petita()
    b.aules = {'A': object(), 'B': object()}
    (tmp_path/'5.4').mkdir()
    Proposta.de_base(b).escriu(tmp_path/'5.4/proposta.csv')
    with patch.object(delivery, 'carrega_oficial', return_value=b):
        folder = delivery.graelles(tmp_path/'sortida', tmp_path)
    assert len(list(folder.glob('*.html'))) == 3
    index = (folder/'index.html').read_text()
    assert 'aula-000.html' in index and 'aula-001.html' in index
    assert '<!doctype html>' in (folder/'aula-000.html').read_text()


def test_xifres_referencia_real(tmp_path):
    from nivell2.test_xifres import base_petita
    from nivell2.base import Proposta
    from nivell2.xifres import compara
    b = base_petita()
    ref = Proposta.de_base(b)
    ref.files['0'].h_ini = '09:00'
    refpath = ref.escriu(tmp_path/'proposta.csv')
    proposal = Proposta.de_base(b)
    proposal.files['0'].h_ini = '09:00'
    proposal.files['1'].aula = 'B'
    report = Informe({'veredicte': 'VALIDA', 'restriccions': {
        'R1': {'compten': 0, 'heretades': 2, 'declarades': 3}},
        'incompliments_declarats': 3, 'objectius': {}}, '')
    with patch('nivell2.xifres.carrega_oficial', return_value=b), \
         patch('nivell2.xifres.verifica', return_value=report):
        result = compara(proposal, b, referencia=refpath)
    rows = {r['xifra']: r for r in result.files}
    assert rows['sessions_canvien_hora']['despres'] == 0
    assert rows['sessions_nomes_canvien_aula']['despres'] == 1
    assert rows['incompliments_declarats']['despres'] == 3
    assert rows['incompliments_heretats']['despres'] == 2


@pytest.mark.parametrize('verification', [
    'python -m nivell2.verificacio 5.2',
    'python -m horaris check proposta.csv \\\n  --semestre 2',
])
def test_normalitza_bloc_mixt(verification):
    generation = 'python -m nivell2.s52 --temps-franges 300 --temps-aules 600 --llavor 0'
    people = 'RESULTATS_DIR=$PWD/resultats/nivell2 python -m nivell2.comprova_persones'
    original = f'```sh\n{generation}\n{verification}\n{people}\n```\n'
    result = normalitza(original, '5.2')
    assert generation in result
    assert people in result
    assert normalitza(result, '5.2') == result
    assert result.count(verificacio.ordre('5.2')) == 1


def test_conserva_explicacions_nomes_si_xifra_igual(tmp_path):
    from nivell2 import xifres_lliurament as delivery
    out = tmp_path/'5.2'
    out.mkdir()
    path = out/'README.md'
    path.write_text('## Què empitjora i per què\n\n'
                    '- hores_mortes_min: 1 → 2; Explicació conservada.\n'
                    '- canvis_aula: 0 → 1; Explicació antiga.\n')
    comparison = SimpleNamespace(files=[
        {'xifra': 'hores_mortes_min', 'abans': 1, 'despres': 2},
        {'xifra': 'canvis_aula', 'abans': 0, 'despres': 3}])
    with patch.object(delivery.Proposta, 'llegeix'), patch.object(delivery, 'compara', return_value=comparison):
        delivery.genera('5.2', tmp_path)
        first = path.read_text()
        delivery.genera('5.2', tmp_path)
    assert path.read_text() == first
    assert 'Explicació conservada.' in first
    assert 'Explicació antiga.' not in first
    assert '- canvis_aula: 0 → 3; per explicar.' in first


def test_seccio_comptatge_idempotent():
    from nivell2.readmes import explica_comptatge
    x = dict(simultanis_proposta=3, simultanis_partida=4, te_oficial=2,
             te_sense_dobles=5, te_partida=6, te_partida_sense_dobles=7, aula_csv=7, aula_oficial=6)
    for q in verificacio.OPCIONS:
        text = explica_comptatge(normalitza('Introducció\n\n## Final\n\nText.\n', q), x, q)
        assert text.count('## Com compta el verificador') == 1
        assert explica_comptatge(text, x, q) == text
        abans = 'referència 5.2' if q in ('5.3', '5.4') else 'partida'
        assert f'3 casos a la proposta i 4 a la {abans}' in text
        assert f'({abans} → proposta)' in text
        assert 'Aules extra de teoria per grup» (`r6_aules_te_extra_per_grup`)' in text
        assert '`aules_extra_teoria`' not in text
        assert '6 → 2 segons el verificador, i 7 → 5' in text
        assert ('7 canvis d’aula' in text) == (q == '5.3')
        assert '## Final\n\nText.' in text
        assert explica_comptatge(normalitza(text, q), x, q) == normalitza(text, q)


@pytest.mark.parametrize('q', verificacio.OPCIONS)
def test_comptatge_independent_i_readme(q):
    """Contrasta només recomptes; no mostra sessions ni identificadors."""
    from collections import defaultdict
    from horaris.check import Informe as Intern, _col_loca
    from nivell2.base import RESULTATS, Proposta, carrega_oficial
    from nivell2.xifres_lliurament import comptatge_verificador
    from nivell2.readmes import explica_comptatge
    options = verificacio.opcions_pregunta(q, RESULTATS)
    b = carrega_oficial(options.get('escenari'))
    p = Proposta.llegeix(RESULTATS/q/'proposta.csv')
    ref = (Proposta.llegeix(options['referencia']) if 'referencia' in options
           else Proposta.de_base(carrega_oficial()))
    col = _col_loca(b, p.a_files(), Intern())

    def independent(placements):
        # Construeix cada agenda directament des de les claus de subgrup.
        keys = {(coh, c.s.linia, c.data) for c in placements.values() for coh in c.s.cohorts}
        count = 0
        for coh, lin, day in keys:
            cs = [c for c in placements.values() if coh in c.s.cohorts and c.s.linia == lin and c.data == day]
            groups = {c.s.num_grup for c in cs if c.s.tipus != 'TE'} or {None}
            for group in groups:
                ordered = sorted([c for c in cs if c.s.tipus == 'TE'] +
                                 [c for c in cs if c.s.tipus != 'TE' and c.s.num_grup == group], key=lambda c: c.ini)
                count += sum(bool(a.aula and z.aula) and a.aula != z.aula and a.ini == z.ini
                             for a, z in zip(ordered, ordered[1:]))
        return count

    x = comptatge_verificador(q, RESULTATS)
    assert x['simultanis_proposta'] == independent(col)
    start = _col_loca(carrega_oficial(), ref.a_files(), Intern())
    assert x['simultanis_partida'] == independent(start)
    for exclude, key in ((False, 'te_oficial'), (True, 'te_sense_dobles')):
        rooms = defaultdict(set)
        for c in col.values():
            if c.s.tipus == 'TE' and c.aula and not (exclude and c.s.sense_espai):
                for coh in c.s.cohorts:
                    rooms[coh, c.s.linia].add(c.aula)
        assert x[key] == sum(len(v)-1 for v in rooms.values())
        rooms.clear()
        for c in start.values():
            if c.s.tipus == 'TE' and c.aula and not (exclude and c.s.sense_espai):
                for coh in c.s.cohorts:
                    rooms[coh, c.s.linia].add(c.aula)
        assert x['te_partida_sense_dobles' if exclude else 'te_partida'] == sum(len(v)-1 for v in rooms.values())
    if q == '5.3':
        assert x['aula_csv'] == sum(p.files[s].aula != ref.files[s].aula for s in p.files.keys() & ref.files.keys())
        placed_ref = _col_loca(b, ref.a_files(), Intern())
        assert x['aula_oficial'] == sum(col[s].aula != placed_ref[s].aula for s in col.keys() & placed_ref.keys())
    if q == '5.1':
        assert (x['te_partida_sense_dobles'], x['te_sense_dobles']) == (8, 9)
    text = (RESULTATS/q/'README.md').read_text()
    assert '## Com compta el verificador' in text
    assert explica_comptatge(text, x, q).split('## Com compta el verificador')[1].strip() == text.split('## Com compta el verificador')[1].split('\n## ')[0].strip()
