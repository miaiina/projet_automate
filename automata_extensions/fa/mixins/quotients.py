"""
QuotientMixin
=============

Quotients d'un langage et d'un automate :

- `left_quotient_word(mot)` : {w : mot·w dans L} (on lit d'abord `mot`) ;
- `right_quotient_word(mot)` : {w : w·mot dans L} ;
- `residual_automaton()` : automate des résiduels (quotients à gauche
  par un mot) du langage, c'est-à-dire l'automate minimal complet, avec
  des états nommés `q0`, `q1`... ;
- `quotient_by(application)` : fusion d'états selon une application.

Les noms portent le suffixe `_word` pour ne pas entrer en collision avec
`NFA.left_quotient` / `right_quotient` d'automata-lib, qui prennent un
automate (et non un mot) en argument.

`_minimal_complet` est aussi utilisé par `AlgebreMixin`.
"""
from collections import deque

from .operations import _completer_sur, _vers_dfa

EPSILON = ""


def _automate_vide(dfa):
    """DFA du langage vide, réduit à l'état initial de `dfa`."""
    return dfa._build(
        states={dfa.initial_state},
        transitions={dfa.initial_state: {}},
        initial_state=dfa.initial_state,
        final_states=set(),
    )


def _minimal_complet(automate):
    """DFA minimal complet du langage de `automate`, dont les états sont
    tous accessibles (états nommés par un représentant de chaque classe).
    Étapes : déterminisation si besoin, complétion, restriction aux
    états accessibles, minimisation de Moore."""
    dfa = _vers_dfa(automate)
    dfa = _completer_sur(dfa, dfa.input_symbols)
    dfa = dfa.induced_subautomaton(dfa.accessible_states())
    return dfa.minimize()


class QuotientMixin:
    """Mixin de quotients, à utiliser avec `ExtendedFA`."""

    # ------------------------------------------------------------------
    # Quotients par un mot
    # ------------------------------------------------------------------

    def left_quotient_word(self, word):
        """DFA du quotient à gauche par un mot : {w : word·w est dans
        L(self)}. On lit `word` depuis l'état initial, et l'état atteint
        devient l'état initial ; si la lecture est bloquée, le résultat
        est le langage vide. Un NFA est d'abord déterminisé.

        Complexité : O(|word|) après déterminisation éventuelle.
        """
        dfa = _vers_dfa(self)
        etat = dfa.initial_state
        for lettre in word:
            table = dfa.transitions.get(etat, {})
            if lettre not in table:
                return _automate_vide(dfa)
            etat = table[lettre]
        return dfa._build(
            states=set(dfa.states),
            transitions={e: dict(t) for e, t in dfa.transitions.items()},
            initial_state=etat,
            final_states=set(dfa.final_states),
        )

    def right_quotient_word(self, word):
        """DFA du quotient à droite par un mot : {w : w·word est dans
        L(self)}. Un état devient final si lire `word` depuis lui mène à
        un état final. Un NFA est d'abord déterminisé.

        Complexité : O(|Q| · |word|) après déterminisation éventuelle.
        """
        dfa = _vers_dfa(self)

        def apres(etat):
            for lettre in word:
                table = dfa.transitions.get(etat, {})
                if lettre not in table:
                    return None
                etat = table[lettre]
            return etat

        finals = {
            e for e in dfa.states if apres(e) in dfa.final_states
        }
        return dfa._build(
            states=set(dfa.states),
            transitions={e: dict(t) for e, t in dfa.transitions.items()},
            initial_state=dfa.initial_state,
            final_states=finals,
        )

    # ------------------------------------------------------------------
    # Résiduels
    # ------------------------------------------------------------------

    def residual_automaton(self):
        """Automate des résiduels du langage : un état par quotient à
        gauche distinct w⁻¹L, la transition par a allant de w⁻¹L à
        (wa)⁻¹L. C'est l'automate minimal complet ; ses états sont nommés
        `q0`, `q1`... dans l'ordre où on les découvre en lisant les mots
        du plus court au plus long (`q0` est L lui-même).

        Complexité : celle de la minimisation (O(|Q|² · |Σ|)) plus
        O(|Q| · |Σ|) pour le renommage.
        """
        from ..dfa import ExtendedDFA

        minimal = _minimal_complet(self)
        symboles = sorted(minimal.input_symbols, key=str)
        nom = {minimal.initial_state: "q0"}
        file = deque([minimal.initial_state])
        while file:
            etat = file.popleft()
            for lettre in symboles:
                cible = minimal.transitions[etat][lettre]
                if cible not in nom:
                    nom[cible] = f"q{len(nom)}"
                    file.append(cible)
        return ExtendedDFA(
            states=set(nom.values()),
            input_symbols=set(minimal.input_symbols),
            transitions={
                nom[e]: {a: nom[minimal.transitions[e][a]] for a in symboles}
                for e in nom
            },
            initial_state="q0",
            final_states={nom[e] for e in minimal.final_states if e in nom},
        )

    # ------------------------------------------------------------------
    # Fusion d'états
    # ------------------------------------------------------------------

    def quotient_by(self, state_map):
        """NFA obtenu en fusionnant les états selon `state_map` (un
        dictionnaire état -> nouvel état, défini pour tous les états). Une
        transition p --a--> q devient f(p) --a--> f(q) ; l'état initial et
        les états finaux sont remplacés par leurs images.

        Contrairement à `minimize`, la fusion n'est pas forcément une
        congruence : le résultat peut être non déterministe (d'où un NFA)
        et reconnaître plus de mots que l'automate d'origine.

        `ValueError` si un état n'a pas d'image. Complexité : O(|Q| + |E|).
        """
        from ..nfa import ExtendedNFA

        manquants = set(self.states) - set(state_map)
        if manquants:
            raise ValueError(
                "state_map doit définir une image pour chaque état ; "
                f"manquants : {sorted(map(str, manquants))}"
            )
        transitions = {state_map[e]: {} for e in self.states}
        for source, symbole, cible in self._labeled_edges():
            transitions[state_map[source]].setdefault(symbole, set()).add(
                state_map[cible]
            )
        return ExtendedNFA(
            states=set(transitions),
            input_symbols=set(self.input_symbols) - {EPSILON},
            transitions=transitions,
            initial_state=state_map[self.initial_state],
            final_states={state_map[f] for f in self.final_states},
        )
