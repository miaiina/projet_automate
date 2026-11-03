"""ExtendedGNFA : GNFA de automata-lib étendu par les mixins du projet."""
from __future__ import annotations

from automata.fa.gnfa import GNFA

from .fa import ExtendedFA
from .mixins.analyse import AnalyseMixin
from .mixins.visualisation import VisualisationMixin


class ExtendedGNFA(
    AnalyseMixin,
    VisualisationMixin,
    ExtendedFA,
    GNFA,
):
    """GNFA étendu.

    Pas de ConversionsMixin ni de GrammaireMixin ici : le GNFA est
    lui-même l'outil interne utilisé par `to_regex()` (élimination
    d'états) pour convertir un DFA/NFA en expression régulière ; il
    n'a pas vocation à être construit directement par l'utilisateur.
    """

    def _successors(self, state):
        """Un GNFA relie chaque paire d'états par une regex (ou None
        s'il n'y a pas d'arête). Complexité : O(|Q|)."""
        return {
            target
            for target, regex in self.transitions.get(state, {}).items()
            if regex is not None
        }
