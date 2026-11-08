"""Xifres comparables de la proposta; el JSON oficial és l'autoritat.

Rutina: sessions fora del patró modal (dia, hora, aula) de l'activitat.
Una activitat d'una sessió és rutinària; aula buida és un valor del patró,
però no una aula al recompte de grup/setmana. Els empats es mostren tots.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from nivell2.base import Base, Informe, Proposta, carrega_oficial, verifica
from horaris.check import Informe as InformeIntern, _col_loca
from horaris.model import llegeix_relaxacions, a_traslladar


@dataclass
class Comparacio:
    files: list[dict]
    titulacions: list[dict]
    abans: Informe
    despres: Informe


def calcula(proposta: Proposta, base: Base, informe: Informe,
            relaxacions: Path | None = None) -> tuple[dict, list[dict]]:
    """Calcula un costat de la taula. `base` ha de ser l'oficial.

    La col·locació reutilitza la lectura de dates i errors del verificador.
    Els percentatges per cohort tenen totes les seves sessions al denominador;
    si alguna no és avaluable, els percentatges són None (no disponibles).
    """
    col = _col_loca(base, proposta.a_files(), InformeIntern())
    x = {'veredicte': informe.veredicte}
    for codi, valors in informe.json['restriccions'].items():
        x[f'incompliments:{codi}'] = valors['compten']
    x['incompliments_declarats'] = informe.json.get('incompliments_declarats', 0)
    x['incompliments_heretats'] = sum(v.get('heretades', 0) for v in informe.json['restriccions'].values())
    for codi, v in informe.json['restriccions'].items():
        x[f'heretats:{codi}'] = v.get('heretades', 0)
        x[f'declarats:{codi}'] = v.get('declarades', 0)
    x.update(informe.objectius)
    x['sessions_no_avaluables'] = len(base.sessions) - len(col)
    patrons = defaultdict(Counter)
    aules = defaultdict(set)
    cohorts = defaultdict(Counter)
    for s in base.sessions.values():
        for coh in set(s.cohorts):
            cohorts[coh]['sessions'] += 1
    torns = sense_regla = assignades = 0
    for sid, c in col.items():
        s = c.s
        patrons[s.activitat or sid][(c.data.weekday(), c.ini, c.aula)] += 1
        torn = c.ini >= 870
        canvi_torn = torn != (s.ini >= 870)
        torns += canvi_torn
        sense_regla += canvi_torn and not (
            s.torn in ('mati', 'tarda') and torn == (s.torn == 'tarda'))
        aula_assignada = bool(not s.aula and c.aula and not s.sense_espai)
        assignades += aula_assignada
        for coh in set(s.cohorts):
            k = (coh, s.linia, c.data.isocalendar()[:2])
            aules[k]  # inclou grups/setmanes sense cap aula assignada
            if c.aula and not s.sense_espai:
                aules[k].add(c.aula)
            r = cohorts[coh]
            r['avaluables'] += 1
            r['franja'] += (c.data, c.ini) != (s.data, s.ini)
            r['aula'] += bool(s.aula and not a_traslladar(s.aula) and not s.sense_espai
                              and c.aula != s.aula)
            r['aules_assignades'] += aula_assignada
            r['torn'] += canvi_torn
    x['activitats_rutinaries_pct'] = (
        100 * sum(len(p) == 1 for p in patrons.values()) / len(patrons) if patrons else None)
    x['excepcions_rutina'] = sum(sum(p.values()) - max(p.values()) for p in patrons.values())
    x['aules_assignades'] = assignades
    x['canvis_torn'] = torns
    x['canvis_torn_sense_regla1'] = sense_regla
    x['aules_grup_setmana_mitjana'] = sum(map(len, aules.values())) / len(aules) if aules else 0
    x['aules_grup_setmana_maxim'] = max(map(len, aules.values()), default=0)
    relax = Counter((r.restriccio, r.justificacio) for r in llegeix_relaxacions(relaxacions))
    x['relaxacions_declarades'] = sum(relax.values())
    for tipus in sorted({k[0] for k in relax}):
        x[f'relaxacions:{tipus}'] = sum(n for (t, _), n in relax.items() if t == tipus)
    for (tipus, motiu), n in sorted(relax.items()):
        x[f'relaxacio:{tipus}: {motiu}'] = n
    files = []
    for coh, r in sorted(cohorts.items()):
        fila = {'cohort': coh, 'sessions': r['sessions'], 'avaluables': r['avaluables']}
        for canvi in ('franja', 'aula', 'torn'):
            fila[canvi] = r[canvi]
            fila[f'{canvi}_pct'] = (100 * r[canvi] / r['sessions']
                                       if r['avaluables'] == r['sessions'] else None)
        fila['aules_assignades'] = r['aules_assignades']
        files.append(fila)
    for canvi in ('franja', 'aula', 'torn'):
        candidats = [r for r in files if r[f'{canvi}_pct'] is not None]
        pitjor = max((r[f'{canvi}_pct'] for r in candidats), default=None)
        x[f'pitjor_cohort_{canvi}'] = ', '.join(
            r['cohort'] for r in candidats if r[f'{canvi}_pct'] == pitjor) or 'No disponible'
        x[f'pitjor_cohort_{canvi}_pct'] = pitjor
    return x, files


def compara(proposta: Proposta, base: Base | None = None, *,
            escenari: Path | None = None, referencia: Path | None = None,
            relaxacions: Path | None = None, nomes_aules: bool = False,
            proposta_path: Path | None = None) -> Comparacio:
    """Verifica els dos costats amb l'ordre oficial i calcula la comparació.

    `proposta_path`, si es proporciona, conserva els errors del CSV original
    (p. ex. duplicats) al veredicte; `proposta` en representa les assignacions.
    """
    avui = carrega_oficial()
    base = base if base is not None else carrega_oficial(escenari)
    inicial = Proposta.llegeix(referencia) if referencia else Proposta.de_base(avui)
    relax_abans = referencia.with_name('relaxacions.csv') if referencia else None
    if relax_abans is not None and not relax_abans.exists():
        relax_abans = None
    with TemporaryDirectory() as tmp:
        partida = inicial.escriu(Path(tmp) / 'avui.csv')
        desti = proposta_path or proposta.escriu(Path(tmp) / 'proposta.csv')
        abans = verifica(partida, referencia=referencia, relaxacions=relax_abans, nomes_aules=nomes_aules)
        despres = verifica(desti, escenari=escenari, referencia=referencia,
                           relaxacions=relaxacions, nomes_aules=nomes_aules)
    a, ta = calcula(inicial, avui, abans, relax_abans)
    d, td = calcula(proposta, base, despres, relaxacions)
    # Les claus sense sufix sempre es comparen amb avui, també si hi ha referència.
    for values, candidate in ((a, inicial), (d, proposta)):
        origens = [(Proposta.de_base(avui if values is a else base), '')]
        if referencia:
            origens.append((inicial, '_vs_referencia'))
        for origin, suffix in origens:
            hora = aula = torn = 0
            for sid, old in origin.files.items():
                new = candidate.files.get(sid)
                if new is None:
                    continue
                moved = (old.dia, old.h_ini, old.data) != (new.dia, new.h_ini, new.data)
                hora += moved
                aula += not moved and old.aula != new.aula
                from nivell2.base import hm
                torn += (hm(old.h_ini) >= 870) != (hm(new.h_ini) >= 870)
            values['sessions_canvien_hora' + suffix] = hora
            values['sessions_nomes_canvien_aula' + suffix] = aula
            # calcula() compta també les sessions noves respecte de la seva partida.
            if suffix:
                values['canvis_torn' + suffix] = torn
    claus = dict.fromkeys([*a, *d])
    files = [{'xifra': k, 'abans': a.get(k, 0), 'despres': d.get(k, 0)} for k in claus]
    titulacions = []
    for costat, dades in (('abans', ta), ('despres', td)):
        titulacions.extend({'horari': costat, **r} for r in dades)
    return Comparacio(files, titulacions, abans, despres)
