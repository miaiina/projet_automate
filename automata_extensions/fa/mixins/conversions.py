"""
ConversionsMixin
================

Conversions entre représentations : NFA -> DFA, automate -> regex,
suppression des epsilon-transitions, regex -> NFA (Thompson).

Statut : squelette (phase 3 du projet, pas encore implémenté).

Méthodes prévues :
- epsilon_closure(state)          : fermeture epsilon d'un état
- remove_epsilon_transitions()    : nouvel automate sans epsilon-transitions
- to_dfa() / determinize()        : construction par sous-ensembles
- to_regex()                      : élimination d'états (passage par GNFA)
- to_regex_optimum()              : élimination d'états avec heuristique
                                     de choix de l'ordre (poids des regex)
- to_regex_arden()                : résolution par équations d'Arden
- brzozowski_minimize()           : minimisation par double inversion +
                                     déterminisation (Brzozowski)
- from_regex() / thompson()       : construction de Thompson (regex -> NFA
                                     avec epsilon-transitions)
"""


class ConversionsMixin:
    """Mixin de conversions, à utiliser avec `ExtendedFA`."""
