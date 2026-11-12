"""ExtendedDFA : DFA de automata-lib étendu par les mixins du projet."""
from __future__ import annotations

from automata.fa.dfa import DFA

from .fa import ExtendedFA
from .mixins.analyse import AnalyseMixin
from .mixins.conversions import ConversionsMixin
from .mixins.algebre import AlgebreMixin
from .mixins.grammaire import GrammaireMixin
from .mixins.graphe import GrapheMixin
from .mixins.quotients import QuotientMixin
from .mixins.operations import OperationsMixin
from .mixins.pas_a_pas import PasAPasMixin
from .mixins.relations import RelationsMixin
from .mixins.visualisation import VisualisationMixin


class ExtendedDFA(
    AnalyseMixin,
    ConversionsMixin,
    OperationsMixin,
    PasAPasMixin,
    RelationsMixin,
    GrapheMixin,
    QuotientMixin,
    AlgebreMixin,
    GrammaireMixin,
    VisualisationMixin,
    ExtendedFA,
    DFA,
):
    """DFA étendu par les mixins pédagogiques du projet.

    S'utilise exactement comme `automata.fa.dfa.DFA` :

        from automata_extensions.fa import ExtendedDFA
        a = ExtendedDFA(states=..., input_symbols=..., transitions=...,
                         initial_state=..., final_states=...)
        a.accessible_states()   # une fois le mixin analyse implémenté
    """

    def _successors(self, state):
        """Pour un DFA : un seul état cible par symbole.
        Complexité : O(|Σ|)."""
        return set(self.transitions.get(state, {}).values())

    def copy(self):
        """Copie indépendante de l'automate (mêmes états, alphabet,
        transitions, état initial, états finaux et option
        `allow_partial`). Complexité : O(|Q| · |Σ|)."""
        return ExtendedDFA(
            states=set(self.states),
            input_symbols=set(self.input_symbols),
            transitions={e: dict(t) for e, t in self.transitions.items()},
            initial_state=self.initial_state,
            final_states=set(self.final_states),
            allow_partial=self.allow_partial,
        )

    def _labeled_edges(self):
        """Triplets (source, symbole, cible). Complexité : O(|Q| · |Σ|)."""
        for etat, table in self.transitions.items():
            for symbole, cible in table.items():
                yield (etat, symbole, cible)

    def _build(self, states, transitions, initial_state, final_states):
        """Construit un nouvel ExtendedDFA. `allow_partial=True` car
        les automates produits par `trim()` ou des quotients peuvent
        ne plus être complets (c'est au mixin `conversions`, phase 3,
        de les recompléter si besoin)."""
        return ExtendedDFA(
            states=set(states),
            input_symbols=self.input_symbols,
            transitions=transitions,
            initial_state=initial_state,
            final_states=set(final_states),
            allow_partial=True,
        )

    def _filtered_transitions(self, states):
        """Transitions de `self` restreintes à `states` (DFA : une
        seule cible par symbole). Complexité : O(|states| · |Σ|)."""
        states = set(states)
        return {
            state: {
                symbol: target
                for symbol, target in self.transitions.get(state, {}).items()
                if target in states
            }
            for state in states
        }
