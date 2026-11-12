"""
PasAPasMixin
============

Les algorithmes du cours montrés étape par étape, comme on les déroule sur
une copie : on ne donne pas seulement le résultat, mais tout ce qui y
mène.

- `determinization_steps()` / `determinization_table()` : construction par
  sous-ensembles d'un NFA, ligne par ligne, dans l'ordre où on découvre
  les sous-ensembles ;
- `moore_partitions()` / `moore_partitions_str()` : partitions successives
  P0, P1, ... de l'algorithme de Moore (les états sont regroupés tant qu'on
  ne peut pas les distinguer), jusqu'à la partition stable ;
- `to_regex_steps()` / `to_regex_steps_str()` : élimination d'états, avec
  l'automate généralisé (arêtes étiquetées par des expressions) après
  chaque suppression, et possibilité de choisir l'ordre de suppression.

Chaque version `_str` renvoie du texte à afficher avec `print`.
"""
from collections import deque

from automata.fa.dfa import DFA

from ...regex.regex import to_string
from ..fa import _as_set, _cle_tri
from .visualisation import _formater_table

EPSILON = ""


def _nom_ensemble(ensemble):
    """Écriture d'un ensemble d'états : `{1,2}`, ou `∅` s'il est vide."""
    if not ensemble:
        return "∅"
    return "{" + ",".join(sorted(_nom_court(e) for e in ensemble)) + "}"


def _nom_court(etat):
    return etat if isinstance(etat, str) else _cle_tri(etat)


