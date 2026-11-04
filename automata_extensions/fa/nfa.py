"""ExtendedNFA : NFA de automata-lib étendu par les mixins du projet."""
from __future__ import annotations

from automata.fa.nfa import NFA

from ..regex.regex import lettres, parse, thompson
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

    @classmethod
    def from_regex(cls, regex, *, input_symbols=None):
        """NFA (avec epsilon-transitions) reconnaissant le langage d'une
        expression régulière, par la construction de Thompson.

        Syntaxe acceptée : lettres, `|`, `*`, `+`, `?`, `()` (mot vide),
        `.` (n'importe quelle lettre de `input_symbols`) et `∅` (langage
        vide). Si `input_symbols` n'est pas donné, l'alphabet est formé
        des lettres de l'expression. Lève `ValueError` en cas d'erreur de
        syntaxe ou de lettre hors de l'alphabet.

        Complexité : O(n) pour une expression de taille n.
        """
        expression = parse(regex, input_symbols)
        alphabet = (
            set(input_symbols) if input_symbols is not None
            else lettres(expression)
        )
        etats, transitions, initial, final = thompson(expression)
        return cls(
            states=etats,
            input_symbols=alphabet,
            transitions=transitions,
            initial_state=initial,
            final_states={final},
        )
