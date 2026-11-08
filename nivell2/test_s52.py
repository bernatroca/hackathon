"""Proves ràpides de la integració sense resoldre el semestre complet."""
from unittest.mock import patch
from nivell2.base import Proposta
from nivell2.test_franges import base_petita, sessio
from nivell2.s52 import resol, escriu_csv


def test_integra_referencia_i_aules():
    s = sessio('a', ini=870)
    b = base_petita(s)
    slots = {'a': (s.data, 930)}
    with patch('nivell2.s52.assigna_franges',return_value=(slots,'FEASIBLE',[])) as f, \
         patch('nivell2.s52.assigna_aules',return_value=({'a':'0'},'OPTIMAL')) as a:
        f.estadistiques = {}
        p,ex,h = resol(b,temps_franges=1,temps_aules=1)
    assert p.files['a'].h_ini == '15:30'
    assert p.files['a'].aula == '0'
    assert a.call_args.kwargs['referencia'] == Proposta.de_base(b)
    assert h[0]['franges'] == 'FEASIBLE' and h[0]['aules'] == 'OPTIMAL'


def test_reintent_limitat_sense_relaxacio():
    s = sessio('a',ini=870)
    b = base_petita(s)
    with patch('nivell2.s52.assigna_franges',return_value=({'a':(s.data,s.ini)},'FEASIBLE',[])) as f, \
         patch('nivell2.s52.assigna_aules',return_value=({},'INFEASIBLE')) as a:
        f.estadistiques = {}
        p,_,history = resol(b,temps_franges=10,temps_aules=10)
    assert p is None and len(history) == 3 and a.call_count == 3
    assert history[1]['limits_capacitat'][-1] == 3
    assert history[2]['limits_capacitat'][-1] == 2


def test_unknown_franges_no_crida_aules():
    with patch('nivell2.s52.assigna_franges',return_value=({},'UNKNOWN',[])) as f, \
         patch('nivell2.s52.assigna_aules') as a:
        f.estadistiques = {}
        p,_,h = resol(base_petita(sessio('a')))
    assert p is None and not a.called and h[0]['franges'] == 'UNKNOWN'


def test_excepcions_buides_amb_capcalera(tmp_path):
    path = tmp_path/'excepcions.csv'
    escriu_csv(path,[],['id_sessio','motiu'])
    assert path.read_text().strip() == 'id_sessio,motiu'


def test_model_setmana_excepcions_minimes_i_originals():
    import datetime as dt
    import time
    from nivell2.franges import _problema, _resol_torn
    from horaris.model import MATI, TARDA
    date = dt.date(2027,4,9)
    a = sessio('a',data=date,dia='V',ini=540)
    b = sessio('b',data=date,dia='V',ini=660)
    lab = sessio('lab',data=date,dia='V',ini=870,durada=390,tipus='PLAB',fixada='R7')
    base = base_petita(a,b,lab,dies_sense_classe=frozenset(date-dt.timedelta(days=d) for d in range(1,5)))
    ref = Proposta.de_base(base)
    units,weeks,edges,groups = _problema(base,ref,{})
    current = {s.id:(s.data,s.ini) for s in base.sessions.values()}
    common = dict(reparacio=True,setmana_completa=True)
    result,state = _resol_torn(base,units,weeks,edges,groups,set(units),current,ref,{},
        (MATI[0],TARDA[1]),time.monotonic()+5,0,**common)
    assert result is None and state == 'INFEASIBLE'
    result,state = _resol_torn(base,units,weeks,edges,groups,set(units),current,ref,{},
        (MATI[0],TARDA[1]),time.monotonic()+5,0,torn_tou=True,**common)
    assert state == 'OPTIMAL'
    assert result == current  # Les dues excepcions només poden conservar la partida.


def test_rebutja_relaxacio_fora_w14_i_fora_original():
    import datetime as dt
    import pytest
    from nivell2.s52 import valida_excepcions
    a = sessio('a')
    b = base_petita(a)
    with pytest.raises(ValueError):
        valida_excepcions(b,Proposta.de_base(b),['a'],setmanes=set())
    a.data = dt.date(2027,4,9)
    a.dia = 'V'
    p = Proposta.de_base(b)
    valida_excepcions(b,p,['a'],setmanes={a.data-dt.timedelta(days=a.data.weekday())})
    p.files['a'].h_ini = '10:00'
    with pytest.raises(ValueError):
        valida_excepcions(b,p,['a'],setmanes={a.data-dt.timedelta(days=a.data.weekday())})


