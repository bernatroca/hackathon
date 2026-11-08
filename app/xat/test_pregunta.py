"""Terminal sense xarxa ni dades reals: la mateixa IA/eina falsa que al servidor."""
import json
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from xat import pregunta as p


@pytest.fixture
def falsa(monkeypatch):
    s = p.servidor
    monkeypatch.setattr(s, 'carrega_env', lambda *a: None)
    monkeypatch.setattr(s, 'proveidors', lambda: [{'nom': 'falsa', 'model': 'fals'}])
    executa = Mock(return_value={'ok': True, 'id_sessio': ['S90001'], 'resultat': {
        'total': 6, 'files': [{'aula': 'Q9/0001', 'capacitat': 90}]}})
    monkeypatch.setattr(s, '_eines', lambda: SimpleNamespace(executa=executa))
    historials = []
    def ia(proveidor, missatges):
        historials.append(list(missatges))
        if len(historials) == 1:
            yield 'tools', [{'id': 'call_1', 'function': {'name': 'aules_lliures',
                'arguments': json.dumps({'dia': 'M', 'hora_ini': '10:00', 'durada_min': 60, 'places_min': 0})}}]
        else:
            yield 'tros', 'Queden 6 aules, com Q9/0001 (90 places).'
        yield 'fi', {'model': 'fals', 'tallada': False}
    monkeypatch.setattr(s, '_trossos_api', ia)
    return executa, historials


def test_pregunta_ia_i_pantalla(falsa, capsys):
    assert p.main(['Quantes aules queden lliures dimarts a les 10?',
                   '--proposta', '5.2', '--setmana', 'típica']) == 0
    executa, historials = falsa
    text = capsys.readouterr().out
    assert text.startswith('Queden 6 aules, com Q9/0001 (90 places).')
    assert '\nConsultes:\naules_lliures ' in text
    assert 'S90001' in text and 'Q9/0001' in text
    assert '"hora_ini": "10:00"' in text
    pregunta = historials[0][1]['content']
    assert pregunta.startswith('<pantalla>\nProposta: 5.2. Setmana: típica\n</pantalla>')
    assert '<pantalla>' not in text
    executa.assert_called_once()


def test_sense_ia_una_eina(falsa, monkeypatch, capsys):
    executa, historials = falsa
    monkeypatch.setattr(p.servidor, 'carrega_env', lambda *a: pytest.fail('No necessita clau'))
    args = {'dia': 'M', 'hora_ini': '10:00', 'durada_min': 60, 'places_min': 0}
    assert p.main(['--sense-ia', '--eina', 'aules_lliures', '--args', json.dumps(args)]) == 0
    executa.assert_called_once_with('aules_lliures', args)
    assert historials == []
    text = capsys.readouterr().out
    assert '"total": 6' in text and 'S90001' in text and 'Q9/0001' in text


@pytest.mark.parametrize('args', [[], ['--sense-ia'],
    ['--sense-ia', '--eina', 'consulta_sql', '--args', '[]'],
    ['--sense-ia', '--eina', 'consulta_sql', '--args', '{'],
    ['Pregunta', '--eina', 'consulta_sql']])
def test_arguments_incorrectes(args):
    with pytest.raises(SystemExit) as exc:
        p.main(args)
    assert exc.value.code == 2


def test_errors_controlats(falsa, monkeypatch, capsys):
    monkeypatch.setattr(p.servidor, '_executa', lambda c: {'ok': False, 'error': 'Eina desconeguda.'})
    assert p.main(['--sense-ia', '--eina', 'inventada']) == 1
    assert 'Eina desconeguda.' in capsys.readouterr().out
    monkeypatch.setattr(p.servidor, 'falta', lambda: 'Falta configuració IA.')
    assert p.main(['Pregunta']) == 1
    assert 'Falta configuració IA.' in capsys.readouterr().err


def test_modul_des_de_arrel():
    resultat = subprocess.run([sys.executable, '-m', 'app.xat.pregunta', '--help'],
                              capture_output=True, text=True, check=False)
    assert resultat.returncode == 0, resultat.stderr
    assert '--sense-ia' in resultat.stdout
