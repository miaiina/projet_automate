"""ExtendedNFA : NFA de automata-lib étendu par les mixins du projet."""
from __future__ import annotations

from automata.fa.nfa import NFA

from ..grammar.grammar import Grammar
from ..regex.regex import lettres, parse, thompson
from .fa import ExtendedFA, _as_set
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


class ExtendedNFA(
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

    def copy(self):
        """Copie indépendante de l'automate (mêmes états, alphabet,
        transitions, état initial et états finaux). Complexité :
        O(|Q| · |Σ| · d)."""
        return ExtendedNFA(
            states=set(self.states),
            input_symbols=set(self.input_symbols),
            transitions={
                e: {a: set(_as_set(c)) for a, c in t.items()}
                for e, t in self.transitions.items()
            },
            initial_state=self.initial_state,
            final_states=set(self.final_states),
        )

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

    @classmethod
    def from_grammar(cls, grammar, *, input_symbols=None):
        """NFA reconnaissant le langage d'une grammaire régulière
        (linéaire à droite).

        Les états sont les non-terminaux (l'axiome est l'état initial),
        plus un état final supplémentaire `F` et des états intermédiaires
        quand une règle produit plusieurs lettres :
        - A -> a B    donne la transition  A --a--> B ;
        - A -> a      donne la transition  A --a--> F ;
        - A -> w B    (mot w de plusieurs lettres) passe par des états
          intermédiaires, un par lettre ;
        - A -> B      donne une epsilon-transition  A --ε--> B ;
        - A -> ε      rend A final.

        `input_symbols` doit contenir tous les terminaux de la grammaire
        (`ValueError` sinon) ; par défaut, ce sont exactement les
        terminaux. Complexité : O(taille totale des règles).
        """
        terminaux = set(grammar.terminals)
        alphabet = terminaux if input_symbols is None else set(input_symbols)
        if not terminaux <= alphabet:
            raise ValueError(
                "Terminaux absents de input_symbols : "
                f"{sorted(terminaux - alphabet)}"
            )

        etats = set(grammar.non_terminals)

        def nom_frais(base):
            nom = base
            while nom in etats:
                nom += "'"
            etats.add(nom)
            return nom

        final = nom_frais("F")
        finals = {final}
        transitions = {}

        def relier(source, symbole, cible):
            transitions.setdefault(source, {}).setdefault(
                symbole, set()
            ).add(cible)

        for regle in grammar.rules:
            cible = regle.right if regle.right is not None else final
            if regle.word == "":
                if regle.right is None:
                    finals.add(regle.left)
                else:
                    relier(regle.left, "", cible)
                continue
            courant = regle.left
            for lettre in regle.word[:-1]:
                suivant = nom_frais(f"{regle.left}.{lettre}")
                relier(courant, lettre, suivant)
                courant = suivant
            relier(courant, regle.word[-1], cible)

        for etat in etats:
            transitions.setdefault(etat, {})
        return cls(
            states=etats,
            input_symbols=alphabet,
            transitions=transitions,
            initial_state=grammar.start,
            final_states=finals,
        )

    @classmethod
    def from_grammar_string(cls, texte, *, input_symbols=None):
        """NFA d'une grammaire écrite en texte au format classique, par
        exemple `"S -> aS | b"` (voir `Grammar.from_string`)."""
        return cls.from_grammar(
            Grammar.from_string(texte), input_symbols=input_symbols
        )
