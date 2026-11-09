"""
AlgebreMixin
============

Notions algébriques sur les langages et les automates :

- `syntactic_monoid()` : monoïde syntaxique du langage ;
- `is_morphism_to(other, state_map)` : une application entre états
  est-elle un morphisme d'automates ? ;
- `project(application)` : renommage ou effacement de lettres ;
- `is_prefix_closed()`, `prefix_closed_sublanguage()` : clôture par
  préfixe.
"""
from collections import deque

from ..fa import _cle_tri
from .operations import _aretes, _vers_dfa
from .quotients import _automate_vide, _minimal_complet

EPSILON = ""


class AlgebreMixin:
    """Mixin d'algèbre des langages, à utiliser avec `ExtendedFA`."""

    # ------------------------------------------------------------------
    # Monoïde syntaxique
    # ------------------------------------------------------------------

    def syntactic_monoid(self):
        """Monoïde syntaxique du langage, calculé comme le monoïde de
        transitions de l'automate minimal complet : chaque lettre agit
        sur les états, et le monoïde est l'ensemble des actions de tous
        les mots (l'identité correspond au mot vide).

        Renvoie un dictionnaire { plus court mot : action }, où l'action
        est un dictionnaire { état : état atteint en lisant ce mot }, sur
        les états de l'automate minimal (voir `minimize()`). Le nombre
        d'éléments est `len(automate.syntactic_monoid())`. Les mots sont
        découverts du plus court au plus long, par ordre alphabétique.

        Complexité : O(|M| · |Σ| · |Q|) où |M| est la taille du monoïde
        (qui peut être exponentielle en |Q|), plus celle de la
        minimisation.
        """
        minimal = _minimal_complet(self)
        etats = sorted(minimal.states, key=_cle_tri)
        symboles = sorted(minimal.input_symbols, key=str)
        identite = tuple(etats)
        elements = {identite: ""}
        file = deque([identite])
        while file:
            action = file.popleft()
            for lettre in symboles:
                suivante = tuple(
                    minimal.transitions[image][lettre] for image in action
                )
                if suivante not in elements:
                    elements[suivante] = elements[action] + lettre
                    file.append(suivante)
        return {
            mot: dict(zip(etats, action)) for action, mot in elements.items()
        }

    # ------------------------------------------------------------------
    # Morphismes et projection
    # ------------------------------------------------------------------

    def is_morphism_to(self, other, state_map):
        """Vrai si `state_map` (dictionnaire état de self -> état de
        `other`) est un morphisme d'automates de self vers `other` :

        - chaque état de self a une image, qui est un état de `other` ;
        - l'état initial a pour image l'état initial de `other` ;
        - un état est final si et seulement si son image l'est ;
        - toute transition p --a--> q de self a pour image la transition
          f(p) --a--> f(q), qui doit exister dans `other`.

        Un morphisme conserve le langage reconnu. Renvoie `False` (et ne
        lève pas d'exception) si une de ces conditions n'est pas remplie.
        Complexité : O(|Q| + |E|).
        """
        if any(e not in state_map for e in self.states):
            return False
        if any(state_map[e] not in other.states for e in self.states):
            return False
        if state_map[self.initial_state] != other.initial_state:
            return False
        for etat in self.states:
            if (etat in self.final_states) != (
                state_map[etat] in other.final_states
            ):
                return False
        aretes_de_other = set(_aretes(other))
        return all(
            (state_map[p], a, state_map[q]) in aretes_de_other
            for p, a, q in _aretes(self)
        )

    def project(self, mapping):
        """NFA obtenu en changeant les lettres selon `mapping` (lettre ->
        nouvelle lettre, ou `None` pour effacer la lettre : la transition
        devient une epsilon-transition). Les lettres absentes de
        `mapping` sont conservées. Le langage obtenu est l'image du
        langage d'origine par le morphisme de mots correspondant.

        Exemple : avec {"a": "x", "b": None}, le mot "abab" devient "xx".

        `ValueError` si une image n'est ni `None` ni une chaîne d'un seul
        caractère. Complexité : O(|Q| + |E|).
        """
        from ..nfa import ExtendedNFA

        for lettre, image in mapping.items():
            if image is not None and (
                not isinstance(image, str) or len(image) != 1
            ):
                raise ValueError(
                    f"L'image de {lettre!r} doit être None ou une lettre "
                    f"unique, pas {image!r}."
                )
        transitions = {e: {} for e in self.states}
        alphabet = set()
        for source, symbole, cible in self._labeled_edges():
            nouveau = EPSILON if symbole == EPSILON else mapping.get(
                symbole, symbole
            )
            if nouveau is None:
                nouveau = EPSILON
            if nouveau != EPSILON:
                alphabet.add(nouveau)
            transitions[source].setdefault(nouveau, set()).add(cible)
        for symbole in self.input_symbols:
            if symbole != EPSILON:
                image = mapping.get(symbole, symbole)
                if image is not None:
                    alphabet.add(image)
        return ExtendedNFA(
            states=set(self.states),
            input_symbols=alphabet,
            transitions=transitions,
            initial_state=self.initial_state,
            final_states=set(self.final_states),
        )

    # ------------------------------------------------------------------
    # Clôture par préfixe
    # ------------------------------------------------------------------

    def is_prefix_closed(self):
        """Vrai si le langage est clos par préfixe : tout préfixe d'un
        mot du langage est dans le langage. Il suffit que tous les états
        utiles (accessibles et coaccessibles) soient finaux : un état
        utile atteint par un préfixe u peut être prolongé en un mot du
        langage, donc u doit lui-même être dans le langage. Le langage
        vide est clos par préfixe. Un NFA est d'abord déterminisé.

        Complexité : O(|Q| + |E|) après déterminisation éventuelle.
        """
        dfa = _vers_dfa(self)
        utiles = dfa.accessible_states() & dfa.coaccessible_states()
        if dfa.initial_state not in utiles:
            return True
        return utiles <= set(dfa.final_states)

    def prefix_closed_sublanguage(self):
        """DFA du plus grand sous-langage clos par préfixe : les mots
        du langage dont tous les préfixes sont aussi dans le langage. On
        ne garde que les états finaux (et les transitions entre eux). Si
        l'état initial n'est pas final, le résultat est le langage vide.
        Un NFA est d'abord déterminisé. Complexité : O(|Q| · |Σ|).
        """
        dfa = _vers_dfa(self)
        if dfa.initial_state not in dfa.final_states:
            return _automate_vide(dfa)
        return dfa.induced_subautomaton(set(dfa.final_states))
