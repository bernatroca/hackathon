"""Esquelet comú de la part 2. El fan servir totes les tasques; només el modifica la integració.

- `carrega_oficial()` dona la base tal com la veu el verificador del jurat.
- `carrega_model()` dona la mateixa base per al nostre model, amb els alumnes dels grups sense dada
  (dades/alumnes_sense_dada.json). No es passa mai al verificador.
- `Proposta` és el que lliurem: per a cada sessió, dia, hora d'inici i aula (i data, si és una recuperació).
- `verifica()` executa el verificador oficial (la mateixa ordre que el jurat) i en llegeix el JSON.
"""
from __future__ import annotations

import copy
import csv
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ARREL = Path(__file__).resolve().parents[1]
# Les dades són fora del repositori (no van a git). Ruta absoluta, perquè els worktrees no les tenen.
REPTE = Path('/Users/bernatroca/Bernat/Hackathon/repte/repte-horaris-escola')
PAQUET = REPTE / 'paquet'
ESCENARIS = PAQUET / 'escenaris'
CONTINGENCIES = ESCENARIS / 'contingencies'
GRAU_NOU = ESCENARIS / 'grau-nou-40'
ALUMNES_SENSE_DADA = Path('/Users/bernatroca/Bernat/Hackathon/dades/alumnes_sense_dada.json')
RESULTATS = ARREL / 'resultats' / 'nivell2'
PYTHON = Path('/Users/bernatroca/Bernat/Hackathon/.venv/bin/python')
SEMESTRE = 2

if str(REPTE) not in sys.path:
    sys.path.insert(0, str(REPTE))

from horaris.check import avalua  # noqa: E402
from horaris.model import Base, Fila, Sessio, carrega_base, fmt, hm  # noqa: E402

__all__ = ['ARREL', 'REPTE', 'PAQUET', 'CONTINGENCIES', 'GRAU_NOU', 'RESULTATS', 'SEMESTRE',
           'Base', 'Sessio', 'Fila', 'fmt', 'hm', 'carrega_oficial', 'carrega_model', 'alumnes_recerca',
           'Proposta', 'Informe', 'verifica', 'avalua_rapid']


def carrega_oficial(escenari: Path | None = None, semestre: int = SEMESTRE) -> Base:
    """La base del verificador oficial (el que veu el jurat)."""
    return carrega_base(PAQUET, semestre=semestre, escenari=escenari)


def alumnes_recerca() -> dict[tuple[str, str], int]:
    """(codi, grup) -> alumnes dels grups que al paquet tenen 0 (vegeu dades/alumnes_sense_dada.json)."""
    cfg = json.loads(ALUMNES_SENSE_DADA.read_text(encoding='utf-8'))
    return {(g['codi'], g['grup']): int(g['alumnes']) for g in cfg['grups']}


def carrega_model(escenari: Path | None = None, semestre: int = SEMESTRE) -> Base:
    """La base per al nostre model: igual que l'oficial, però amb els alumnes dels grups sense dada.

    És una còpia: modificar-la no canvia la base oficial. No la passis mai al verificador.
    """
    base = copy.deepcopy(carrega_oficial(escenari, semestre))
    xifres = alumnes_recerca()
    for s in base.sessions.values():
        if s.alumnes == 0 and (s.codi, s.grup) in xifres:
            s.alumnes = xifres[(s.codi, s.grup)]
    return base


@dataclass
class Assignacio:
    dia: str          # L M X J V
    h_ini: str        # HH:MM
    aula: str         # '' si no en necessita (PLAB amb aula del departament, dobles sense espai)
    data: str = ''    # només per a la sessió recuperada del 5.3 (AAAA-MM-DD)


@dataclass
class Proposta:
    """Una proposta: id_sessio -> Assignacio. Una fila per sessió."""
    files: dict[str, Assignacio] = field(default_factory=dict)

    @classmethod
    def de_base(cls, base: Base) -> 'Proposta':
        """L'horari d'avui de totes les sessions de la base (el punt de partida)."""
        return cls({sid: Assignacio(s.dia, fmt(s.ini), s.aula) for sid, s in base.sessions.items()})

    @classmethod
    def llegeix(cls, path: Path) -> 'Proposta':
        with open(path, encoding='utf-8-sig', newline='') as f:
            return cls({r['id_sessio']: Assignacio(r['dia'], r['h_ini'], r['aula'], r.get('data') or '')
                        for r in csv.DictReader(f)})

    def escriu(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        amb_data = any(a.data for a in self.files.values())
        cols = ['id_sessio', 'dia', 'h_ini', 'aula'] + (['data'] if amb_data else [])
        with open(path, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(cols)
            for sid in sorted(self.files):
                a = self.files[sid]
                w.writerow([sid, a.dia, a.h_ini, a.aula] + ([a.data] if amb_data else []))
        return path

    def a_files(self) -> list[Fila]:
        """En el format del verificador, per cridar `avalua` sense passar per disc."""
        return [Fila(sid, a.dia, a.h_ini, a.aula, i + 2, a.data) for i, (sid, a) in enumerate(sorted(self.files.items()))]


@dataclass
class Informe:
    """El JSON del verificador oficial. El veredicte es llegeix d'aquí, mai del codi de sortida."""
    json: dict
    sortida: str

    @property
    def veredicte(self) -> str:
        return self.json['veredicte']

    @property
    def valida(self) -> bool:
        return self.veredicte == 'VALIDA'

    @property
    def objectius(self) -> dict:
        return self.json['objectius']

    def compten(self) -> dict[str, int]:
        """Incompliments que compten, per regla (només les que en tenen)."""
        return {k: v['compten'] for k, v in self.json['restriccions'].items() if v.get('compten')}


def verifica(proposta: Path, *, escenari: Path | None = None, referencia: Path | None = None,
             relaxacions: Path | None = None, nomes_aules: bool = False, json_path: Path | None = None,
             violacions_path: Path | None = None) -> Informe:
    """Executa `python -m horaris check` (la mateixa ordre que el jurat) des de la carpeta del repte."""
    with tempfile.TemporaryDirectory() as tmp:
        jp = Path(json_path) if json_path else Path(tmp) / 'informe.json'
        cmd = [str(PYTHON), '-m', 'horaris', 'check', str(Path(proposta).resolve()), '--semestre', str(SEMESTRE),
               '--json', str(jp.resolve())]
        if escenari:
            cmd += ['--escenari', str(Path(escenari).resolve())]
        if referencia:
            cmd += ['--referencia', str(Path(referencia).resolve())]
        if relaxacions:
            cmd += ['--relaxacions', str(Path(relaxacions).resolve())]
        if nomes_aules:
            cmd.append('--nomes-aules')
        if violacions_path:
            cmd += ['--violacions', str(Path(violacions_path).resolve())]
        r = subprocess.run(cmd, cwd=REPTE, capture_output=True, text=True)
        if r.returncode == 2 or not jp.exists():
            raise RuntimeError(f'El verificador no ha pogut llegir la proposta:\n{r.stderr or r.stdout}')
        return Informe(json.loads(jp.read_text(encoding='utf-8')), r.stdout)


def avalua_rapid(base: Base, proposta: Proposta, *, nomes_aules: bool = False, referencia: Proposta | None = None):
    """Crida `avalua` en memòria (sense disc ni subprocés), per iterar de pressa dins del solver.

    `base` ha de ser la de `carrega_oficial()`. Per al lliurament, fes servir sempre `verifica()`.
    """
    ref = referencia.a_files() if referencia else None
    return avalua(base, proposta.a_files(), referencia=ref, nomes_aules=nomes_aules)
