"""Regla d'alumnat compartit, additiva respecte del verificador oficial.

Una cohort és una etiqueta completa de ``titulacions_curs`` (p. ex. GXX:1r).
La mida només es considera coneguda si es proporciona explícitament, o si
només hi ha un grup TE diferent a tota la cohort: aleshores és el màxim
d'alumnes d'aquest TE. No sumem sessions recurrents ni línies de teoria.
Un grup cobreix tota la cohort si alumnes >= mida coneguda positiva, o si
és TE i la cohort només té una etiqueta de grup TE, encara que falti aforament.

Amb una sola teoria només admetem subgrups paral·lels si tots dos són PAUL,
la regla oficial els considera separats, els números són el número complet
del TE seguit de sufixos diferents de la mateixa longitud, i els aforaments
positius sumen com a màxim la mida del TE. És la convenció de subgrups
germans de l'esquema; PAUL/91 i PAUL/92 no són germans de TE/91.
Qualsevol altra combinació amb una sola teoria es prohibeix per prudència.
En cohorts amb diverses teories i mida desconeguda conservem la regla oficial.
La mateixa unitat física queda exempta al consumidor, no en aquesta regla.
"""
from collections import defaultdict

from horaris.check import _alumnat_comparteix


class ReglaAlumnat:
    def __init__(self, sessions, *, mides=None):
        self.teories = defaultdict(set)
        self.mides_te = defaultdict(int)
        maxims = defaultdict(int)
        for s in sessions:
            if s.tipus == 'TE':
                for coh in s.cohorts:
                    self.teories[coh].add(s.grup)
                    self.mides_te[coh, s.grup] = max(self.mides_te[coh, s.grup], s.alumnes)
                    maxims[coh] = max(maxims[coh], s.alumnes)
        self.mides = {c: n for c, n in maxims.items()
                      if len(self.teories[c]) == 1 and n > 0}
        self.mides.update(mides or {})

    def completa(self, s, cohort):
        mida = self.mides.get(cohort, 0)
        return ((mida > 0 and s.alumnes >= mida)
                or (s.tipus == 'TE' and len(self.teories[cohort]) == 1))

    def __call__(self, a, b):
        if _alumnat_comparteix(a, b):
            return True
        return any(self.completa(a, c) or self.completa(b, c)
                   or (len(self.teories[c]) == 1 and not self.germans(a, b, c))
                   for c in set(a.cohorts) & set(b.cohorts))

    def germans(self, a, b, cohort):
        if a.tipus != 'PAUL' or b.tipus != 'PAUL':
            return False
        if not (a.alumnes > 0 and b.alumnes > 0):
            return False
        for grup in self.teories[cohort]:
            if a.alumnes + b.alumnes > self.mides_te[cohort, grup]:
                continue
            parent = grup.split('/')[-1]
            na, nb = a.grup.split('/')[-1], b.grup.split('/')[-1]
            if (na != nb and len(na) == len(nb) > len(parent)
                    and na.startswith(parent) and nb.startswith(parent)):
                return True
        return False