def test_doble_i_host_mouen_junts_sense_mutar_base():
    from nivell2.franges import assigna_franges
    host = sessio('inventat-host',codi='100000',ini=540,activitat='inventada-host')
    double = sessio('inventat-doble',codi='100000',ini=540,grup='TE/91',
                    activitat='inventada-doble',sense_espai=True,cohorts=('GZZ:3r',))
    base = base_petita(host,double)
    result,state,_ = assigna_franges(base,referencia=Proposta.de_base(base),temps_s=5)
    assert state == 'FEASIBLE'
    assert result[host.id] == result[double.id]
    assert result[host.id][1] >= 870
    assert host.compartida == double.compartida == ''
    assert not host.fixada and not double.fixada


def test_doble_fixat_i_no_aparellat_es_conserven():
    from nivell2.franges import assigna_franges
    host = sessio('inventat-host',codi='100000',ini=540,fixada='R1: GXX 1r')
    double = sessio('inventat-doble',codi='100000',ini=540,sense_espai=True,grup='TE/91')
    orphan = sessio('inventat-sol',codi='100099',ini=660,sense_espai=True,grup='TE/92')
    base = base_petita(host,double,orphan)
    result,state,_ = assigna_franges(base,referencia=Proposta.de_base(base),temps_s=5)
    assert state == 'FEASIBLE'
    assert all(result[s.id] == (s.data,s.ini) for s in base.sessions.values())
    assert assigna_franges.estadistiques['dobles_sense_parella'] == 1


def test_relaxacions_per_motiu_amb_dades_inventades():
    from nivell2.s52 import relaxacions_proposta, MOTIU_FIXADES, MOTIU_DOBLES
    fixed = sessio('inventat-fix',codi='100000',ini=900,torn='mati',fixada='R1: GXX 1r')
    double = sessio('inventat-doble',codi='100000',ini=900,torn='mati',sense_espai=True,grup='TE/91',fixada='R1: GXX 1r')
    base = base_petita(fixed,double)
    proposal = Proposta.de_base(base)
    proposal.files[fixed.id].aula = 'aula-inventada'
    rows = relaxacions_proposta(base,proposal,set())
    assert {r['justificacio'] for r in rows} == {MOTIU_FIXADES}
    assert all(double.id not in r['sessions'].split('|') for r in rows)
    assert all(r['restriccio'] == 'R1-TORN' for r in rows)


def test_vincles_horaris_no_sumen_aforament_de_classes_diferents():
    from nivell2.franges import assigna_franges
    rows = [sessio(f'inventat-{i}',codi='100000',tipus='PAUL',grup=f'PAUL/8{i}1',
                    alumnes=70,ini=540,cohorts=(f'GXX{i}:3r',),docents=frozenset({f'doc-inventat-{i}'}))
            for i in range(3)]
    double = sessio('inventat-doble',codi='100000',tipus='PAUL',grup='PAUL/911',
                    sense_espai=True,ini=540,cohorts=('GZZ:3r',),docents=frozenset())
    base = base_petita(*rows,double)
    result,state,_ = assigna_franges(base,referencia=Proposta.de_base(base),temps_s=5)
    assert state == 'FEASIBLE'
    assert len({result[s.id] for s in base.sessions.values()}) == 1


def test_sortida_solver_no_mostra_detall_privatiu(capsys):
    secret = 'identificador-inventat-privat'
    row = sessio(secret,ini=870)
    base = base_petita(row)
    with patch('nivell2.s52.assigna_franges',return_value=({row.id:(row.data,row.ini)},'FEASIBLE',[])) as f, \
         patch('nivell2.s52.assigna_aules',return_value=({row.id:'aula-inventada'},'OPTIMAL')):
        f.estadistiques = {'proves_torn':[{'sessions':[secret]}]}
        _,_,history = resol(base,temps_franges=1,temps_aules=1)
    stdout = capsys.readouterr().out
    assert secret not in stdout and 'aula-inventada' not in stdout
    assert history[0]['estadistiques_franges']['proves_torn'][0]['sessions'] == [secret]


