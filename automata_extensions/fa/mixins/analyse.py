"""
AnalyseMixin
============

Analyse structurelle d'un automate : accessibilité, "nettoyage" (trim),
distinguabilité des états, minimisation.

- `accessible_states`, `coaccessible_states`, `useful_states`, `is_trim`
  et `trim` sont écrits au niveau `FA` (via `_successors`/`_edges` de
  `ExtendedFA`) et fonctionnent donc sur `ExtendedDFA`, `ExtendedNFA`
  et `ExtendedGNFA` indifféremment.
- `distinguishable_states`, `pair_table_str`, `print_pair_table`,
  `equivalence_classes`, `is_minimal` et `minimize` utilisent
  l'algorithme des tables (Moore), qui suppose un automate
  **déterministe et complet** ; ils ne sont donc définis que pour un
  DFA complet (voir `is_complete`). Pour un DFA incomplet, complétez-le
  d'abord avec `complete()` (voir `ConversionsMixin`).

Ces algorithmes sont volontairement pédagogiques : pas d'optimisation
de type Hopcroft, pas de mémoïsation superflue.
"""
from itertools import combinations

from automata.fa.dfa import DFA

from ..fa import _as_set, _cle_tri


def _nom_court(etat):
    """Nom d'un état pour l'affichage : lui-même pour une chaîne, sinon
    son écriture reproductible."""
    return etat if isinstance(etat, str) else _cle_tri(etat)


