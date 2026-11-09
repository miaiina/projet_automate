"""
GrapheMixin
===========

L'automate vu comme un graphe orienté (états = sommets, transitions =
arcs), sans tenir compte des étiquettes : accessibilité d'un état,
parcours en largeur et en profondeur, cycles, composantes fortement
connexes, sous-automate induit.

Toutes ces méthodes s'appuient sur `_successors` de `ExtendedFA` : elles
valent donc pour un DFA comme pour un NFA (epsilon-transitions comprises).
Les parcours essaient les successeurs dans l'ordre alphabétique des noms
d'états, pour des résultats reproductibles.
"""
from collections import deque

from ..fa import _cle_tri


def _a_un_cycle(automate, depart=None):
    """Vrai si le graphe de transitions contient un cycle ; si `depart`
    est donné, seulement un cycle atteignable depuis cet état. Parcours
    en profondeur itératif à trois couleurs : blanc (pas vu), gris (en
    cours), noir (terminé) ; un cycle existe dès qu'on retombe sur un état
    gris. Complexité : O(|Q| + |E|)."""
    blanc, gris, noir = 0, 1, 2
    couleur = {etat: blanc for etat in automate.states}
    departs = [depart] if depart is not None else list(automate.states)
    for debut in departs:
        if couleur[debut] != blanc:
            continue
        couleur[debut] = gris
        pile = [(debut, iter(automate._successors(debut)))]
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


