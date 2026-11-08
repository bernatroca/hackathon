"""Presentació del 5.3, calculada en memòria sense llegir ni escriure fitxers.

Els recomptes són de sessions datades, com els del verificador. Una sessió pot
estar afectada per més d'un imprevist; al total i a la taula només es compta un cop.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import re

from nivell2.junta import MOTIU_S04526

DIES = 'LMXJV'
NOMS_DIES = ('Dilluns', 'Dimarts', 'Dimecres', 'Dijous', 'Divendres', 'Dissabte', 'Diumenge')
TIPUS = {'TE': 'teoria', 'PAUL': 'problemes', 'SEM': 'seminari', 'PLAB': 'laboratori'}
IMPREVISTOS = (
    ('aula_reservada', 'Aula reservada una setmana'),
    ('grup_creix', 'Un grup de teoria creix'),
    ('aula_avariada', 'Aula avariada un dia'),
    ('recuperacio', 'Classe cancel·lada que es recupera'),
)
ORDRE = 'python -m nivell2.s53 --temps 40 --llavor 0'


def nom_grup(grup, tipus):
    nom = TIPUS.get(tipus, 'classe')
    return f'{"Grup" if tipus == "TE" else "Subgrup"} {grup.rsplit("/", 1)[-1]} · {nom}'


MOTIU_DESCONEGUT = '1 d’aquestes classes necessita una excepció a les condicions habituals; en pots consultar el motiu al detall tècnic.'
MOTIU_FIXADA = '1 d’aquestes classes estava fixada; com que la seva aula està tancada, només li canviem l’aula: es fa el mateix dia, a la mateixa hora.'
MOTIUS_PLANERS = {
    'L’aula de la sessió fixada està tancada per una contingència; és imprescindible canviar només l’aula, conservant el dia, l’hora i el torn.':
        MOTIU_FIXADA,
    'La regla 1 diu que les classes de 1r i 2n d’aquests graus no es toquen; ja es fan a la tarda.':
        'Aquestes classes ja es fan a la tarda i mantenen l’horari perquè estaven fixades.',
    'El doble va a la classe d’un altre grup, que no es mou.':
        'L’alumnat de la doble titulació comparteix classe amb un altre grup i en manté l’horari.',
    'Setmana d’avaluació: impossibilitat demostrada amb R1 dura; vegeu diagnostic.md.':
        MOTIU_S04526,
}


def motiu_planer(text, n=1):
    """Només publiquem traduccions conegudes; un motiu nou no exposa text tècnic."""
    normalitzat = text.replace("'", '’')
    normalitzat = re.sub(r'(?:\.\./5\.2/)?diagnostic\.md', 'diagnostic.md', normalitzat)
    planer = MOTIUS_PLANERS.get(normalitzat, MOTIU_DESCONEGUT)
    if n != 1:
        if planer == MOTIU_FIXADA:
            return (f'{n} d’aquestes classes estaven fixades; com que la seva aula està tancada, '
                    'només els canviem l’aula: es fan el mateix dia, a la mateixa hora.')
        if planer == MOTIU_DESCONEGUT:
            return (f'{n} d’aquestes classes necessiten una excepció a les condicions habituals; '
                    'en pots consultar el motiu al detall tècnic.')
    return planer


def _moment(sessio, assignacio):
    data = (date.fromisoformat(assignacio.data) if assignacio.data else
            sessio.data - timedelta(days=sessio.data.weekday())
            + timedelta(days=DIES.index(assignacio.dia)))
    hora, minut = map(int, assignacio.h_ini.split(':'))
    return data, hora * 60 + minut


def _hora(minuts):
    return f'{minuts // 60:02}:{minuts % 60:02}'


def _lloc(sessio, assignacio):
    data, inici = _moment(sessio, assignacio)
    aula = ('Sense aula pròpia' if getattr(sessio, 'sense_espai', False)
            else 'Aula no indicada a les dades') if not assignacio.aula else f'Aula {assignacio.aula}'
    return (f'{NOMS_DIES[data.weekday()]} {data:%d/%m/%Y} · '
            f'{_hora(inici)}–{_hora(inici + sessio.durada)} · {aula}')


def _relaxacions(files):
    """Normalitza files CSV o objectes Relaxacio; deduplica per sessió i motiu."""
    resultat = set()
    for fila in files:
        if isinstance(fila, dict):
            regla, sessions, motiu = fila['restriccio'], fila['sessions'], fila['justificacio']
        else:
            regla, sessions, motiu = fila.restriccio, fila.sessions, fila.justificacio
        if isinstance(sessions, str):
            sessions = sessions.split('|')
        resultat.update((regla, sid.strip(), motiu) for sid in sessions if sid.strip())
    return resultat


def calcula(base_52, contingencies, proposta_52, proposta_53, relaxacions, *,
            relaxacions_referencia=(), resum=None, informe=None, noms=None):
    """Torna resum, quatre targetes i files ordenades, tots serialitzables.

    ``relaxacions`` conté totes les declaracions del 5.3; es resten les del 5.2
    per sessió, regla i justificació. ``informe`` aporta el veredicte oficial
    un cop comprovada l'empremta del CSV pel carregador; ``resum`` només el temps.
    ``noms`` associa codis amb noms d'assignatura, sense exposar-ne els codis.
    """
    ids = set(base_52.sessions)
    if any(set(files) != ids for files in
           (contingencies.sessions, proposta_52.files, proposta_53.files)):
        raise ValueError('Les bases i les propostes han de contenir les mateixes classes.')
    noms = noms or {}
    resum = resum or {}
    informe = informe or {}
    afectades = {clau: set() for clau, _ in IMPREVISTOS}
    afectades['recuperacio'] = set(contingencies.cancellades)
    if not afectades['recuperacio'] <= ids:
        raise ValueError('La recuperació ha de correspondre a una classe de la proposta.')
    moments_abans, moments_despres = {}, {}
    canvis_aula, canvis_franja = set(), set()
    for sid, sessio in contingencies.sessions.items():
        abans, despres = proposta_52.files[sid], proposta_53.files[sid]
        data, inici = moments_abans[sid] = _moment(sessio, abans)
        moments_despres[sid] = _moment(sessio, despres)
        if abans.aula != despres.aula:
            canvis_aula.add(sid)
        if moments_abans[sid] != moments_despres[sid]:
            canvis_franja.add(sid)
        if sessio.alumnes > base_52.sessions[sid].alumnes:
            afectades['grup_creix'].add(sid)
        for tancament in contingencies.tancaments:
            if (not sessio.sense_espai and abans.aula == tancament.aula
                    and tancament.data_ini <= data <= tancament.data_fi
                    and inici < tancament.fi and inici + sessio.durada > tancament.ini):
                clau = 'aula_reservada' if tancament.data_ini != tancament.data_fi else 'aula_avariada'
                afectades[clau].add(sid)

    def nom(sessio):
        return noms.get(sessio.codi) or getattr(sessio, 'assignatura', '') or 'Assignatura sense nom'

    def descripcio(clau):
        frases = []
        if clau in ('aula_reservada', 'aula_avariada'):
            for t in contingencies.tancaments:
                if (t.data_ini != t.data_fi) != (clau == 'aula_reservada'):
                    continue
                periode = (f'del {t.data_ini:%d/%m/%Y} al {t.data_fi:%d/%m/%Y}'
                           if t.data_ini != t.data_fi else f'el {t.data_ini:%d/%m/%Y}')
                causa = 'reservada' if clau == 'aula_reservada' else 'avariada'
                franja = (f', de {_hora(t.ini)} a {_hora(t.fi)}'
                          if (t.ini, t.fi) != (0, 1440) else '')
                frases.append(f'L’aula {t.aula} està {causa} {periode}{franja}.')
        elif clau == 'grup_creix':
            grups = {}
            for sid in sorted(afectades[clau]):
                s = contingencies.sessions[sid]
                grups.setdefault((s.codi, s.grup, s.alumnes, base_52.sessions[sid].alumnes), s)
            for (_, _, alumnes, anteriors), s in grups.items():
                frases.append(f'{nom(s)} · {nom_grup(s.grup, s.tipus)} passa de '
                              f'{anteriors} a {alumnes} alumnes durant tot el semestre.')
        else:
            for sid in sorted(afectades[clau], key=lambda sid: moments_abans[sid]):
                s = contingencies.sessions[sid]
                limit = contingencies.cancellades[sid]
                frases.append(f'{nom(s)} · {nom_grup(s.grup, s.tipus)}: classe cancel·lada '
                              f'el {s.data:%d/%m/%Y}; es pot recuperar fins al {limit:%d/%m/%Y}. '
                              f'La recuperem: {_lloc(s, proposta_53.files[sid])}.')
        return ' '.join(dict.fromkeys(frases)) or 'Aquest imprevist no consta a l’escenari.'

    totes_relax = _relaxacions(relaxacions)
    noves = totes_relax - _relaxacions(relaxacions_referencia)
    targetes = []
    for clau, titol in IMPREVISTOS:
        sessions = afectades[clau]
        # Comptem classes úniques per explicació, encara que tinguin més d’una regla.
        per_explicacio = defaultdict(set)
        originals = {}
        for _, sid, motiu in noves:
            if sid in sessions:
                explicacio = motiu_planer(motiu)
                per_explicacio[explicacio].add(sid)
                originals[explicacio] = motiu
        motius = sorted(motiu_planer(originals[m], len(ids))
                        for m, ids in per_explicacio.items())
        targetes.append({'clau': clau, 'titol': titol, 'descripcio': descripcio(clau),
                        'sessions_afectades': len(sessions),
                        'canvis_aula': len(sessions & canvis_aula),
                        'canvis_franja': len(sessions & canvis_franja),
                        'excepcio': bool(motius), 'motius': motius})
    files = []
    mogudes = canvis_aula | canvis_franja
    for sid in sorted(mogudes, key=lambda sid: (*moments_abans[sid], sid)):
        s = contingencies.sessions[sid]
        files.append({'assignatura': nom(s), 'grup': nom_grup(s.grup, s.tipus),
                      'abans': _lloc(s, proposta_52.files[sid]),
                      'despres': _lloc(s, proposta_53.files[sid]),
                      'data': moments_abans[sid][0].isoformat(),
                      'hora': _hora(moments_abans[sid][1]),
                      'imprevistos': [clau for clau, _ in IMPREVISTOS if sid in afectades[clau]]})
    per_motiu = defaultdict(set)
    for _, sid, motiu in totes_relax:
        per_motiu[motiu].add(sid)
    directes = set().union(*afectades.values())
    return {
        'resum': {
            'veredicte': informe.get('veredicte', ''), 'temps_s': resum.get('temps_s'),
            'canvis_aula_vs_referencia': len(canvis_aula),
            'canvis_franja_vs_referencia': len(canvis_franja),
            'canvis_aula_oficials': informe.get('objectius', {}).get('canvis_aula_vs_referencia'),
            'canvis_aula_recuperades': len(canvis_aula & set(contingencies.cancellades)),
            'sessions_afectades_per_imprevist': {k: len(v) for k, v in afectades.items()},
            'classes_de_suport': len(mogudes - directes),
            'relaxacions_per_motiu': [{'motiu': motiu, 'sessions': len(sessions)}
                                     for motiu, sessions in sorted(per_motiu.items())],
        },
        'imprevistos': targetes, 'files': files, 'ordre': ORDRE,
    }
