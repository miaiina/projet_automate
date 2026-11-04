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

from ..fa import _cle_tri


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
            utiles = {self.initial_state}
        return self._build(
            states=utiles,
            transitions=self._filtered_transitions(utiles),
            initial_state=self.initial_state,
            final_states=self.final_states & utiles,
        )

    # ------------------------------------------------------------------
    # Complétude (prérequis des méthodes ci-dessous)
    # ------------------------------------------------------------------

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

    def distinguishable_states(self):
        """Ensemble des paires d'états distinguables, par l'algorithme
        des tables (Moore) : on marque d'abord les paires (état final,
        état non final), puis on propage — une paire (p, q) est
        distinguable dès qu'il existe un symbole a tel que
        (delta(p,a), delta(q,a)) est une paire déjà marquée distinguable.

        Complexité : O(|Q|² · |Σ|) dans cette version naïve (on refait
        une passe complète sur toutes les paires tant qu'un changement
        a eu lieu, sans l'optimisation en O(|Q| · |Σ|) de Hopcroft).
        """
        self._verifier_dfa_complet("distinguishable_states")

        paires = {frozenset(p) for p in combinations(self.states, 2)}
        distinguables = {
            p for p in paires
            if len({(etat in self.final_states) for etat in p}) > 1
        }

        changement = True
        while changement:
            changement = False
            for p in paires - distinguables:
                e1, e2 = tuple(p)
                for symbole in self.input_symbols:
                    s1 = self.transitions[e1][symbole]
                    s2 = self.transitions[e2][symbole]
                    if s1 != s2 and frozenset((s1, s2)) in distinguables:
                        distinguables.add(p)
                        changement = True
                        break
        return distinguables

    def pair_table_str(self):
        """Représentation textuelle de la table des paires : une ligne
        par état (sauf le premier), une colonne par état précédent,
        'X' si la paire est distinguable. Complexité : celle de
        `distinguishable_states`."""
        distinguables = self.distinguishable_states()
        etats = sorted(self.states, key=_cle_tri)
        lignes = []
        for i, e2 in enumerate(etats[1:], start=1):
            marques = [
                "X" if frozenset((e1, e2)) in distinguables else "."
                for e1 in etats[:i]
            ]
            lignes.append(f"{e2} | " + " ".join(marques))
        entete = "    " + " ".join(etats[:-1])
        return entete + "\n" + "\n".join(lignes)

    def print_pair_table(self):
        """Affiche la table des paires (voir `pair_table_str`)."""
        print(self.pair_table_str())

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

    def minimize(self):
        """Nouvel automate minimal, par quotient selon les classes
        d'équivalence calculées par `equivalence_classes` (algorithme
        de Moore). Le représentant de chaque classe est choisi comme
        `min(classe, key=_cle_tri)`, pour un résultat déterministe et
        reproductible d'un appel à l'autre.

        Complexité : celle de `equivalence_classes` + O(|Q| · |Σ|)
        pour reconstruire les transitions du quotient.
        """
        self._verifier_dfa_complet("minimize")
        classes = self.equivalence_classes()
        representant = {
            etat: min(classe, key=_cle_tri)
            for classe in classes
            for etat in classe
        }
        nouveaux_etats = set(representant.values())
        nouvelles_transitions = {
            r: {
                symbole: representant[self.transitions[r][symbole]]
                for symbole in self.input_symbols
            }
            for r in nouveaux_etats
        }
        nouveaux_finals = {
            representant[etat] for etat in self.final_states
        }
        return self._build(
            states=nouveaux_etats,
            transitions=nouvelles_transitions,
            initial_state=representant[self.initial_state],
            final_states=nouveaux_finals,
        )