class GrapheMixin:
    """Mixin de graphe, à utiliser avec `ExtendedFA`."""

    def _verifier_etat(self, etat):
        if etat not in self.states:
            raise ValueError(f"État inconnu : {etat!r}")

    # ------------------------------------------------------------------
    # Accessibilité d'un état donné
    # ------------------------------------------------------------------

    def reachable_states(self, state):
        """États atteignables depuis `state` (lui-même compris) : comme
        `accessible_states()`, mais depuis un état quelconque.
        Complexité : O(|Q| + |E|)."""
        self._verifier_etat(state)
        vus = {state}
        a_traiter = [state]
        while a_traiter:
            for suivant in self._successors(a_traiter.pop()):
                if suivant not in vus:
                    vus.add(suivant)
                    a_traiter.append(suivant)
        return vus

    def is_accessible(self, state):
        """Vrai si `state` est atteignable depuis l'état initial."""
        self._verifier_etat(state)
        return state in self.accessible_states()

    def is_coaccessible(self, state):
        """Vrai si un état final est atteignable depuis `state`."""
        self._verifier_etat(state)
        return state in self.coaccessible_states()

    # ------------------------------------------------------------------
    # Parcours
    # ------------------------------------------------------------------

    def bfs(self, start=None):
        """Parcours en largeur : liste des états atteignables dans
        l'ordre de visite, depuis l'état initial ou depuis `start`.
        Complexité : O(|Q| + |E|)."""
        depart = self.initial_state if start is None else start
        self._verifier_etat(depart)
        ordre = [depart]
        vus = {depart}
        file = deque([depart])
        while file:
            for suivant in sorted(self._successors(file.popleft()),
                                  key=_cle_tri):
                if suivant not in vus:
                    vus.add(suivant)
                    ordre.append(suivant)
                    file.append(suivant)
        return ordre

    def dfs(self, start=None, *, recursive=False):
        """Parcours en profondeur (ordre préfixe) : liste des états
        atteignables dans l'ordre de visite, depuis l'état initial ou
        depuis `start`. Itératif par défaut ; `recursive=True` donne le
        même résultat avec une récursion (limitée par la profondeur de
        pile de Python). Complexité : O(|Q| + |E|)."""
        depart = self.initial_state if start is None else start
        self._verifier_etat(depart)
        ordre, vus = [], set()
        if recursive:
            def visiter(etat):
                vus.add(etat)
                ordre.append(etat)
                for suivant in sorted(self._successors(etat), key=_cle_tri):
                    if suivant not in vus:
                        visiter(suivant)
            visiter(depart)
            return ordre
        pile = [depart]
        while pile:
            etat = pile.pop()
            if etat in vus:
                continue
            vus.add(etat)
            ordre.append(etat)
            for suivant in sorted(self._successors(etat), key=_cle_tri,
                                  reverse=True):
                if suivant not in vus:
                    pile.append(suivant)
        return ordre

    # ------------------------------------------------------------------
    # Cycles et composantes fortement connexes
    # ------------------------------------------------------------------

    def has_cycle(self):
        """Vrai si le graphe de transitions contient un cycle (une boucle
        sur un état en est un). Complexité : O(|Q| + |E|)."""
        return _a_un_cycle(self)

    def has_cycle_from(self, state):
        """Vrai s'il existe un cycle atteignable depuis `state`."""
        self._verifier_etat(state)
        return _a_un_cycle(self, state)

    def strongly_connected_components(self):
        """Composantes fortement connexes (algorithme de Tarjan, itératif) :
        liste de `frozenset`, triée par plus petit nom d'état. Deux états
        sont dans la même composante si chacun est atteignable depuis
        l'autre ; un état seul sans boucle forme une composante à lui
        seul. Complexité : O(|Q| + |E|)."""
        index, bas, sur_la_pile = {}, {}, set()
        pile, composantes = [], []
        compteur = 0
        for depart in sorted(self.states, key=_cle_tri):
            if depart in index:
                continue
            index[depart] = bas[depart] = compteur
            compteur += 1
            pile.append(depart)
            sur_la_pile.add(depart)
            travail = [(depart, iter(sorted(self._successors(depart),
                                            key=_cle_tri)))]
            while travail:
                etat, suivants = travail[-1]
                descendu = False
                for suivant in suivants:
                    if suivant not in index:
                        index[suivant] = bas[suivant] = compteur
                        compteur += 1
                        pile.append(suivant)
                        sur_la_pile.add(suivant)
                        travail.append((suivant, iter(sorted(
                            self._successors(suivant), key=_cle_tri))))
                        descendu = True
                        break
                    if suivant in sur_la_pile:
                        bas[etat] = min(bas[etat], index[suivant])
                if descendu:
                    continue
                travail.pop()
                if travail:
                    parent = travail[-1][0]
                    bas[parent] = min(bas[parent], bas[etat])
                if bas[etat] == index[etat]:
                    composante = set()
                    while True:
                        membre = pile.pop()
                        sur_la_pile.discard(membre)
                        composante.add(membre)
                        if membre == etat:
                            break
                    composantes.append(frozenset(composante))
        return sorted(
            composantes, key=lambda c: min(_cle_tri(e) for e in c)
        )

    def is_strongly_connected(self):
        """Vrai si le graphe n'a qu'une composante fortement connexe."""
        return len(self.strongly_connected_components()) == 1

    # ------------------------------------------------------------------
    # Sous-automate, alias
    # ------------------------------------------------------------------

    def induced_subautomaton(self, states):
        """Sous-automate induit par un sous-ensemble d'états : on garde
        ces états et les transitions entre eux, l'état initial et les
        états finaux qui y sont. `ValueError` si un état est inconnu ou si
        l'état initial n'est pas dans le sous-ensemble. Le résultat peut
        être partiel. Complexité : O(|states| · |Σ|)."""
        sous_ensemble = set(states)
        inconnus = sous_ensemble - set(self.states)
        if inconnus:
            raise ValueError(f"États inconnus : {sorted(map(str, inconnus))}")
        if self.initial_state not in sous_ensemble:
            raise ValueError(
                "L'état initial doit appartenir au sous-ensemble d'états."
            )
        return self._build(
            states=sous_ensemble,
            transitions=self._filtered_transitions(sous_ensemble),
            initial_state=self.initial_state,
            final_states=set(self.final_states) & sous_ensemble,
        )

    def accepts(self, word):
        """Alias pédagogique de `accepts_input`."""
        return self.accepts_input(word)
