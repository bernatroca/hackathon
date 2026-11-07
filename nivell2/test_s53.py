"""Contracte del lliurament i selecció d'escenaris, amb dades inventades."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from nivell2.base import CONTINGENCIES, GRAU_NOU, Informe, Proposta
from nivell2.reparacio import Reparacio
from nivell2.test_reparacio import base, sessio
from nivell2 import comprova_persones, s53


def test_escenari_53_carrega_contingencies(tmp_path):
    for name in ('5.2', '5.3', '5.4'):
        directory = tmp_path/name
        directory.mkdir()
        (directory/'proposta.csv').write_text('id_sessio,dia,h_ini,aula\n')
    with patch.object(comprova_persones, 'RESULTATS_PRINCIPAL', tmp_path):
        scenarios = {n: e for n, _, e in comprova_persones.escenaris()}
    assert scenarios == {'avui': None, '5.2': None, '5.3': CONTINGENCIES, '5.4': GRAU_NOU}


def test_lliura_referencia_relaxacions_i_sortida_només_recomptes(tmp_path, capsys):
    b = base(sessio('identificador-inventat-privat'))
    principal, out = tmp_path/'principal', tmp_path/'local'
    (principal/'5.2').mkdir(parents=True)
    ref = Proposta.de_base(b)
    path = ref.escriu(principal/'5.2'/'proposta.csv')
    s53.escriu_csv(path.parent/'relaxacions.csv', [
        {'restriccio': 'R1-TORN', 'sessions': 'identificador-inventat-privat',
         'justificacio': 'Motiu heretat inventat: diagnostic.md'}], ['restriccio', 'sessions', 'justificacio'])
    frozen_relax = (path.parent/'relaxacions.csv').read_bytes()
    frozen = path.read_bytes()
    result = Reparacio(ref, 'OPTIMAL', {'sessions_afectades': 1,
        'sessions_afectades_per_imprevist': {'recuperacio': 1}, 'sessions_obertes': 1,
        'intents': [], 'canvis_franja_vs_referencia': 1, 'canvis_aula_vs_referencia': 0})
    report = Informe({'veredicte': 'VALIDA AMB RELAXACIONS DECLARADES', 'restriccions': {},
                      'objectius': {'canvis_franja_vs_referencia': 1, 'canvis_aula_vs_referencia': 0}}, '')
    with patch.object(s53, 'RESULTATS', out), patch.object(s53, 'RESULTATS_PRINCIPAL', principal), \
         patch.object(s53, 'carrega_model', return_value=b), \
         patch.object(s53, 'repara', return_value=result), patch.object(s53, 'verifica', return_value=report) as verify:
        assert s53.main([]) == 0
    assert verify.call_args.kwargs['escenari'] == CONTINGENCIES
    assert verify.call_args.kwargs['referencia'] == path
    assert path.read_bytes() == frozen
    assert (path.parent/'relaxacions.csv').read_bytes() == frozen_relax
    assert (out/'5.3'/'relaxacions.csv').read_bytes() == frozen_relax.replace(
        b'diagnostic.md', b'../5.2/diagnostic.md')
    summary = json.loads((out/'5.3'/'resum.json').read_text())
    assert summary['incompliments_no_declarats'] == 0
    assert summary['relaxacions_per_motiu'][0]['sessions'] == 1
    assert 'identificador-inventat-privat' not in json.dumps(summary)
    stdout = capsys.readouterr().out
    assert 'identificador-inventat-privat' not in stdout and 'Q9/' not in stdout


@pytest.mark.parametrize('failure', ['sense_proposta', 'invalida', 'excepcio'])
def test_reparacio_fallida_conserva_lliurament_sencer(tmp_path, failure):
    b = base(sessio('inventada'))
    principal = tmp_path/'principal'
    path = Proposta.de_base(b).escriu(principal/'5.2'/'proposta.csv')
    s53.escriu_csv(path.parent/'relaxacions.csv', [], ['restriccio', 'sessions', 'justificacio'])
    out = tmp_path/'resultats'
    previous = out/'5.3'
    previous.mkdir(parents=True)
    expected = {'proposta.csv': b'csv anterior', 'informe.json': b'informe anterior',
                'relaxacions.csv': b'relaxacions anteriors', 'resum.json': b'resum anterior'}
    for name, content in expected.items():
        (previous/name).write_bytes(content)
    good = Informe({'veredicte': 'VALIDA', 'restriccions': {},
                    'objectius': {'canvis_franja_vs_referencia': 0, 'canvis_aula_vs_referencia': 0}}, '')
    bad = Informe(dict(good.json, veredicte='NO VALIDA'), '')
    result = Reparacio(None if failure == 'sense_proposta' else Proposta.de_base(b), 'UNKNOWN', {
        'sessions_afectades': 1, 'sessions_afectades_per_imprevist': {}, 'sessions_obertes': 1,
        'intents': [], 'canvis_franja_vs_referencia': 0, 'canvis_aula_vs_referencia': 0})
    reports = [good, RuntimeError('fallada inventada')] if failure == 'excepcio' else [good, bad]
    with patch.object(s53, 'RESULTATS', out), patch.object(s53, 'RESULTATS_PRINCIPAL', principal), \
         patch.object(s53, 'carrega_model', return_value=b), patch.object(s53, 'repara', return_value=result), \
         patch.object(s53, 'verifica', side_effect=reports):
        if failure == 'excepcio':
            with pytest.raises(RuntimeError):
                s53.main([])
        else:
            assert s53.main([]) == 1
    assert {p.name: p.read_bytes() for p in previous.iterdir()} == expected
    assert sorted(p.name for p in out.iterdir()) == ['5.3']


def test_determinisme_compara_csv_i_no_publica_si_difereixen(tmp_path):
    out = tmp_path/'resultats'
    (out/'5.3').mkdir(parents=True)
    (out/'5.3'/'proposta.csv').write_bytes(b'anterior')
    counter = 0

    def genera(args, stage, start):
        nonlocal counter
        counter += 1
        stage.mkdir()
        (stage/'proposta.csv').write_text(str(counter))
        return 0

    with patch.object(s53, 'RESULTATS', out), patch.object(s53, '_genera', side_effect=genera):
        assert s53.main(['--comprova-determinisme']) == 1
    assert counter == 2
    assert (out/'5.3'/'proposta.csv').read_bytes() == b'anterior'


def test_publicacio_restaura_carpeta_si_falla_el_rename(tmp_path):
    out = tmp_path/'resultats'
    (out/'5.3').mkdir(parents=True)
    (out/'5.3'/'proposta.csv').write_bytes(b'anterior')
    rename = Path.rename

    def genera(args, stage, start):
        stage.mkdir()
        (stage/'proposta.csv').write_bytes(b'nova')
        return 0

    def falla(stage, destination):
        if stage.parent.name.startswith('.5.3-') and stage.name == '5.3':
            raise OSError('fallada inventada')
        return rename(stage, destination)

    with patch.object(s53, 'RESULTATS', out), patch.object(s53, '_genera', side_effect=genera), \
         patch.object(Path, 'rename', falla):
        with pytest.raises(OSError):
            s53.main([])
    assert (out/'5.3'/'proposta.csv').read_bytes() == b'anterior'
