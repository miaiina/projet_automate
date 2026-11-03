"""ExtendedNFA : NFA de automata-lib étendu par les mixins du projet."""
from __future__ import annotations

from automata.fa.nfa import NFA

from .fa import ExtendedFA
from .mixins.analyse import AnalyseMixin
from .mixins.conversions import ConversionsMixin
from .mixins.grammaire import GrammaireMixin
from .mixins.visualisation import VisualisationMixin


class ExtendedNFA(
    AnalyseMixin,
    ConversionsMixin,
    GrammaireMixin,
    VisualisationMixin,
    ExtendedFA,
    NFA,
):
    """NFA étendu (epsilon-transitions comprises)."""

    def _successors(self, state):
        """Pour un NFA : un ensemble d'états cibles par symbole,
        epsilon-transitions comprises. Complexité : O(|Σ| + d)."""
        successors = set()
        for targets in self.transitions.get(state, {}).values():
            successors |= _as_set(targets)
        return successors

    def _build(self, states, transitions, initial_state, final_states):
        """Construit un nouvel ExtendedNFA."""
        return ExtendedNFA(
            states=set(states),
            input_symbols=self.input_symbols,
            transitions=transitions,
            initial_state=initial_state,
            final_states=set(final_states),
        )

    def _filtered_transitions(self, states):
        """Transitions de `self` restreintes à `states` (NFA : un
        ensemble de cibles par symbole ; les cibles hors de `states`
        sont retirées, et le symbole est omis si plus aucune cible ne
        reste). Complexité : O(|states| · |Σ| · d)."""
        states = set(states)
        transitions = {}
        for state in states:
            transitions[state] = {}
            for symbol, targets in self.transitions.get(state, {}).items():
                restants = _as_set(targets) & states
                if restants:
                    transitions[state][symbol] = restants
        return transitions


def _as_set(targets):
    """Les transitions d'un NFA sont censées associer un ensemble
    d'états à chaque symbole, mais les exemples du poly (voir
    `exemple_automates.py`) utilisent parfois directement une chaîne
    comme '1' pour un seul état cible. Cette fonction uniformise les
    deux cas."""
    if isinstance(targets, str):
        return {targets}
    return set(targets)
