"""Proves amb sortides inventades: no executen verificadors ni consultes reals."""
import shlex
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest
from pagines import comprova as c


def test_llista_tancada_i_ordres():
    assert len(c.ORDRES) == 7
    for ordre in c.ORDRES:
        argv, cwd = c.prepara(ordre, 'Pregunta inventada')
        assert '--json' not in argv and '--violacions' not in argv
        with patch.object(c.subprocess, 'run', return_value=SimpleNamespace(stdout='VALIDA', stderr='', returncode=0)) as run:
            c.executa(ordre, 'Pregunta inventada')
        assert 'shell' not in run.call_args.kwargs
        assert run.call_args.kwargs['timeout'] == 180
        assert run.call_args.kwargs['env']['REPTE_DIR'] == str(c.REPTE)
        assert cwd == (c.ARREL if ordre.clau in ('assistent', 'xifres') else c.REPTE)
    ordres = {o.clau: c.prepara(o)[0] for o in c.ORDRES[:-1]}
    assert '--nomes-aules' in ordres['5.1']
    for clau in ('5.3', '5.4'):
        assert '--escenari' in ordres[clau] and '--referencia' in ordres[clau]


@pytest.mark.parametrize('pregunta', ['Quantes "aules"; echo sorpresa?', "Amb 'cometes' i ; dins"])
def test_pregunta_un_sol_argument(monkeypatch, pregunta):
    crides = []
    def run(argv, **kwargs):
        crides.append((argv, kwargs))
        return SimpleNamespace(stdout='Resposta inventada', stderr='', returncode=0)
    monkeypatch.setattr(c.subprocess, 'run', run)
    resultat = c.executa(c.ORDRES[-1], pregunta, '5.2')
    argv, kwargs = crides[0]
    assert argv[3] == pregunta
    assert argv == [str(c.PYTHON), '-m', 'app.xat.pregunta', pregunta,
                    '--proposta', '5.2', '--setmana', 'típica']
    assert shlex.split(resultat['ordre'])[3] == pregunta
    assert kwargs['capture_output'] and kwargs['text']


def test_pregunta_buida_no_executa():
    with patch.object(c.subprocess, 'run') as run:
        with pytest.raises(ValueError, match='Escriu una pregunta'):
            c.executa(c.ORDRES[-1], '  ')
        run.assert_not_called()


@pytest.mark.parametrize('error', [OSError('inventat'), subprocess.TimeoutExpired('inventat', 180)])
def test_errors_controlats(error):
    with patch.object(c.subprocess, 'run', side_effect=error):
        resultat = c.executa(c.ORDRES[0])
    assert resultat['error'] and resultat['codi'] is None


def pagina_inventada():
    from pagines.comprova import mostra
    mostra()


def test_renderitzat_i_persistencia():
    with patch.object(c.Path, 'is_file', return_value=False):
        at = AppTest.from_function(pagina_inventada).run()
        assert not at.exception
        assert len(at.button) == 7
        assert at.selectbox[0].value == '5.2'
        assert all(at.button[i].disabled for i in (1, 2, 3, 4, 6))
        with patch.object(c.subprocess, 'run', return_value=SimpleNamespace(stdout='VALIDA\nSortida inventada', stderr='', returncode=0)):
            at.button[0].click().run()
        assert not at.exception
        assert at.success[0].value == 'VALIDA'
        at.run()
        assert any('Sortida inventada' in bloc.value for bloc in at.code)
        assert not at.exception


def test_ordres_mostrees_portables():
    for ordre in c.ORDRES:
        cmd = c.ordre_terminal(ordre, 'Pregunta inventada')
        assert '/Users' not in cmd and '.venv' not in cmd
    assert c.ordre_terminal(c.ORDRES[0]) == (
        'cd "$REPTE_DIR" && python -m horaris check paquet/proposta_partida.csv --semestre 2')
    for ordre in c.ORDRES[1:5]:
        cmd = c.ordre_terminal(ordre)
        assert f'"$OLDPWD/resultats/nivell2/{ordre.clau}/proposta.csv"' in cmd
        if ordre.clau != '5.1':
            assert f'--relaxacions "$OLDPWD/resultats/nivell2/{ordre.clau}/relaxacions.csv"' in cmd
        if ordre.clau in ('5.3', '5.4'):
            assert '--referencia "$OLDPWD/resultats/nivell2/5.2/proposta.csv"' in cmd
            escenari = 'contingencies' if ordre.clau == '5.3' else 'grau-nou-40'
            assert '--escenari paquet/escenaris/' + escenari in cmd
    assert c.ordre_terminal(c.ORDRES[5]) == 'python -m nivell1.comprova'
    assert c.ordre_terminal(c.ORDRES[6], 'Pregunta inventada') == (
        "python -m app.xat.pregunta 'Pregunta inventada' --proposta 5.2 --setmana típica")
