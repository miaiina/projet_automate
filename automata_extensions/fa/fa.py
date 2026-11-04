"""
Classe de base commune à toutes les extensions d'automates finis.

`ExtendedFA` ne réimplémente aucun algorithme : elle expose une petite
interface indépendante du type concret d'automate (DFA, NFA, GNFA), afin
que les mixins de haut niveau (accessibilité, minimisation, conversions,
visualisation...) puissent être écrits une seule fois et fonctionner
sur les trois classes à la fois.

Chaque sous-classe concrète (`ExtendedDFA`, `ExtendedNFA`, `ExtendedGNFA`)
doit fournir `_successors`, car le format du dictionnaire de
transitions diffère d'une classe à l'autre :
- DFA   : transitions[état][symbole] -> état
- NFA   : transitions[état][symbole] -> ensemble d'états
- GNFA  : transitions[état][état]    -> regex (ou None s'il n'y a pas
          d'arête)
"""
from __future__ import annotations

from automata.fa.fa import FA


def _as_set(targets):
    """Uniformise une valeur de transition de NFA en ensemble d'états.

    Les transitions d'un NFA associent un ensemble d'états à chaque
    symbole, mais les exemples du poly (voir `exemple_automates.py`)
    utilisent parfois directement une chaîne comme '1' pour un seul état
    cible. Cette fonction accepte les deux écritures.
    """
    if isinstance(targets, str):
        return {targets}
    return set(targets)


def _cle_tri(etat):
    """Clé de tri reproductible pour des états quelconques.

    `sorted(..., key=str)` n'est pas reproductible d'une exécution à
    l'autre pour des états de type `frozenset` (l'ordre d'affichage des
    éléments d'un ensemble dépend du hachage) ; cette clé trie d'abord
    les éléments internes.
    """
    if isinstance(etat, (frozenset, set)):
        return "{" + ",".join(sorted(_cle_tri(e) for e in etat)) + "}"
    return str(etat)


class ExtendedFA(FA):
    """Interface commune utilisée par tous les mixins de l'extension."""

    def _successors(self, state):
        """Retourne l'ensemble des états directement atteignables depuis
        `state`, tous symboles confondus (y compris les epsilon-
        transitions pour un NFA).

        Complexité : O(d) où d est le degré sortant de `state`.

        À implémenter dans chaque sous-classe concrète.
        """
        raise NotImplementedError(
            "_successors doit être implémenté par la sous-classe concrète "
            "(ExtendedDFA, ExtendedNFA ou ExtendedGNFA)."
        )

    def _is_final(self, state) -> bool:
        """Teste si `state` est un état final. Complexité : O(1)."""
        return state in self.final_states

    def _build(self, states, transitions, initial_state, final_states):
        """Construit un nouvel automate du même type concret que `self`
        (même classe, mêmes `input_symbols`), à partir d'un nouvel
        ensemble d'états, de transitions, d'un état initial et d'états
        finaux.

        Utilisé par les mixins (ex. `trim()`, `minimize()`) pour
        produire un nouvel automate sans connaître le format exact des
        transitions de la classe concrète (DFA, NFA...).

        À implémenter dans chaque sous-classe concrète.
        """
        raise NotImplementedError(
            "_build doit être implémenté par la sous-classe concrète "
            "(ExtendedDFA ou ExtendedNFA)."
        )

    def _filtered_transitions(self, states):
        """Retourne le dictionnaire de transitions de `self`, restreint
        aux états de `states` : toute transition vers un état hors de
        `states` est supprimée.

        Utilisé par `trim()`. À implémenter dans chaque sous-classe
        concrète (le format du dictionnaire diffère entre DFA et NFA).
        """
        raise NotImplementedError(
            "_filtered_transitions doit être implémenté par la sous-classe "
            "concrète (ExtendedDFA ou ExtendedNFA)."
        )

    def _labeled_edges(self):
        """Énumère les transitions sous la forme (source, symbole,
        cible), une par triplet ; le symbole vaut `""` pour une
        epsilon-transition.

        À implémenter dans chaque sous-classe concrète (un DFA a une
        seule cible par symbole, un NFA un ensemble de cibles).
        """
        raise NotImplementedError(
            "_labeled_edges doit être implémenté par la sous-classe "
            "concrète (ExtendedDFA ou ExtendedNFA)."
        )

    def _edges(self):
        """Énumère les arêtes du graphe de transition sous la forme
        (état_source, état_cible).

        Implémentation générique à partir de `_successors` ; les
        sous-classes peuvent la surcharger si elles ont besoin du
        symbole associé à chaque arête (utile pour l'affichage).

        Complexité : O(|Q| + |E|) où E est l'ensemble des arêtes.
        """
        for state in self.states:
            for target in self._successors(state):
                yield (state, target)