def test_fallada_conserva_tot_el_lliurament(tmp_path):
    from nivell2.s52 import main
    root = tmp_path/'nivell2'
    out = root/'5.2'
    out.mkdir(parents=True)
    original = {'README.md':b'anterior', 'relaxacions.csv':b'anterior',
                'diagnostic.md':b'anterior', 'xifres.csv':b'anterior'}
    for name,content in original.items():
        (out/name).write_bytes(content)
    for state in ('UNKNOWN','INFEASIBLE'):
        with patch('nivell2.s52.RESULTATS',root), \
             patch('nivell2.s52.carrega_model',return_value=base_petita(sessio('inventat'))), \
             patch('nivell2.s52.carrega_oficial',return_value=base_petita(sessio('inventat'))), \
             patch('nivell2.s52.resol',return_value=(None,[],[{'franges':state}])):
            assert main(['--temps-franges','1','--temps-aules','1']) == 1
        assert {p.name:p.read_bytes() for p in out.iterdir()} == original
    diagnostics = [p.read_text() for p in (tmp_path/'.intents-s52').glob('*/diagnostic.md')]
    assert any('UNKNOWN — temps esgotat' in text for text in diagnostics)
    assert any('INFEASIBLE — impossibilitat demostrada' in text for text in diagnostics)


def test_error_verificador_conserva_lliurament(tmp_path):
    from nivell2.s52 import main
    root = tmp_path/'nivell2'
    out = root/'5.2'
    out.mkdir(parents=True)
    (out/'proposta.csv').write_bytes(b'proposta anterior')
    with patch('nivell2.s52.RESULTATS',root), \
         patch('nivell2.s52.verifica',side_effect=RuntimeError('inventat')):
        assert main([]) == 2
    assert (out/'proposta.csv').read_bytes() == b'proposta anterior'
    assert list(p.name for p in out.iterdir()) == ['proposta.csv']


def test_publicacio_fallida_restaura_directori(tmp_path):
    import pytest
    from pathlib import Path
    from nivell2.s52 import publica
    out = tmp_path/'5.2'
    out.mkdir()
    (out/'proposta.csv').write_text('anterior')
    stage = tmp_path/'stage'
    stage.mkdir()
    (stage/'proposta.csv').write_text('nova')
    with patch('nivell2.s52._intercanvia',side_effect=OSError('fallada inventada')), pytest.raises(OSError):
        publica(stage,out)
    assert (out/'proposta.csv').read_text() == 'anterior'


def test_publicacio_atomica_sense_barrejar_fitxers(tmp_path):
    from nivell2.s52 import publica
    out = tmp_path/'5.2'
    out.mkdir()
    (out/'proposta.csv').write_text('anterior')
    (out/'fitxer-antic').write_text('antic')
    stage = tmp_path/'stage'
    stage.mkdir()
    (stage/'proposta.csv').write_text('nova')
    (stage/'informe.json').write_text('nou')
    publica(stage,out)
    assert {p.name:p.read_text() for p in out.iterdir()} == {
        'proposta.csv':'nova','informe.json':'nou'}
    assert not stage.exists()


def test_candidata_invalida_o_pitjor_no_publica(tmp_path):
    from types import SimpleNamespace
    from nivell2.base import Informe
    from nivell2.s52 import _executa
    def report(verdict,declared):
        return Informe({'veredicte':verdict,'incompliments_declarats':declared,
                        'restriccions':{},'objectius':dict.fromkeys(
                            ('canvis_franja','hores_mortes_min','desplacaments_aula',
                             'r6_aules_te_extra_per_grup'),0)},'')
    base = base_petita(sessio('inventat',ini=870))
    out = tmp_path/'5.2'
    out.mkdir()
    Proposta.de_base(base).escriu(out/'proposta.csv')
    original = (out/'proposta.csv').read_bytes()
    for index,(verdict,declared) in enumerate([('NO VALIDA',0),('VALIDA AMB RELAXACIONS DECLARADES',460),
            ('VALIDA AMB RELAXACIONS DECLARADES',459),('VALIDA',0)]):
        stage = tmp_path/f'stage-{index}'
        stage.mkdir()
        with patch('nivell2.s52.verifica',side_effect=[report('VALIDA AMB RELAXACIONS DECLARADES',459),
                 report(verdict,declared),report(verdict,declared)]), \
             patch('nivell2.s52.carrega_model',return_value=base), \
             patch('nivell2.s52.carrega_oficial',return_value=base), \
             patch('nivell2.s52.resol',return_value=(Proposta.de_base(base),[],[{'estadistiques_franges':{}}])), \
             patch('nivell2.s52.publica') as publish:
            assert _executa(SimpleNamespace(temps_franges=1,temps_aules=1,llavor=0),stage,out) == 1
        assert not publish.called
        assert {p.name:p.read_bytes() for p in out.iterdir()} == {'proposta.csv':original}


