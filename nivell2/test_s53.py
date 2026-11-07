"""Contracte del lliurament i selecció d'escenaris, amb dades inventades."""
import json
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
         'justificacio': 'Motiu heretat inventat'}], ['restriccio', 'sessions', 'justificacio'])
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
    assert (out/'5.3'/'relaxacions.csv').read_bytes() == (path.parent/'relaxacions.csv').read_bytes()
    summary = json.loads((out/'5.3'/'resum.json').read_text())
    assert summary['incompliments_no_declarats'] == 0
    assert summary['relaxacions_per_motiu'][0]['sessions'] == 1
    assert 'identificador-inventat-privat' not in json.dumps(summary)
    stdout = capsys.readouterr().out
    assert 'identificador-inventat-privat' not in stdout and 'Q9/' not in stdout
