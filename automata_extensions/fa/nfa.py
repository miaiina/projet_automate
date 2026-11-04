"""ExtendedNFA : NFA de automata-lib étendu par les mixins du projet."""
from __future__ import annotations

from automata.fa.nfa import NFA

from .fa import ExtendedFA, _as_set
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

    def _labeled_edges(self):
        """Triplets (source, symbole, cible), epsilon-transitions
        comprises (symbole `""`). Complexité : O(|Q| · |Σ| · d)."""
        for etat, table in self.transitions.items():
            for symbole, cibles in table.items():
                for cible in _as_set(cibles):
                    yield (etat, symbole, cible)

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

    def eliminate_lambda(self):
        """Redirige vers `remove_epsilon_transitions()` : la méthode
        d'origine d'automata-lib échoue sur ExtendedNFA (voir la
        documentation du projet)."""
        return self.remove_epsilon_transitions()
