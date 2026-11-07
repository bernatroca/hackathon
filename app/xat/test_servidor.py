"""Contracte del servidor: només IA, eines i HTTP simulats; cap socket."""
import io
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from xat import servidor as s


@pytest.fixture(autouse=True)
def configuracio(monkeypatch):
    for prefix in ('IA', 'IA_RESERVA'):
        for camp in ('URL', 'CLAU', 'MODEL'):
            monkeypatch.delenv(f'{prefix}_{camp}', raising=False)
    monkeypatch.delenv('IA_PROVA', raising=False)
    monkeypatch.setenv('IA_URL', 'http://ia.invalid/v1')
    monkeypatch.setenv('IA_CLAU', 'secret-de-prova')
    monkeypatch.setenv('IA_MODEL', 'model-fals')
    monkeypatch.setattr(s, '_eines', lambda: SimpleNamespace(EINES=[{'type': 'function'}], executa=lambda n, a: {'ok': True, 'resultat': a}))


def crida(nom='consulta', args='{}', id='call_1'):
    return {'id': id, 'type': 'function', 'function': {'name': nom, 'arguments': args}}


def conversa():
    return s.valida({'missatges': [{'role': 'user', 'content': 'Pregunta inventada'}]})


def events():
    return [json.loads(e[6:]) for e in s.flux(conversa())]


@pytest.mark.parametrize('entrada', [None, {}, {'missatges': []}, {'missatges': [{'role': 'system', 'content': 'x'}]}, {'missatges': [{'role': 'user', 'content': 1}]}, {'missatges': [{'role': 'user', 'content': 'x'}, {'role': 'assistant', 'content': 'y'}]}])
def test_validacio(entrada):
    with pytest.raises(s.ErrorXat) as exc:
        s.valida(entrada)
    assert exc.value.estat == 400


def test_limits_i_camps():
    with pytest.raises(s.ErrorXat) as exc:
        s.valida({'missatges': [{}] * 61})
    assert exc.value.estat == 413
    assert 'tool_calls' not in s.valida({'missatges': [{'role': 'user', 'content': 'x', 'tool_calls': ['intrus']} ]})[1]
    assert conversa()[0]['content'] == s.instruccions()