def test_revisio_pista_unknown_no_demostra_excepcio():
    import datetime as dt
    import time
    from nivell2.franges import _revisa_pista, assigna_franges
    row = sessio('inventat',data=dt.date(2027,4,9),dia='V',ini=540)
    base = base_petita(row)
    ref = Proposta.de_base(base)
    with patch('nivell2.franges._resol_torn',return_value=(None,'UNKNOWN')) as solve:
        result,state,_ = _revisa_pista(base,ref,ref,{},time.monotonic()+5,0,True)
    assert not result and state == 'UNKNOWN'
    assert solve.call_count == 1  # No soft R1 model without a hard proof.
    assert 'sessions' not in assigna_franges.estadistiques['proves_torn'][0]
    assert solve.call_args.kwargs['setmana_completa']
    assert 'limits_capacitat' not in solve.call_args.kwargs


def test_revisio_pista_sense_excepcio_si_r1_dura_es_possible():
    import datetime as dt
    import time
    from nivell2.franges import _revisa_pista, assigna_franges
    from nivell2.s52 import relaxacions_proposta
    row = sessio('inventat',data=dt.date(2027,4,9),dia='V',ini=540)
    base = base_petita(row)
    ref = Proposta.de_base(base)
    with patch('nivell2.franges._resol_torn',return_value=({row.id:(row.data,870)},'FEASIBLE')):
        result,state,_ = _revisa_pista(base,ref,ref,{},time.monotonic()+5,0,True)
    assert state == 'FEASIBLE' and result[row.id][1] == 870
    assert 'sessions' not in assigna_franges.estadistiques['proves_torn'][0]
    from nivell2.franges import proposta_franges
    assert not relaxacions_proposta(base,proposta_franges(base,ref,result),set())


def test_restauracio_rutina_i_motius_reals(tmp_path):
    import datetime as dt
    from nivell2.base import Informe
    from nivell2.s52 import restaura_rutina, excepcions_rutina
    rows = [sessio(f'inventat-{i}', activitat='A', ini=870,
                   data=dt.date(2031,2,3)+dt.timedelta(weeks=i)) for i in range(3)]
    base = base_petita(*rows)
    proposal = Proposta.de_base(base)
    proposal.files[rows[-1].id].h_ini = '16:30'
    valid = Informe({'veredicte':'VALIDA AMB RELAXACIONS DECLARADES',
                     'incompliments_declarats':2,'restriccions':{}}, '')
    bad = Informe({'veredicte':'NO VALIDA','incompliments_declarats':2,
                   'restriccions':{'R4-AULA':{'compten':1}}}, '')
    with patch('nivell2.s52.verifica', return_value=valid), \
         patch('nivell2.s52.persones_correctes',return_value=True):
        result,_,notes = restaura_rutina(base,proposal,None,tmp_path,valid)
    assert not notes and not excepcions_rutina(base,result)
    assert proposal.files[rows[-1].id].h_ini == '16:30'
    for report, people in [(bad,True), (valid,False),
            (Informe({**valid.json,'incompliments_declarats':3},''),True)]:
        with patch('nivell2.s52.verifica',return_value=report), \
             patch('nivell2.s52.persones_correctes',side_effect=[True,people,people]):
            result,_,notes = restaura_rutina(base,proposal,None,tmp_path,valid)
        assert result == proposal and len(notes) == 1
        assert 'Excepció de calendari' not in notes[0]['motiu']
        assert any(reason in notes[0]['motiu'] for reason in ('R4-AULA','conflictes nous','augment'))