class AnalyseMixin:
    """Mixin d'analyse structurelle, à utiliser avec `ExtendedFA`."""

    # ------------------------------------------------------------------
    # Accessibilité
    # ------------------------------------------------------------------

    def accessible_states(self):
        """États atteignables depuis l'état initial (parcours en
        largeur). Complexité : O(|Q| + |E|)."""
        vus = {self.initial_state}
        a_traiter = [self.initial_state]
        while a_traiter:
            etat = a_traiter.pop()
            for suivant in self._successors(etat):
                if suivant not in vus:
                    vus.add(suivant)
                    a_traiter.append(suivant)
        return vus

    def coaccessible_states(self):
        """États depuis lesquels on peut atteindre un état final
        (parcours en largeur sur le graphe des transitions inversé).
        Complexité : O(|Q| + |E|)."""
        predecesseurs = {etat: set() for etat in self.states}
        for source, cible in self._edges():
            predecesseurs[cible].add(source)

        vus = set(self.final_states)
        a_traiter = list(self.final_states)
        while a_traiter:
            etat = a_traiter.pop()
            for pred in predecesseurs[etat]:
                if pred not in vus:
                    vus.add(pred)
                    a_traiter.append(pred)
        return vus

    def useful_states(self):
        """États à la fois accessibles et coaccessibles.
        Complexité : celle de `accessible_states` + `coaccessible_states`."""
        return self.accessible_states() & self.coaccessible_states()

    def is_trim(self):
        """Vrai si tous les états de l'automate sont utiles."""
        return self.useful_states() == self.states

    def trim(self):
        """Nouvel automate restreint aux états utiles (accessibles ET
        coaccessibles). Cas particulier : si l'état initial lui-même
        n'est pas utile, le langage reconnu est vide ; on renvoie alors
        un automate réduit au seul état initial, sans transition.

        Complexité : celle de `useful_states` + O(|states| · |Σ|) pour
        reconstruire les transitions.
        """
        utiles = self.useful_states()
        if self.initial_state not in utiles:
            # Langage vide : l'état initial seul, sans aucune transition
            # (même pas une boucle sur lui-même).
            return self._build(
                states={self.initial_state},
                transitions={self.initial_state: {}},
                initial_state=self.initial_state,
                final_states=set(),
            )
        return self._build(
            states=utiles,
            transitions=self._filtered_transitions(utiles),
            initial_state=self.initial_state,
            final_states=self.final_states & utiles,
        )

    # ------------------------------------------------------------------
    # Déterminisme et complétude (prérequis des méthodes ci-dessous)
    # ------------------------------------------------------------------

    def is_deterministic(self):
        """Vrai si la fonction de transition est déterministe : au plus
        un état cible par état et par symbole, et aucune
        epsilon-transition. Un DFA l'est toujours. Complexité :
        O(|Q| · |Σ|)."""
        if isinstance(self, DFA):
            return True
        for table in self.transitions.values():
            for symbole, cibles in table.items():
                cibles = _as_set(cibles)
                if (symbole == "" and cibles) or len(cibles) > 1:
                    return False
        return True

    def is_complete(self):
        """Vrai si chaque état a une transition définie pour chaque
        symbole de l'alphabet. Complexité : O(|Q| · |Σ|)."""
        return all(
            symbole in self.transitions.get(etat, {})
            for etat in self.states
            for symbole in self.input_symbols
        )

    # ------------------------------------------------------------------
    # Distinguabilité et minimisation (DFA complet uniquement)
    # ------------------------------------------------------------------

    def _verifier_dfa_complet(self, nom_methode):
        if not isinstance(self, DFA):
            raise NotImplementedError(
                f"{nom_methode}() n'est implémenté que pour un DFA dans "
                "cette version pédagogique (déterminisez d'abord avec "
                "to_dfa())."
            )
        if not self.is_complete():
            raise ValueError(
                f"{nom_methode}() nécessite un DFA complet ; complétez-le "
                "d'abord avec complete()."
            )

    def pair_table(self):
        """Table des paires, par l'algorithme de remplissage de table
        (Moore) : dictionnaire qui associe à chaque paire d'états
        (un `frozenset` de deux états) le numéro du passage où elle a été
        reconnue distinguable, ou `None` si les deux états sont
        équivalents.

        - Passage 0 : les paires (état final, état non final).
        - Passage k >= 1 : une paire (p, q) est marquée dès qu'il existe
          une lettre a telle que (delta(p,a), delta(q,a)) est déjà marquée.

        Comme dans le cours, on parcourt les paires dans l'ordre
        alphabétique (1,2), (1,3), ..., (2,3), ... et les lettres dans
        l'ordre alphabétique, et une paire marquée pendant un passage est
        immédiatement utilisable par les paires suivantes du même
        passage : le numéro d'une paire peut donc être plus petit que la
        longueur du plus court mot qui distingue ses deux états.

        Complexité : O(|Q|² · |Σ|) par passage, au plus |Q|² passages
        (version pédagogique, sans l'optimisation de Hopcroft).
        """
        self._verifier_dfa_complet("pair_table")

        etats = sorted(self.states, key=_cle_tri)
        symboles = sorted(self.input_symbols, key=str)
        paires = [frozenset(p) for p in combinations(etats, 2)]
        passage = {
            p: 0 for p in paires
            if len({(etat in self.final_states) for etat in p}) > 1
        }

        numero = 0
        changement = True
        while changement:
            changement = False
            numero += 1
            for p in paires:
                if p in passage:
                    continue
                e1, e2 = sorted(p, key=_cle_tri)
                for symbole in symboles:
                    s1 = self.transitions[e1][symbole]
                    s2 = self.transitions[e2][symbole]
                    if s1 != s2 and frozenset((s1, s2)) in passage:
                        passage[p] = numero
                        changement = True
                        break
        return {p: passage.get(p) for p in paires}

    def distinguishable_states(self):
        """Ensemble des paires d'états distinguables (les paires de
        `pair_table()` dont le passage n'est pas `None`). Complexité :
        celle de `pair_table`."""
        return {p for p, passage in self.pair_table().items()
                if passage is not None}

    def pair_table_str(self, show_round=False):
        """Table triangulaire des paires en texte : une ligne par état
        (sauf le premier), une colonne par état (sauf le dernier). Une
        case contient `.` pour deux états équivalents, et sinon `X`, ou le
        numéro de passage de `pair_table()` si `show_round` est vrai.

        Exemple (`show_round=False`) :
               1  2  3
            2  X
            3  X  .

        Complexité : celle de `pair_table`.
        """
        table = self.pair_table()
        etats = sorted(self.states, key=_cle_tri)

        def case(p):
            passage = table[p]
            if passage is None:
                return "."
            return str(passage) if show_round else "X"

        lignes_de_cases = [
            [case(frozenset((a, b))) for a in etats[:i]]
            for i, b in enumerate(etats) if i > 0
        ]
        etiquettes = [_nom_court(e) for e in etats]
        largeur_etiquette = max(len(e) for e in etiquettes[1:])
        largeur_case = max(
            [len(e) for e in etiquettes[:-1]]
            + [len(c) for ligne in lignes_de_cases for c in ligne]
        )
        lignes = [" " * largeur_etiquette + "".join(
            "  " + e.rjust(largeur_case) for e in etiquettes[:-1]
        )]
        for etiquette, cases in zip(etiquettes[1:], lignes_de_cases):
            lignes.append(
                etiquette.ljust(largeur_etiquette)
                + "".join("  " + c.rjust(largeur_case) for c in cases)
            )
        return "\n".join(lignes)

    def print_pair_table(self, show_round=False):
        """Affiche la table des paires (voir `pair_table_str`)."""
        print(self.pair_table_str(show_round=show_round))

    def equivalence_classes(self):
        """Partitionne les états en classes d'équivalence (états deux
        à deux non distinguables). Complexité : celle de
        `distinguishable_states` + O(|Q|²) pour regrouper."""
        distinguables = self.distinguishable_states()
        classes = []
        for etat in sorted(self.states, key=_cle_tri):
            for classe in classes:
                representant = next(iter(classe))
                if frozenset((etat, representant)) not in distinguables:
                    classe.add(etat)
                    break
            else:
                classes.append({etat})
        return classes

    def is_minimal(self):
        """Vrai si l'automate est complet, trim, et si aucune paire
        d'états distincts n'est équivalente."""
        self._verifier_dfa_complet("is_minimal")
        return self.is_trim() and all(
            len(classe) == 1 for classe in self.equivalence_classes()
        )

    def minimize(self, keep_original_names=True):
        """Nouvel automate minimal, par quotient selon les classes
        d'équivalence calculées par `equivalence_classes` (algorithme
        de Moore). Avec `keep_original_names=True` (par défaut), chaque
        classe est nommée par son représentant, choisi comme
        `min(classe, key=_cle_tri)` pour un résultat reproductible ;
        avec `keep_original_names=False`, chaque état du résultat est le
        `frozenset` des états de sa classe.

        Complexité : celle de `equivalence_classes` + O(|Q| · |Σ|)
        pour reconstruire les transitions du quotient.
        """
        self._verifier_dfa_complet("minimize")
        classes = self.equivalence_classes()
        representant = {
            etat: (
                min(classe, key=_cle_tri) if keep_original_names
                else frozenset(classe)
            )
            for classe in classes
            for etat in classe
        }
        nouvelles_transitions = {}
        for classe in classes:
            # Tous les états d'une classe ont des transitions
            # équivalentes : on lit celles d'un état quelconque de la classe.
            exemple = min(classe, key=_cle_tri)
            nouvelles_transitions[representant[exemple]] = {
                symbole: representant[self.transitions[exemple][symbole]]
                for symbole in self.input_symbols
            }
        nouveaux_etats = set(nouvelles_transitions)
        nouveaux_finals = {
            representant[etat] for etat in self.final_states
        }
        return self._build(
            states=nouveaux_etats,
            transitions=nouvelles_transitions,
            initial_state=representant[self.initial_state],
            final_states=nouveaux_finals,
        )
