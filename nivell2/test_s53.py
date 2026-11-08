"""Contracte del lliurament i selecció d'escenaris, amb dades inventades."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from nivell2.base import CONTINGENCIES, GRAU_NOU, Informe, Proposta
from nivell2.reparacio import Reparacio
from nivell2.test_reparacio import base as base_sense_reserva, sessio, DATE
from nivell2 import comprova_persones, s53
from nivell2.imprevistos import ORDRE, TEMPS_REPARACIO
from horaris.model import Aula, Tancament


def base(*rows):
    b = base_sense_reserva(*rows)
    for room in ('Q9/0098', 'Q9/0099'):
        b.aules[room] = Aula(room, 'Q9', 'Aules docents', 30)
    return b


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
    assert summary['reserva_minima_operativa'] == 2
    assert summary['classes_suport'] == 0
    assert summary['estat_solver'] == 'OPTIMAL'
    assert ORDRE in (out/'5.3'/'README.md').read_text()
    assert summary['relaxacions_per_motiu'][0]['sessions'] == 1
    assert 'identificador-inventat-privat' not in json.dumps(summary)
    stdout = capsys.readouterr().out
    assert 'identificador-inventat-privat' not in stdout and 'Q9/' not in stdout


@pytest.mark.parametrize('failure', ['sense_proposta', 'invalida', 'excepcio', 'reserva',
                                     'feasible'])
def test_reparacio_fallida_conserva_lliurament_sencer(tmp_path, failure):
    b = base(sessio('inventada'))
    if failure == 'reserva':
        b.tancaments = [Tancament('Q9/0098', DATE, DATE)]
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
    state = 'FEASIBLE' if failure == 'feasible' else 'OPTIMAL'
    result = Reparacio(None if failure == 'sense_proposta' else Proposta.de_base(b), state, {
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


@pytest.mark.parametrize('canvis_anteriors', [None, 65, 66, 64])
def test_canvis_superiors_a_64_depenen_nomes_de_la_proposta_anterior(tmp_path, capsys, canvis_anteriors):
    import datetime as dt
    b = base(*(sessio(f'inventada-{i}', data=DATE+dt.timedelta(weeks=i)) for i in range(66)))
    out = tmp_path/'resultats'
    reference = Proposta.de_base(b)
    reference.escriu(out/'5.2'/'proposta.csv')
    s53.escriu_csv(out/'5.2'/'relaxacions.csv', [], ['restriccio', 'sessions', 'justificacio'])
    if canvis_anteriors is not None:
        previous = Proposta.de_base(b)
        for i in range(canvis_anteriors):
            previous.files[f'inventada-{i}'].aula = 'Q9/0002'
        previous.escriu(out/'5.3'/'proposta.csv')
        (out/'5.3'/'resum.json').write_text('resum anterior')
        frozen = {p.name: p.read_bytes() for p in (out/'5.3').iterdir()}
    proposal = Proposta.de_base(b)
    for i in range(65):
        proposal.files[f'inventada-{i}'].aula = 'Q9/0002'
    result = Reparacio(proposal, 'OPTIMAL', {'sessions_afectades': 0,
        'sessions_afectades_per_imprevist': {}, 'sessions_obertes': 65, 'intents': [],
        'canvis_franja_vs_referencia': 0, 'canvis_aula_vs_referencia': 65})
    report = Informe({'veredicte': 'VALIDA', 'restriccions': {}, 'objectius': {
        'canvis_franja_vs_referencia': 0, 'canvis_aula_vs_referencia': 65}}, '')
    blocked = canvis_anteriors is not None and canvis_anteriors < 65
    with patch.object(s53, 'RESULTATS', out), patch.object(s53, 'carrega_model', return_value=b), \
         patch.object(s53, 'repara', return_value=result), patch.object(s53, 'verifica', return_value=report):
        assert s53.main([]) == int(blocked)
    if blocked:
        assert {p.name: p.read_bytes() for p in (out/'5.3').iterdir()} == frozen
        assert 'regressió' in capsys.readouterr().out
    else:
        summary = json.loads((out/'5.3'/'resum.json').read_text())
        assert 'comparacio_anterior' not in summary
        execution = json.loads((out/'5.3'/'execucio.json').read_text())
        assert ('comparacio_anterior' in execution) == (canvis_anteriors is not None)
        assert summary['canvis_aula_vs_referencia'] == 65
        assert summary['reserva_minima_operativa'] == 2
        assert summary['estat_solver'] == 'OPTIMAL'
        readme = (out/'5.3'/'README.md').read_text()
        assert "màxim 64" not in readme
        assert 'La publicació exigeix OPTIMAL.' in readme


@pytest.mark.parametrize('canvi, reserva_anterior, reserva_nova, bloqueja', [
    ({'canvis_aula_vs_referencia': 1}, 2, 2, True),
    ({'canvis_franja_vs_referencia': 1}, 2, 2, True),
    ({'canvis_aula_vs_referencia': 1}, 3, 2, True),
    ({'canvis_aula_vs_referencia': 1}, 2, 3, False),
    ({'canvis_aula_vs_referencia': 0}, 2, 2, False),
    ({'canvis_aula_vs_referencia': -1}, 2, 2, False),
    ({'canvis_aula_vs_referencia': -1, 'canvis_franja_vs_referencia': 1}, 2, 2, False),
])
def test_regressio_compara_suma_oficial_i_reserva(canvi, reserva_anterior, reserva_nova, bloqueja):
    old = {'canvis_franja_vs_referencia': 1, 'canvis_aula_vs_referencia': 5,
           'reserva_minima_operativa': reserva_anterior}
    new = dict(old, reserva_minima_operativa=reserva_nova)
    for key, increment in canvi.items():
        new[key] += increment
    assert s53.regressio_oficial(old, new) is bloqueja


@pytest.mark.parametrize('millora_reserva', [False, True])
def test_publicacio_protegeix_anterior_si_empitjoren_canvis(tmp_path, capsys, millora_reserva):
    b = base(sessio('inventada', aula='Q9/0098' if millora_reserva else 'Q9/0001'))
    out = tmp_path/'resultats'
    ref = Proposta.de_base(b)
    ref.escriu(out/'5.2'/'proposta.csv')
    s53.escriu_csv(out/'5.2'/'relaxacions.csv', [], ['restriccio', 'sessions', 'justificacio'])
    ref.escriu(out/'5.3'/'proposta.csv')
    (out/'5.3'/'resum.json').write_text('resum anterior')
    frozen = {p.name: p.read_bytes() for p in (out/'5.3').iterdir()}
    proposal = Proposta.de_base(b)
    proposal.files['inventada'].aula = 'Q9/0002'
    result = Reparacio(proposal, 'OPTIMAL', {'sessions_afectades': 0,
        'sessions_afectades_per_imprevist': {}, 'sessions_obertes': 1, 'intents': [],
        'canvis_franja_vs_referencia': 0, 'canvis_aula_vs_referencia': 1})
    report = Informe({'veredicte': 'VALIDA', 'restriccions': {}, 'objectius': {
        'canvis_franja_vs_referencia': 0, 'canvis_aula_vs_referencia': 1}}, '')
    with patch.object(s53, 'RESULTATS', out), patch.object(s53, 'carrega_model', return_value=b), \
         patch.object(s53, 'repara', return_value=result), patch.object(s53, 'verifica', return_value=report):
        assert s53.main([]) == (0 if millora_reserva else 1)
    if millora_reserva:
        assert (out/'5.3'/'proposta.csv').read_bytes() != frozen['proposta.csv']
        assert json.loads((out/'5.3'/'resum.json').read_text())['reserva_minima_operativa'] == 2
    else:
        assert {p.name: p.read_bytes() for p in (out/'5.3').iterdir()} == frozen
        stdout = capsys.readouterr().out
        assert 'regressió' in stdout
        assert 'Canvis oficials (franja + aula): 0 → 1' in stdout
        assert 'Reserva mínima operativa: 2 → 2' in stdout
        assert 'inventada' not in stdout and 'Q9/' not in stdout


def test_auditoria_independent_detecta_una_sola_aula_operativa_lliure():
    b = base(sessio('inventada', aula='Q9/0098', ini=900, durada=30),
             sessio('compartida', aula='Q9/0098', ini=930, durada=30))
    b.aules['Q9/0097'] = Aula('Q9/0097', 'Q9', 'Aules docents', 30)
    b.tancaments = [Tancament('Q9/0097', DATE, DATE)]
    minimum, deficits = s53.comprova_reserva_operativa(b, Proposta.de_base(b))
    assert minimum == 1
    deficit = next(d for d in deficits if d['franja'] == 870)
    assert deficit['data'] == DATE
    assert deficit['lliures'] == ['Q9/0099']
    assert deficit['tancades'] == ['Q9/0097']
    assert deficit['ocupades'] == ['Q9/0098']


def test_auditoria_tancament_parcial_i_data_recuperada():
    import datetime as dt
    tomorrow = DATE+dt.timedelta(days=1)
    b = base(sessio('recuperada', aula='Q9/0098', ini=870, durada=60))
    b.aules['Q9/0097'] = Aula('Q9/0097', 'Q9', 'Aules docents', 30)
    b.tancaments = [Tancament('Q9/0097', tomorrow, tomorrow, 900, 930)]
    proposta = Proposta.de_base(b)
    proposta.files['recuperada'].data = tomorrow.isoformat()
    proposta.files['recuperada'].dia = 'M'
    minimum, deficits = s53.comprova_reserva_operativa(b, proposta)
    assert minimum == 1
    assert [(d['data'], d['franja']) for d in deficits] == [(tomorrow, 870)]


def test_determinisme_compara_csv_i_no_publica_si_difereixen(tmp_path):
    out = tmp_path/'resultats'
    (out/'5.3').mkdir(parents=True)
    (out/'5.3'/'proposta.csv').write_bytes(b'anterior')
    counter = 0

    def genera(args, stage, start):
        nonlocal counter
        assert args.temps == TEMPS_REPARACIO
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