def test_restauracio_aula_actual_si_modal_ocupada(tmp_path):
    import datetime as dt
    from nivell2.base import Informe
    from nivell2.s52 import restaura_rutina
    rows = [sessio(f'inventat-{i}', activitat='A', ini=870, aula='0',
                   data=dt.date(2031,2,3)+dt.timedelta(weeks=i)) for i in range(3)]
    base = base_petita(*rows)
    proposal = Proposta.de_base(base)
    proposal.files[rows[-1].id].h_ini = '16:30'
    valid = Informe({'veredicte':'VALIDA','incompliments_declarats':0,'restriccions':{}},'')
    bad = Informe({'veredicte':'NO VALIDA','incompliments_declarats':0,
                   'restriccions':{'R4-AULA':{'compten':1}}},'')
    proposal.files[rows[-1].id].aula = '1'
    def check(path, **kwargs):
        attempt = Proposta.llegeix(path)
        return bad if attempt.files[rows[-1].id].aula == '0' else valid
    # L'hora es restaura encara que calgui conservar una excepció d'aula.
    with patch('nivell2.s52.verifica',side_effect=check), \
         patch('nivell2.s52.persones_correctes',return_value=True):
        result,_,notes = restaura_rutina(base,proposal,None,tmp_path,valid)
    assert result.files[rows[-1].id].h_ini == '14:30'
    assert result.files[rows[-1].id].aula == '1'
    assert len(notes) == 1 and 'aula conservada' in notes[0]['motiu']


def test_setmanes_avaluacio_es_deriven_del_calendari():
    import datetime as dt
    from unittest.mock import mock_open
    from nivell2.franges import setmanes_avaluacio
    invented = 'data,tipus\n2031-06-11,avaluacio\n2031-06-12,avaluacio\n2031-06-20,festiu\n'
    with patch('pathlib.Path.open',mock_open(read_data=invented)):
        assert setmanes_avaluacio() == {dt.date(2031,6,9)}


def test_pista_no_reassigna_aules_ni_franges_globals():
    base = base_petita(sessio('inventat',ini=870,aula='0'))
    pista = Proposta.de_base(base)
    with patch('nivell2.s52.assigna_franges') as franges, \
         patch('nivell2.s52.assigna_aules') as aules:
        result,_,history = resol(base,pista=pista)
    assert result == pista and result is not pista
    assert not franges.called and not aules.called
    assert history[0]['mode'] == 'restauracio_local'


def test_limits_de_qualitat_no_permeten_mes_2_percent_ni_aula_extra():
    from nivell2.s52 import qualitat_protegida
    before = {'desplacaments_aula':100,'r6_aules_te_extra_per_grup':3}
    assert qualitat_protegida(before,{**before,'desplacaments_aula':102})
    assert not qualitat_protegida(before,{**before,'desplacaments_aula':103})
    assert not qualitat_protegida(before,{**before,'r6_aules_te_extra_per_grup':4})
    assert not qualitat_protegida({**before,'desplacaments_aula':0},
                                  {**before,'desplacaments_aula':1})


def test_reparacio_aules_nomes_dia_afectat_i_amb_la_resta_fixada():
    import copy
    import datetime as dt
    from nivell2.s52 import aules_locals
    moved = sessio('inventat-mogut',ini=870,aula='0')
    fixed = sessio('inventat-quiet',ini=990,aula='1')
    other = sessio('inventat-altre-dia',data=moved.data+dt.timedelta(days=1),dia='M',aula='2')
    base = base_petita(moved,fixed,other)
    current = Proposta.de_base(base)
    candidate = copy.deepcopy(current)
    candidate.files[moved.id].h_ini = '15:30'
    with patch('nivell2.s52.assigna_aules',return_value=(
            {moved.id:'3',fixed.id:'1'},'FEASIBLE')) as solve:
        result = aules_locals(base,current,candidate,{moved.id})
    assert set(solve.call_args.args[0].sessions) == {moved.id,fixed.id}
    assert solve.call_args.kwargs['fixes'] == {fixed.id}
    assert result.files[fixed.id] == current.files[fixed.id]
    assert result.files[other.id] == current.files[other.id]
    assert result.files[moved.id].aula == '3'


def test_no_canvia_aules_de_sessions_que_no_es_mouen(tmp_path):
    import datetime as dt
    from nivell2.base import Informe
    from nivell2.s52 import restaura_rutina
    rows = [sessio(f'inventat-{i}',activitat='A',ini=870,aula='0',
                   data=dt.date(2031,2,3)+dt.timedelta(weeks=i)) for i in range(3)]
    base = base_petita(*rows)
    pista = Proposta.de_base(base)
    pista.files[rows[-1].id].aula = '1'
    report = Informe({'veredicte':'VALIDA','incompliments_declarats':0,'restriccions':{}},'')
    with patch('nivell2.s52.verifica') as check, \
         patch('nivell2.s52.persones_correctes',return_value=True):
        result,_,notes = restaura_rutina(base,pista,None,tmp_path,report)
    assert result == pista and len(notes) == 1 and not check.called


