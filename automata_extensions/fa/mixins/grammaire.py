"""
GrammaireMixin
==============

Passage d'un automate à une grammaire régulière (linéaire à droite) :

- `to_grammar()` : grammaire équivalente. Chaque état devient un
  non-terminal (son nom, en texte), l'état initial est l'axiome ; une
  transition p --a--> q donne la règle  p -> a q , et chaque état final f
  donne  f -> ε . Les epsilon-transitions sont d'abord supprimées, pour
  n'avoir que des règles de la forme `A -> a B` ou `A -> ε`.
- `derivation_tree(mot)` : suite des étapes de dérivation d'un mot
  accepté (voir `automata_extensions.grammar.DerivationStep`).

Le passage inverse (grammaire -> NFA) est `ExtendedNFA.from_grammar` et
`ExtendedNFA.from_grammar_string`.
"""
from ...grammar.grammar import DerivationStep, Grammar, Rule
from ..fa import _cle_tri


def _noms_non_terminaux(etats):
    """Nom de chaque état en tant que non-terminal : le nom lui-même
    pour une chaîne, sinon son écriture texte reproductible. Lève
    `ValueError` si deux états ont le même nom une fois écrits."""
    noms = {
        etat: (etat if isinstance(etat, str) else _cle_tri(etat))
        for etat in etats
    }
    if len(set(noms.values())) != len(noms):
        raise ValueError(
            "Deux états portent le même nom une fois écrits en texte : "
            "renommez-les avant de construire une grammaire."
        )
    return noms


def _chemin_acceptant(automate, mot):
    """Un chemin (liste de triplets (source, lettre, cible)) qui lit
    `mot` depuis l'état initial jusqu'à un état final, ou `None` s'il n'y
    en a pas. `automate` ne doit pas avoir d'epsilon-transition.

    Parcours par couches (une couche par lettre lue), en mémorisant pour
    chaque état atteint la transition par laquelle on y est arrivé ;
    l'ordre de parcours est fixé, donc le chemin choisi est reproductible.
    Complexité : O(|mot| · (|Q| + |E|))."""
    aretes = {}
    for source, lettre, cible in automate._labeled_edges():
        aretes.setdefault(source, []).append((lettre, cible))
    for liste in aretes.values():
        liste.sort(key=lambda t: (str(t[0]), _cle_tri(t[1])))

    couches = [{automate.initial_state: None}]
    for lettre in mot:
        suivante = {}
        for source in sorted(couches[-1], key=_cle_tri):
            for etiquette, cible in aretes.get(source, []):
                if etiquette == lettre and cible not in suivante:
                    suivante[cible] = (source, lettre)
        if not suivante:
            return None
        couches.append(suivante)

    finals = [e for e in couches[-1] if e in automate.final_states]
    if not finals:
        return None
    etat = min(finals, key=_cle_tri)
    chemin = []
    for i in range(len(mot), 0, -1):
        source, lettre = couches[i][etat]
        chemin.append((source, lettre, etat))
        etat = source
    chemin.reverse()
    return chemin


class GrammaireMixin:
    """Mixin grammaire, à utiliser avec `ExtendedFA`."""

    def to_grammar(self):
        """Grammaire régulière linéaire à droite équivalente à
        l'automate (voir la docstring du module). Les règles sont
        rangées de façon reproductible : l'axiome d'abord, puis les
        autres non-terminaux par ordre alphabétique ; pour chacun, les
        règles `A -> a B` triées par lettre puis par cible, et la règle
        `A -> ε` en dernier.

        Complexité : O(|Q| + |E|) après suppression des
        epsilon-transitions.
        """
        automate = self.remove_epsilon_transitions()
        noms = _noms_non_terminaux(automate.states)
        depart = noms[automate.initial_state]

        regles_de = {noms[etat]: [] for etat in automate.states}
        for source, lettre, cible in automate._labeled_edges():
            regles_de[noms[source]].append(
                Rule(noms[source], lettre, noms[cible])
            )
        regles_vides = {
            noms[etat]: Rule(noms[etat], "", None)
            for etat in automate.final_states
        }

        regles = []
        for non_terminal in [depart] + sorted(n for n in regles_de
                                              if n != depart):
            regles.extend(
                sorted(regles_de[non_terminal],
                       key=lambda r: (r.word, r.right))
            )
            if non_terminal in regles_vides:
                regles.append(regles_vides[non_terminal])
        return Grammar(start=depart, rules=tuple(regles))

    def derivation_tree(self, word):
        """Dérivation (gauche) de `word` dans la grammaire de
        l'automate, sous forme d'une chaîne d'étapes
        `DerivationStep` ; l'étape renvoyée est la première.

        Pour un DFA, la dérivation est unique ; pour un NFA, on garde le
        premier chemin trouvé dans un ordre fixé. Lève `ValueError` si
        `word` n'est pas accepté.

        Exemple (DFA : nombre de 'a' multiple de 3) :
            derivation_tree("aaa").sequence()
            -> '0 => a1 => aa2 => aaa0 => aaa'

        Complexité : O(|word| · (|Q| + |E|)).
        """
        automate = self.remove_epsilon_transitions()
        chemin = _chemin_acceptant(automate, word)
        if chemin is None:
            raise ValueError(f"Le mot {word!r} n'est pas accepté.")
        noms = _noms_non_terminaux(automate.states)

        dernier = chemin[-1][2] if chemin else automate.initial_state
        etape = DerivationStep(
            prefix=word,
            non_terminal=noms[dernier],
            rule=Rule(noms[dernier], "", None),
            next=DerivationStep(
                prefix=word, non_terminal=None, rule=None, next=None
            ),
        )
        for i in range(len(chemin) - 1, -1, -1):
            source, lettre, cible = chemin[i]
            etape = DerivationStep(
                prefix=word[:i],
                non_terminal=noms[source],
                rule=Rule(noms[source], lettre, noms[cible]),
                next=etape,
            )
        return etape
