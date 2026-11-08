"""Comprovacions reproduïbles, amb una llista tancada d'ordres."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shlex
import subprocess
import time

import streamlit as st
from nivell2.base import ARREL, PYTHON, REPTE, RESULTATS_PRINCIPAL


@dataclass(frozen=True)
class Ordre:
    clau: str
    titol: str
    explicacio: str
    proposta: str | None = None


ORDRES = (
    Ordre('avui', 'Verificador oficial · Horari d’avui', 'Comprova el punt de partida; el veredicte esperat és NO VALIDA.'),
    Ordre('5.1', 'Verificador oficial · Aules assignades (5.1)', 'Comprova les aules assignades mantenint els horaris.', '5.1'),
    Ordre('5.2', 'Verificador oficial · Torns nous (5.2)', 'Comprova els torns nous i les relaxacions declarades.', '5.2'),
    Ordre('5.3', 'Verificador oficial · Imprevistos (5.3)', 'Comprova la resposta als imprevistos respecte de 5.2.', '5.3'),
    Ordre('5.4', 'Verificador oficial · Grau nou (5.4)', 'Comprova la incorporació del grau nou respecte de 5.2.', '5.4'),
    Ordre('xifres', 'Xifres de la part 1', 'Recalcula les xifres de l’anàlisi inicial.'),
    Ordre('assistent', 'Pregunta a l’Assistent', 'Fes una pregunta sobre la proposta que triïs.'),
)
FALTEN = "Falten els resultats: descomprimeix lliurament-nivell2.zip a l'arrel."


def prepara(ordre, pregunta='', proposta='5.2'):
    """Retorna arguments i directori sense interpretar mai el text lliure."""
    if ordre not in ORDRES:
        raise ValueError('Ordre desconeguda')
    cmd = [str(PYTHON), '-m']
    if ordre.clau == 'assistent':
        if proposta not in ('5.1', '5.2', '5.3', '5.4', 'avui'):
            raise ValueError('Proposta desconeguda')
        if not pregunta.strip():
            raise ValueError('Escriu una pregunta abans d’executar.')
        if len(pregunta) > 300:
            raise ValueError('La pregunta pot tenir com a màxim 300 caràcters.')
        return cmd + ['app.xat.pregunta', pregunta, '--proposta', proposta, '--setmana', 'típica'], ARREL
    if ordre.clau == 'xifres':
        return cmd + ['nivell1.comprova'], ARREL
    fitxer = (RESULTATS_PRINCIPAL / ordre.proposta / 'proposta.csv' if ordre.proposta
              else REPTE / 'paquet/proposta_partida.csv')
    cmd += ['horaris', 'check', str(fitxer), '--semestre', '2']
    if ordre.clau == '5.1':
        cmd += ['--nomes-aules']
    if ordre.clau in ('5.2', '5.3', '5.4'):
        if ordre.clau != '5.2':
            escenari = 'contingencies' if ordre.clau == '5.3' else 'grau-nou-40'
            cmd += ['--escenari', str(REPTE / 'paquet/escenaris' / escenari),
                    '--referencia', str(RESULTATS_PRINCIPAL / '5.2/proposta.csv')]
        cmd += ['--relaxacions', str(RESULTATS_PRINCIPAL / ordre.clau / 'relaxacions.csv')]
    return cmd, REPTE


def ordre_terminal(ordre, pregunta='', proposta='5.2'):
    """Ordre portable, des de l'arrel amb el venv i REPTE_DIR preparats."""
    if ordre.clau == 'xifres':
        return 'python -m nivell1.comprova'
    if ordre.clau == 'assistent':
        return ('python -m app.xat.pregunta ' + shlex.quote(pregunta)
                + ' --proposta ' + shlex.quote(proposta) + ' --setmana típica')
    prefix = 'cd "$REPTE_DIR" && python -m horaris check '
    if ordre.clau == 'avui':
        return prefix + 'paquet/proposta_partida.csv --semestre 2'
    resultat = f'"$OLDPWD/resultats/nivell2/{ordre.clau}'
    cmd = prefix + resultat + '/proposta.csv" --semestre 2'
    if ordre.clau == '5.1':
        return cmd + ' --nomes-aules'
    if ordre.clau in ('5.3', '5.4'):
        escenari = 'contingencies' if ordre.clau == '5.3' else 'grau-nou-40'
        cmd += (' --escenari paquet/escenaris/' + escenari
                + ' --referencia "$OLDPWD/resultats/nivell2/5.2/proposta.csv"')
    return cmd + ' --relaxacions ' + resultat + '/relaxacions.csv"'


def executa(ordre, pregunta='', proposta='5.2'):
    argv, cwd = prepara(ordre, pregunta, proposta)
    env = os.environ.copy()
    env['REPTE_DIR'] = str(REPTE)
    inici = time.monotonic()
    resultat = {'ordre': ordre_terminal(ordre, pregunta, proposta), 'error': None, 'codi': None}
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=180, cwd=cwd, env=env)
        resultat.update(sortida=r.stdout + r.stderr, codi=r.returncode)
    except subprocess.TimeoutExpired:
        resultat.update(sortida='', error='S’ha superat el límit de 180 segons. Torna-ho a provar.')
    except OSError:
        resultat.update(sortida='', error='No s’ha pogut executar l’ordre. Comprova el Python i les carpetes del projecte.')
    resultat['durada'] = time.monotonic() - inici
    return resultat


def mostra_resultat(resultat):
    st.code(resultat['ordre'], language='bash')
    if resultat['error']:
        st.error(resultat['error'])
    sortida = resultat['sortida']
    veredicte = re.search(r'\b(?:NO VALIDA|VALIDA AMB RELAXACIONS DECLARADES|VALIDA)\b', sortida)
    if veredicte:
        text = veredicte.group()
        if text == 'NO VALIDA':
            st.error(text)
        elif text == 'VALIDA':
            st.success(text)
        else:
            st.warning(text)
    st.code('\n'.join(sortida.splitlines()[-200:]) or 'Sense sortida.', language='text')
    codi = resultat['codi'] if resultat['codi'] is not None else 'no disponible'
    st.caption(f'Codi de sortida: {codi} · Durada: {resultat["durada"]:.2f} s')


def mostra():
    st.write('Executa aquí les mateixes comprovacions que es fan al terminal: el verificador oficial de cada proposta, les xifres de la part 1 i preguntes a l\'Assistent.')
    for ordre in ORDRES:
        with st.container(border=True):
            st.subheader(ordre.titol)
            st.write(ordre.explicacio)
            pregunta, proposta = '', ordre.proposta
            if ordre.clau == 'assistent':
                pregunta = st.text_input('Pregunta', value='Quantes aules queden lliures dimarts a les 10?', max_chars=300, key='comprova-pregunta')
                proposta = st.selectbox('Proposta', ['5.2', '5.1', '5.3', '5.4', 'avui'], key='comprova-proposta')
            falta = bool(proposta and proposta != 'avui' and not (RESULTATS_PRINCIPAL / proposta / 'proposta.csv').is_file())
            if falta:
                st.caption(FALTEN)
            clau = 'comprova-resultat-' + ordre.clau
            if st.button('Executa', key='comprova-executa-' + ordre.clau, disabled=falta):
                if ordre.clau == 'assistent' and not pregunta.strip():
                    st.error('Escriu una pregunta abans d’executar.')
                else:
                    with st.spinner('Executant…'):
                        st.session_state[clau] = executa(ordre, pregunta, proposta)
            if clau in st.session_state:
                mostra_resultat(st.session_state[clau])