class PasAPasMixin:
    """Mixin « pas à pas », à utiliser avec `ExtendedFA`."""

    # ------------------------------------------------------------------
    # Déterminisation
    # ------------------------------------------------------------------

    def determinization_steps(self):
        """Étapes de la construction par sous-ensembles d'un NFA (avec ou
        sans epsilon-transitions) : liste de couples (sous-ensemble,
        {symbole : sous-ensemble atteint}), dans l'ordre où les
        sous-ensembles sont découverts (parcours en largeur, symboles dans
        l'ordre alphabétique). Le premier est la fermeture epsilon de
        l'état initial ; le sous-ensemble vide apparaît s'il est atteint.

        `NotImplementedError` pour un DFA (déjà déterministe).
        Complexité : celle de `determinize`.
        """
        if isinstance(self, DFA):
            raise NotImplementedError(
                "determinization_steps() ne s'applique qu'à un NFA : un "
                "DFA est déjà déterministe."
            )
        symboles = sorted(set(self.input_symbols) - {EPSILON}, key=str)
        depart = frozenset(self.epsilon_closure(self.initial_state))
        vus = {depart}
        file = deque([depart])
        etapes = []
        while file:
            sous_ensemble = file.popleft()
            cibles = {}
            for symbole in symboles:
                atteints = set()
                for etat in sous_ensemble:
                    atteints |= _as_set(
                        self.transitions.get(etat, {}).get(symbole, ())
                    )
                cible = frozenset(self.epsilon_closure_of_set(atteints))
                cibles[symbole] = cible
                if cible not in vus:
                    vus.add(cible)
                    file.append(cible)
            etapes.append((sous_ensemble, cibles))
        return etapes

    def determinization_table(self):
        """Table de la construction par sous-ensembles, en texte : une
        ligne par sous-ensemble (`->` pour l'initial, `*` s'il contient un
        état final), une colonne par symbole.

        Exemple :
                    | a       | b
            --------+---------+------
            -> {1}  | {1,2}   | {1}
               {1,2}| {1,2,3} | {1,3}
        """
        etapes = self.determinization_steps()
        symboles = list(etapes[0][1]) if etapes else []
        etiquettes = []
        for indice, (sous_ensemble, _) in enumerate(etapes):
            marque = ("->" if indice == 0 else "") + (
                "*" if sous_ensemble & set(self.final_states) else ""
            )
            etiquettes.append(marque + _nom_ensemble(sous_ensemble))
        cellules = [
            [_nom_ensemble(cibles[s]) for s in symboles]
            for _, cibles in etapes
        ]
        return _formater_table(etiquettes, symboles, cellules)

    # ------------------------------------------------------------------
    # Partitions de Moore
    # ------------------------------------------------------------------

    def moore_partitions(self):
        """Partitions successives de l'algorithme de Moore : P0 sépare les
        états finaux des autres ; P(k+1) sépare deux états de la même
        classe de P(k) dès qu'une lettre les envoie dans deux classes
        différentes de P(k). On s'arrête quand la partition ne change plus.

        Renvoie la liste [P0, P1, ..., Pn] ; chaque partition est une liste
        de `frozenset`, triée par plus petit nom d'état. La dernière
        partition est celle des classes d'équivalence (voir
        `equivalence_classes`). Défini pour un DFA complet.

        Complexité : O(|Q|² · |Σ|) dans le pire cas.
        """
        self._verifier_dfa_complet("moore_partitions")
        etats = sorted(self.states, key=_cle_tri)
        symboles = sorted(self.input_symbols, key=str)

        def trier(blocs):
            return sorted(
                (frozenset(b) for b in blocs),
                key=lambda b: min(_cle_tri(e) for e in b),
            )

        finals = {e for e in etats if e in self.final_states}
        partition = trier(b for b in (finals, set(etats) - finals) if b)
        historique = [partition]
        while True:
            classe = {e: i for i, bloc in enumerate(partition) for e in bloc}
            groupes = {}
            for etat in etats:
                signature = (classe[etat],) + tuple(
                    classe[self.transitions[etat][s]] for s in symboles
                )
                groupes.setdefault(signature, set()).add(etat)
            nouvelle = trier(groupes.values())
            if len(nouvelle) == len(partition):
                return historique
            partition = nouvelle
            historique.append(partition)

    def moore_partitions_str(self):
        """Les partitions de `moore_partitions()` en texte, une par ligne :

            P0 : {3} | {1,2,4,5,6,7,8}
            P1 : ...
        """
        return "\n".join(
            f"P{i} : " + " | ".join(_nom_ensemble(b) for b in partition)
            for i, partition in enumerate(self.moore_partitions())
        )

    # ------------------------------------------------------------------
    # Élimination d'états
    # ------------------------------------------------------------------

    def to_regex_steps(self, order=None):
        """Étapes de l'élimination d'états. On ajoute un état « début »
        (relié à l'état initial par le mot vide) et un état « fin » (relié
        depuis chaque état final), puis on supprime les états un par un.

        Renvoie une liste de dictionnaires, un par étape :
        `{"supprime": état ou None, "aretes": [(source, cible, expression),
        ...]}`. La première étape (`supprime` vaut `None`) est l'automate
        de départ ; la dernière n'a plus qu'une arête de "début" à "fin",
        dont l'expression est le résultat (c'est celle de `to_regex()` si
        `order` n'est pas donné). Les expressions sont écrites dans le
        style du cours (voir `to_regex`).

        `order` : liste des états dans l'ordre où les supprimer (par
        défaut, ordre alphabétique). `ValueError` si ce n'est pas une
        permutation des états. Complexité : celle de `to_regex`.
        """
        self._verifier_symboles_pour_regex()
        ordre = (
            self._ordre_lexicographique() if order is None else list(order)
        )
        if sorted(map(_cle_tri, ordre)) != sorted(
            map(_cle_tri, self.states)
        ) or len(set(ordre)) != len(self.states):
            raise ValueError(
                "order doit contenir chaque état exactement une fois."
            )
        journal = []
        self._eliminer_etats(ordre, journal=journal)

        def rang(nom):
            if nom == "début" and nom not in self.states:
                return (0, "")
            if nom == "fin" and nom not in self.states:
                return (2, "")
            return (1, _cle_tri(nom))

        etapes = []
        for supprime, table in journal:
            aretes = sorted(table, key=lambda a: (rang(a[0]), rang(a[1])))
            etapes.append({
                "supprime": supprime,
                "aretes": [
                    (_nom_court(p), _nom_court(q),
                     to_string(table[(p, q)], verbeux=True))
                    for p, q in aretes
                ],
            })
        return etapes

    def to_regex_steps_str(self, order=None):
        """Les étapes de `to_regex_steps()` en texte :

            Départ :
              début -> 1 : ()
              1 -> 2 : a
            Suppression de 1 :
              ...
        """
        blocs = []
        for etape in self.to_regex_steps(order):
            titre = (
                "Départ :" if etape["supprime"] is None
                else f"Suppression de {_nom_court(etape['supprime'])} :"
            )
            lignes = [f"  {p} -> {q} : {r}" for p, q, r in etape["aretes"]]
            blocs.append("\n".join([titre] + lignes))
        return "\n".join(blocs)
