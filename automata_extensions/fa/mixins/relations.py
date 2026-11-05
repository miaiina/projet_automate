"""
RelationsMixin
==============

Propriétés d'un langage et relations entre deux automates :

- `is_empty`, `is_finite`, `shortest_word` ;
- `is_included_in`, `is_equivalent`, `is_disjoint_from`, et les
  contre-exemples correspondants (`inclusion_counterexample`,
  `equivalence_counterexample`) ;
- `is_isomorphic_to` : isomorphisme d'automates (renommage bijectif des
  états qui conserve état initial, états finaux et transitions), notion
  plus forte que l'équivalence de langages.

Les relations de langage passent par les opérations booléennes de
`OperationsMixin` : L1 est inclus dans L2 si et seulement si L1 \\ L2 est
vide ; L1 et L2 sont égaux si et seulement si leur différence symétrique
est vide.
"""
from collections import deque

from automata.fa.dfa import DFA

from .operations import _vers_dfa


def _accessibles(dfa):
    """États accessibles d'un DFA (valable aussi pour un DFA
    d'automata-lib qui n'est pas une classe `Extended...`)."""
    vus = {dfa.initial_state}
    a_traiter = [dfa.initial_state]
    while a_traiter:
        etat = a_traiter.pop()
        for suivant in dfa.transitions.get(etat, {}).values():
            if suivant not in vus:
                vus.add(suivant)
                a_traiter.append(suivant)
    return vus


def _a_un_cycle(automate):
    """Vrai si le graphe de transitions (par `_successors`) contient un
    cycle. Parcours en profondeur itératif, avec trois couleurs :
    blanc (pas vu), gris (en cours), noir (terminé) ; un cycle existe
    dès qu'on retombe sur un état gris. Complexité : O(|Q| + |E|)."""
    blanc, gris, noir = 0, 1, 2
    couleur = {etat: blanc for etat in automate.states}
    for depart in automate.states:
        if couleur[depart] != blanc:
            continue
        couleur[depart] = gris
        pile = [(depart, iter(automate._successors(depart)))]
        while pile:
            etat, suivants = pile[-1]
            for suivant in suivants:
                if couleur[suivant] == gris:
                    return True
                if couleur[suivant] == blanc:
                    couleur[suivant] = gris
                    pile.append(
                        (suivant, iter(automate._successors(suivant)))
                    )
                    break
            else:
                couleur[etat] = noir
                pile.pop()
    return False


class RelationsMixin:
    """Mixin de propriétés et de relations, à utiliser avec `ExtendedFA`."""

    # ------------------------------------------------------------------
    # Propriétés d'un langage
    # ------------------------------------------------------------------

    def is_empty(self):
        """Vrai si le langage est vide : aucun état final n'est
        accessible. Complexité : O(|Q| + |E|)."""
        return not (self.accessible_states() & set(self.final_states))

    def is_finite(self):
        """Vrai si le langage est fini : une fois les epsilon-transitions
        supprimées et l'automate réduit à ses états utiles (`trim`), il
        ne reste aucun cycle. Un cycle d'epsilon-transitions seules ne
        rend pas le langage infini, d'où la suppression préalable.

        Complexité : celle de `remove_epsilon_transitions` et `trim`,
        plus O(|Q| + |E|) pour la recherche de cycle.
        """
        utile = self.remove_epsilon_transitions().trim()
        return not _a_un_cycle(utile)

    def shortest_word(self):
        """Plus court mot du langage (le plus petit dans l'ordre
        alphabétique parmi les plus courts), ou `None` si le langage est
        vide. Parcours en largeur du DFA équivalent, en essayant les
        symboles dans l'ordre. Complexité : O(|Q| · |Σ|) après
        déterminisation éventuelle."""
        dfa = _vers_dfa(self)
        if dfa.initial_state in dfa.final_states:
            return ""
        symboles = sorted(dfa.input_symbols, key=str)
        vus = {dfa.initial_state}
        file = deque([(dfa.initial_state, "")])
        while file:
            etat, mot = file.popleft()
            table = dfa.transitions.get(etat, {})
            for symbole in symboles:
                if symbole not in table:
                    continue
                cible = table[symbole]
                if cible in vus:
                    continue
                if cible in dfa.final_states:
                    return mot + symbole
                vus.add(cible)
                file.append((cible, mot + symbole))
        return None

    # ------------------------------------------------------------------
    # Relations entre langages
    # ------------------------------------------------------------------

    def inclusion_counterexample(self, other):
        """Plus court mot de L(self) qui n'est pas dans L(other), ou
        `None` si L(self) est inclus dans L(other). Complexité : celle de
        `difference` plus celle de `shortest_word`."""
        return self.difference(other).shortest_word()

    def is_included_in(self, other):
        """Vrai si L(self) est inclus dans L(other) (inclusion au sens
        large). Complexité : celle de `inclusion_counterexample`."""
        return self.inclusion_counterexample(other) is None

    def equivalence_counterexample(self, other):
        """Plus court mot qui est dans exactement un des deux langages,
        ou `None` si les langages sont égaux. Complexité : celle de
        `symmetric_difference` plus celle de `shortest_word`."""
        return self.symmetric_difference(other).shortest_word()

    def is_equivalent(self, other):
        """Vrai si les deux automates reconnaissent le même langage.
        Complexité : celle de `equivalence_counterexample`."""
        return self.equivalence_counterexample(other) is None

    def is_disjoint_from(self, other):
        """Vrai si les deux langages n'ont aucun mot en commun.
        Complexité : celle de `intersection` plus O(|Q|·|Σ|)."""
        return self.intersection(other).is_empty()

    # ------------------------------------------------------------------
    # Isomorphisme d'automates
    # ------------------------------------------------------------------

    def is_isomorphic_to(self, other):
        """Vrai s'il existe un renommage bijectif des états de `self` vers
        ceux de `other` qui conserve l'état initial, les états finaux et
        les transitions (isomorphisme d'automates déterministes).

        Seules les parties accessibles sont comparées : un état
        inaccessible est ignoré. Les deux automates doivent être des DFA
        (`NotImplementedError` sinon) et avoir le même alphabet. Deux DFA
        minimaux d'un même langage sont toujours isomorphes.

        Comme le DFA est déterministe, l'image de l'état initial fixe
        celle de tous les autres : on construit le renommage en parcourant
        les deux automates ensemble. Complexité : O(|Q| · |Σ|).
        """
        if not (isinstance(self, DFA) and isinstance(other, DFA)):
            raise NotImplementedError(
                "is_isomorphic_to() n'est défini que pour deux DFA "
                "(déterminisez d'abord avec to_dfa())."
            )
        if set(self.input_symbols) != set(other.input_symbols):
            return False
        if len(_accessibles(self)) != len(_accessibles(other)):
            return False

        renommage = {self.initial_state: other.initial_state}
        a_traiter = [self.initial_state]
        while a_traiter:
            p = a_traiter.pop()
            q = renommage[p]
            if (p in self.final_states) != (q in other.final_states):
                return False
            table_p = self.transitions.get(p, {})
            table_q = other.transitions.get(q, {})
            if set(table_p) != set(table_q):
                return False
            for symbole, cible_p in table_p.items():
                cible_q = table_q[symbole]
                if cible_p in renommage:
                    if renommage[cible_p] != cible_q:
                        return False
                else:
                    renommage[cible_p] = cible_q
                    a_traiter.append(cible_p)
        return len(set(renommage.values())) == len(renommage)