def test_publicacio_rebutja_costos_pitjors_amb_menys_excepcions(tmp_path):
    import datetime as dt
    from types import SimpleNamespace
    from nivell2.base import Informe
    from nivell2.s52 import _executa
    rows = [sessio(f'inventat-{i}',activitat='A',ini=870,aula='0',
                   data=dt.date(2031,2,3)+dt.timedelta(weeks=i)) for i in range(3)]
    base = base_petita(*rows)
    initial = Proposta.de_base(base)
    initial.files[rows[-1].id].h_ini = '16:30'
    improved = Proposta.de_base(base)
    out = tmp_path/'5.2'
    out.mkdir()
    initial.escriu(out/'proposta.csv')
    original = (out/'proposta.csv').read_bytes()
    def report(walks, extra):
        return Informe({'veredicte':'VALIDA AMB RELAXACIONS DECLARADES',
                        'incompliments_declarats':2,'restriccions':{},
                        'objectius':{'desplacaments_aula':walks,
                                     'r6_aules_te_extra_per_grup':extra}},'')
    for index,(walks,extra) in enumerate([(103,3),(100,4)]):
        stage = tmp_path/f'stage-{index}'
        stage.mkdir()
        after = report(walks,extra)
        with patch('nivell2.s52.verifica',side_effect=[report(100,3),after,after]), \
             patch('nivell2.s52.carrega_model',return_value=base), \
             patch('nivell2.s52.carrega_oficial',return_value=base), \
             patch('nivell2.s52.resol',return_value=(improved,[],[])), \
             patch('nivell2.s52.restaura_rutina',return_value=(improved,after,[])), \
             patch('nivell2.s52.publica') as publish:
            assert _executa(SimpleNamespace(temps_franges=1,temps_aules=1,llavor=0),stage,out) == 1
        assert not publish.called and (out/'proposta.csv').read_bytes() == original


def test_restaurar_host_no_pot_separar_un_doble(tmp_path):
    import datetime as dt
    from nivell2.base import Informe
    from nivell2.s52 import restaura_rutina, persones_correctes
    hosts = [sessio(f'inventat-host-{i}',codi='100000',activitat='A',
                    ini=930 if i == 2 else 870,
                    data=dt.date(2031,2,3)+dt.timedelta(weeks=i)) for i in range(3)]
    double = sessio('inventat-doble',codi='100000',activitat='B',sense_espai=True,
                    ini=930,data=hosts[-1].data,cohorts=('GZZ:3r',))
    base = base_petita(*hosts,double)
    initial = Proposta.de_base(base)
    assert persones_correctes(base,initial)
    valid = Informe({'veredicte':'VALIDA AMB RELAXACIONS DECLARADES',
                     'incompliments_declarats':2,'restriccions':{}},'')
    with patch('nivell2.s52.verifica',return_value=valid):
        result,_,notes = restaura_rutina(base,initial,None,tmp_path,valid)
    assert result == initial and len(notes) == 1
    assert 'vincle de doble separat/duplicat' in notes[0]['motiu']


def test_restauracio_conjunta_preserva_aules_i_només_torna_al_patro():
    import copy
    import datetime as dt
    import pytest
    from nivell2.s52 import restaura_conjunt
    rows = [sessio(f'inventat-{i}',activitat='A',ini=870,aula='0',
                   data=dt.date(2031,2,3)+dt.timedelta(weeks=i)) for i in range(3)]
    base = base_petita(*rows)
    initial = Proposta.de_base(base)
    initial.files[rows[-1].id].h_ini = '16:30'
    variant = Proposta.de_base(base)
    assert restaura_conjunt(base,initial,variant) == variant
    assert initial.files[rows[-1].id].h_ini == '16:30'
    bad = copy.deepcopy(variant)
    bad.files[rows[0].id].aula = '1'
    with pytest.raises(ValueError,match='sense moure'):
        restaura_conjunt(base,initial,bad)
    bad = copy.deepcopy(variant)
    bad.files[rows[-1].id].h_ini = '17:30'
    with pytest.raises(ValueError,match='fora del patró'):
        restaura_conjunt(base,initial,bad)