@pytest.mark.parametrize('imatge', ['http://extern.invalid/img', [], {'url': 'data:text/html;base64,AAAA'}, {'url': 'data:image/png;base64,' + 'A' * s.MAX_IMATGE}])
def test_imatges_invalides(imatge):
    with pytest.raises(s.ErrorXat):
        s.valida({'missatges': [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': imatge}]}]})


def test_captures():
    part = {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,AAAA', 'detail': 'low'}}
    entrada = {'missatges': [{'role': 'user', 'content': [part] * 3}]}
    assert s.valida(entrada)[1]['content'][0]['image_url']['detail'] == 'high'
    entrada['missatges'][0]['content'].append(part)
    with pytest.raises(s.ErrorXat):
        s.valida(entrada)


@pytest.mark.parametrize('quantitat', [1, 3])
def test_bucle(monkeypatch, quantitat):
    historials = []
    def api(p, missatges):
        historials.append(list(missatges))
        if len(historials) == 1:
            yield 'tools', [crida(args='{"inventat": true}', id=f'c{i}') for i in range(quantitat)]
        else:
            yield 'tros', 'Resposta '
            yield 'tros', 'comprovable'
        yield 'fi', {'tallada': False, 'model': 'fals'}
    monkeypatch.setattr(s, '_trossos_api', api)
    resultat = events()
    assert sum('eina' in e for e in resultat) == quantitat
    assert ''.join(e.get('tros', '') for e in resultat) == 'Resposta comprovable'
    tools = [m for m in historials[1] if m['role'] == 'tool']
    assert len(tools) == quantitat
    for i, tool in enumerate(tools):
        assert tool['tool_call_id'] == f'c{i}'
        assert tool['content'].startswith('<dades>\n') and tool['content'].endswith('\n</dades>')
        assert json.loads(tool['content'][8:-9])['ok']
    assert resultat[-1]['fi']
    assert len(conversa()) == 2


def test_limit(monkeypatch):
    api = Mock(side_effect=lambda *a: iter([('tools', [crida()])]))
    monkeypatch.setattr(s, '_trossos_api', api)
    resultat = events()
    assert api.call_count == 6
    assert 'No he pogut acabar' in resultat[-2]['tros']
    assert resultat[-1]['fi']


@pytest.mark.parametrize('args', ['{', '[]', 'null'])
def test_arguments_invalids(args):
    assert not s._executa(crida(args=args))['ok']


def test_error_eina(monkeypatch):
    def executa(*args):
        raise RuntimeError('secret-de-prova')
    monkeypatch.setattr(s, '_eines', lambda: SimpleNamespace(executa=executa))
    assert s._executa(crida()) == {'ok': False, 'error': 'No s’ha pogut executar l’eina.'}
    monkeypatch.setattr(s, '_eines', lambda: None)
    assert not s._executa(crida())['ok']


def test_reserva(monkeypatch):
    monkeypatch.setenv('IA_RESERVA_URL', 'http://reserva.invalid')
    monkeypatch.setenv('IA_RESERVA_CLAU', 'secret-reserva')
    monkeypatch.setenv('IA_RESERVA_MODEL', 'reserva')
    def api(p, m):
        if p['nom'] == 'ia':
            yield 'tools', [crida()]
            raise s.ErrorIA('secret-de-prova')
        yield 'tros', 'reserva'
        yield 'fi', {'model': 'reserva', 'tallada': False}
    monkeypatch.setattr(s, '_trossos_api', api)
    assert events()[-1]['model'] == 'reserva'


def test_error_durant_flux(monkeypatch):
    def api(*a):
        yield 'tros', 'inici'
        raise s.ErrorIA('secret-de-prova')
    monkeypatch.setattr(s, '_trossos_api', api)
    assert 'error' in events()[-1]
    assert 'secret-de-prova' not in s._sse({'error': 'secret-de-prova'})


def test_stream_fragments(monkeypatch):
    blocs = [
        {'choices': [{'delta': {'tool_calls': [{'index': 0, 'id': 'c1', 'function': {'name': 'cons', 'arguments': '{"a":'}}]}}]},
        {'choices': [{'delta': {'tool_calls': [{'index': 0, 'function': {'name': 'ulta', 'arguments': '1}'}}]}}]},
    ]
    resposta = io.BytesIO(b''.join(('data: ' + json.dumps(b) + '\n\n').encode() for b in blocs) + b'data: [DONE]\n')
    peticions = []
    def obre(req, **kw):
        peticions.append(json.loads(req.data))
        return resposta
    monkeypatch.setattr(s.urllib.request, 'urlopen', obre)
    resultat = list(s._trossos_api(s.proveidors()[0], conversa()))
    assert resultat[0] == ('tools', [crida(args='{"a":1}', id='c1')])
    assert peticions[0]['tool_choice'] == 'auto'
    assert peticions[0]['tools'] == [{'type': 'function'}]


def handler(metode, cos=b'', origen='http://localhost:8501', longitud=None):
    h = object.__new__(s.Handler)
    h.path = '/api/xat'
    h.headers = {'Content-Length': str(len(cos) if longitud is None else longitud)}
    if origen:
        h.headers['Origin'] = origen
    h.rfile, h.wfile = io.BytesIO(cos), io.BytesIO()
    h.send_response = Mock()
    h.send_header = Mock()
    h.end_headers = Mock()
    getattr(h, 'do_' + metode)()
    return h


@pytest.mark.parametrize('origen', ['http://localhost:8501', 'http://127.0.0.1:8501', 'http://localhost:8503', 'http://127.0.0.1:8506', 'http://localhost', 'http://127.0.0.1'])
def test_cors(origen):
    for metode, estat in [('GET', 200), ('OPTIONS', 204)]:
        h = handler(metode, origen=origen)
        h.send_response.assert_called_once_with(estat)
        h.send_header.assert_any_call('Access-Control-Allow-Origin', origen)
    handler('POST', origen='http://extern.invalid').send_response.assert_called_once_with(403)


def test_http_errors(monkeypatch):
    handler('POST', b'{').send_response.assert_called_once_with(400)
    handler('POST', longitud=s.MAX_COS + 1).send_response.assert_called_once_with(413)
    monkeypatch.setattr(s, 'falta', lambda: 'falta')
    handler('POST').send_response.assert_called_once_with(503)


def test_http_flux(monkeypatch):
    monkeypatch.setattr(s, '_trossos_api', lambda *a: iter([('tros', 'Hola'), ('fi', {'model': 'fals', 'tallada': False})]))
    h = handler('POST', json.dumps({'missatges': [{'role': 'user', 'content': 'x'}]}).encode())
    h.send_response.assert_called_once_with(200)
    assert h.wfile.getvalue().startswith(b'data: {"tros": "Hola"}\n\n')
    assert b'"fi": true' in h.wfile.getvalue()


def test_prova(monkeypatch):
    monkeypatch.setenv('IA_PROVA', '1')
    monkeypatch.setattr(s.time, 'sleep', lambda _: None)
    falsa = Mock(wraps=s._executa_prova)
    monkeypatch.setattr(s, '_executa_prova', falsa)
    monkeypatch.setattr(s, '_eines', lambda: pytest.fail('No ha de carregar eines reals'))
    resultat = events()
    falsa.assert_called_once()
    assert resultat[0] == {'eina': 'eco_prova'}
    assert resultat[-1]['model'] == 'prova'


def test_arrenca_un_cop(monkeypatch):
    servidor = Mock(server_address=('127.0.0.1', 8502))
    constructor = Mock(return_value=servidor)
    fil = Mock()
    monkeypatch.setattr(s, '_servidor', None)
    monkeypatch.setattr(s, '_url_reutilitzada', None)
    monkeypatch.setattr(s, '_fil', None)
    monkeypatch.setattr(s, 'ThreadingHTTPServer', constructor)
    monkeypatch.setattr(s.threading, 'Thread', Mock(return_value=fil))
    monkeypatch.setattr(s, 'carrega_env', Mock())
    assert s.arrenca() == s.arrenca(9999) == 'http://127.0.0.1:8502/api/xat'
    constructor.assert_called_once()
    fil.start.assert_called_once()


def test_env(monkeypatch, tmp_path):
    fitxer = tmp_path / '.env'
    fitxer.write_text('IA_MODEL=altre\nIA_PROVA=1\n', encoding='utf-8')
    monkeypatch.setattr(s, '_arrel_principal', lambda: tmp_path)
    s.carrega_env()
    assert s.os.environ['IA_MODEL'] == 'model-fals'
    assert s.os.environ['IA_PROVA'] == '1'


def test_sense_modul_eines(monkeypatch):
    # Exercita la importació real del servidor, sense dependre del fitxer paral·lel.
    import importlib
    spec = importlib.util.spec_from_file_location('servidor_aillat', s.__file__)
    aillat = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aillat)
    aillat.__package__ = 'xat'
    def absent(nom):
        raise ModuleNotFoundError(name=nom)
    monkeypatch.setattr(aillat.importlib, 'import_module', absent)
    assert aillat._eines() is None
    assert not aillat._executa(crida())['ok']


def test_http_error_abans_stream(monkeypatch):
    def falla(*args):
        raise s.ErrorIA('secret-de-prova')
        yield
    monkeypatch.setattr(s, '_trossos_api', falla)
    h = handler('POST', json.dumps({'missatges': [{'role': 'user', 'content': 'x'}]}).encode())
    h.send_response.assert_called_once_with(502)
    assert 'error' in json.loads(h.wfile.getvalue())
    assert b'secret-de-prova' not in h.wfile.getvalue()


@pytest.mark.parametrize('origen', ['https://localhost:8501', 'http://localhost.evil:8501', 'http://127.0.0.2:8501', 'http://localhost:123456', 'http://localhost:8501/path', 'http://extern.invalid'])
def test_cors_rebutja(origen):
    h = handler('POST', origen=origen)
    h.send_response.assert_called_once_with(403)
    assert not any(c.args[0] == 'Access-Control-Allow-Origin' for c in h.send_header.call_args_list)


@pytest.mark.parametrize('resposta', [b'{"ok":true}', b'{"ok":false}', b'{"ok":1}', b'[]', b'no JSON', None])
def test_arrenca_port_ocupat(monkeypatch, resposta):
    import errno
    monkeypatch.setattr(s, '_servidor', None)
    monkeypatch.setattr(s, '_url_reutilitzada', None)
    monkeypatch.setattr(s, 'carrega_env', Mock())
    constructor = Mock(side_effect=OSError(errno.EADDRINUSE, 'address in use'))
    monkeypatch.setattr(s, 'ThreadingHTTPServer', constructor)
    obre = Mock(return_value=io.BytesIO(resposta)) if resposta is not None else Mock(side_effect=TimeoutError())
    monkeypatch.setattr(s.urllib.request, 'urlopen', obre)
    if resposta == b'{"ok":true}':
        assert s.arrenca(8502) == 'http://127.0.0.1:8502/api/xat'
        assert s.arrenca(8502) == 'http://127.0.0.1:8502/api/xat'
        constructor.assert_called_once()
    else:
        with pytest.raises(RuntimeError, match='El port 8502 està ocupat'):
            s.arrenca(8502)
    obre.assert_called_once_with('http://127.0.0.1:8502/api/xat', timeout=2)


def test_arrenca_altre_error_bind(monkeypatch):
    import errno
    monkeypatch.setattr(s, '_servidor', None)
    monkeypatch.setattr(s, '_url_reutilitzada', None)
    monkeypatch.setattr(s, 'carrega_env', Mock())
    monkeypatch.setattr(s, 'ThreadingHTTPServer', Mock(side_effect=OSError(errno.EACCES, 'permission denied')))
    obre = Mock()
    monkeypatch.setattr(s.urllib.request, 'urlopen', obre)
    with pytest.raises(OSError):
        s.arrenca()
    obre.assert_not_called()


@pytest.mark.parametrize('cos, detall', [
    (b'{"error":{"message":"Model inexistent secret-de-prova"}}', 'Model inexistent [clau oculta]'),
    (b'{"error":{"message":"' + b'x' * 400 + b'"}}', 'x' * 300),
    (b'no JSON', ''),
    (b'{"error":"sense missatge"}', ''),
])
def test_detall_http_ia(monkeypatch, cos, detall):
    error = s.urllib.error.HTTPError('http://ia.invalid', 404, 'Not Found', {}, io.BytesIO(cos))
    monkeypatch.setattr(s.urllib.request, 'urlopen', Mock(side_effect=error))
    with pytest.raises(s.ErrorXat) as exc:
        s.flux(conversa())
    assert exc.value.estat == 502
    assert exc.value.missatge == 'La IA ha respost HTTP 404' + (f': {detall}' if detall else '.')
    assert 'secret-de-prova' not in exc.value.missatge


def test_motiu_connexio(monkeypatch):
    monkeypatch.setenv('IA_RESERVA_CLAU', 'secret-reserva')
    error = s.urllib.error.URLError('connexió refusada secret-de-prova secret-reserva')
    monkeypatch.setattr(s.urllib.request, 'urlopen', Mock(side_effect=error))
    with pytest.raises(s.ErrorXat) as exc:
        s.flux(conversa())
    assert 'connexió refusada [clau oculta] [clau oculta]' in exc.value.missatge
    assert 'secret-de-prova' not in exc.value.missatge
    assert 'secret-reserva' not in exc.value.missatge
