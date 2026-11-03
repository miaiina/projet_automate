"""
ConversionsMixin
================

Conversions entre représentations d'automates.

Phase 3a (ce fichier, actuellement) :
- `epsilon_closure`, `epsilon_closure_of_set`
- `remove_epsilon_transitions`
- `determinize` / `to_dfa` (construction par sous-ensembles)
- `complete` (ajout d'un état-puits)

Phase 3b (à venir) : `to_regex`, `to_regex_optimum`, `to_regex_arden`,
`reverse`, `brzozowski_minimize`, construction de Thompson.

Convention d'automata-lib : une epsilon-transition est une transition
étiquetée par la chaîne vide `""` (et non par un symbole 'ϵ' : celui-ci
n'est qu'un symbole ordinaire pour la bibliothèque).
"""
from automata.fa.dfa import DFA
from automata.fa.nfa import NFA

from ..fa import _as_set

EPSILON = ""


class ConversionsMixin:
    """Mixin de conversions, à utiliser avec `ExtendedFA`."""

    # ------------------------------------------------------------------
    # Fermeture epsilon
    # ------------------------------------------------------------------

    def _epsilon_successors(self, state):
        """États atteignables depuis `state` par UNE epsilon-transition
        (ensemble vide pour un DFA, qui n'en a pas)."""
        return _as_set(self.transitions.get(state, {}).get(EPSILON, ()))

    def epsilon_closure(self, state):
        """Fermeture epsilon de `state` : `state` lui-même et tous les
        états atteignables par des epsilon-transitions uniquement
        (parcours en largeur). Complexité : O(|Q| + |E_ε|)."""
        return self.epsilon_closure_of_set({state})

    def epsilon_closure_of_set(self, states):
        """Fermeture epsilon d'un ensemble d'états (union des fermetures
        de chacun). Complexité : O(|Q| + |E_ε|)."""
        fermeture = set(states)
        a_traiter = list(fermeture)
        while a_traiter:
            etat = a_traiter.pop()
            for suivant in self._epsilon_successors(etat):
                if suivant not in fermeture:
                    fermeture.add(suivant)
                    a_traiter.append(suivant)
        return fermeture

    # ------------------------------------------------------------------
    # Suppression des epsilon-transitions
    # ------------------------------------------------------------------

    def remove_epsilon_transitions(self):
        """NFA équivalent sans epsilon-transition, avec les mêmes états.

        Pour chaque état q et chaque symbole a (différent de epsilon) :
            delta'(q, a) = union des delta(p, a) pour p dans eps(q)
        et q est final dans le nouvel automate dès que eps(q) contient
        un état final (eps(q) = fermeture epsilon de q).

        Aucune fermeture n'est appliquée "après" la lecture de a : elle
        sera faite au pas suivant, ou par la règle des états finaux.

        Un automate sans epsilon-transition (en particulier un DFA)
        est renvoyé tel quel.

        Complexité : O(|Q| · (|Q| + |E_ε|) + |Q| · |Σ| · |Q|) dans cette
        version pédagogique (la fermeture est recalculée pour chaque état).
        """
        if not isinstance(self, NFA):
            return self
        if not any(EPSILON in t for t in self.transitions.values()):
            return self

        nouvelles_transitions = {}
        for etat in self.states:
            nouvelles_transitions[etat] = {}
            for p in self.epsilon_closure(etat):
                for symbole, cibles in self.transitions.get(p, {}).items():
                    if symbole == EPSILON:
                        continue
                    nouvelles_transitions[etat].setdefault(
                        symbole, set()
                    ).update(_as_set(cibles))

        nouveaux_finals = {
            etat for etat in self.states
            if self.epsilon_closure(etat) & self.final_states
        }
        return self._build(
            states=self.states,
            transitions=nouvelles_transitions,
            initial_state=self.initial_state,
            final_states=nouveaux_finals,
        )

    # ------------------------------------------------------------------
    # Déterminisation (construction par sous-ensembles)
    # ------------------------------------------------------------------

    def determinize(self):
        """DFA complet équivalent, par la construction des sous-ensembles.

        Les états du DFA sont des `frozenset` d'états du NFA. L'état
        initial est la fermeture epsilon de l'état initial ; pour un
        sous-ensemble S et un symbole a, la cible est la fermeture
        epsilon de l'union des delta(q, a), q dans S. Un sous-ensemble
        est final s'il contient un état final. Seuls les sous-ensembles
        accessibles sont construits ; le sous-ensemble vide (état-puits)
        apparaît s'il est atteint.

        Un DFA est renvoyé tel quel.

        Complexité : O(2^|Q| · |Σ| · |Q|) dans le pire cas (le nombre de
        sous-ensembles accessibles peut être exponentiel).
        """
        if isinstance(self, DFA):
            return self

        from ..dfa import ExtendedDFA  # import local : évite un cycle

        symboles = set(self.input_symbols) - {EPSILON}
        initial = frozenset(self.epsilon_closure(self.initial_state))
        transitions = {}
        a_traiter = [initial]
        while a_traiter:
            sous_ensemble = a_traiter.pop()
            if sous_ensemble in transitions:
                continue
            transitions[sous_ensemble] = {}
            for symbole in symboles:
                atteints = set()
                for etat in sous_ensemble:
                    atteints |= _as_set(
                        self.transitions.get(etat, {}).get(symbole, ())
                    )
                cible = frozenset(self.epsilon_closure_of_set(atteints))
                transitions[sous_ensemble][symbole] = cible
                if cible not in transitions:
                    a_traiter.append(cible)

        return ExtendedDFA(
            states=set(transitions),
            input_symbols=symboles,
            transitions=transitions,
            initial_state=initial,
            final_states={
                s for s in transitions if s & self.final_states
            },
        )

    def to_dfa(self):
        """Alias de `determinize()`."""
        return self.determinize()

    # ------------------------------------------------------------------
    # Complétion
    # ------------------------------------------------------------------

    def complete(self, sink_state="puits"):
        """DFA complet équivalent : si la fonction de transition n'est
        pas totale, ajoute un état-puits (non final, bouclant sur tous
        les symboles) vers lequel pointent toutes les transitions
        manquantes. Un DFA déjà complet est renvoyé tel quel.

        Lève `ValueError` si le nom `sink_state` est déjà un état de
        l'automate, et `NotImplementedError` pour un automate non
        déterministe (déterminisez d'abord avec `to_dfa()`).

        Complexité : O(|Q| · |Σ|).
        """
        if not isinstance(self, DFA):
            raise NotImplementedError(
                "complete() n'est défini que pour un DFA "
                "(déterminisez d'abord avec to_dfa())."
            )
        if self.is_complete():
            return self
        if sink_state in self.states:
            raise ValueError(
                f"Le nom d'état {sink_state!r} existe déjà ; choisissez un "
                "autre nom avec complete(sink_state=...)."
            )

        transitions = {
            etat: {
                symbole: self.transitions.get(etat, {}).get(symbole, sink_state)
                for symbole in self.input_symbols
            }
            for etat in self.states
        }
        transitions[sink_state] = {
            symbole: sink_state for symbole in self.input_symbols
        }
        return self._build(
            states=set(self.states) | {sink_state},
            transitions=transitions,
            initial_state=self.initial_state,
            final_states=self.final_states,
        )
