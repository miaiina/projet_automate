"""
ConversionsMixin
================

Conversions entre représentations d'automates.

Phase 3a :
- `epsilon_closure`, `epsilon_closure_of_set`
- `remove_epsilon_transitions`
- `determinize` / `to_dfa` (construction par sous-ensembles)
- `complete` (ajout d'un état-puits)

Phase 3b (automate -> expression régulière) :
- `to_regex` : élimination d'états, ordre lexicographique, sortie
  volontairement non simplifiée (chaque étape reste lisible) ;
- `to_regex_arden` : résolution du système d'équations par le lemme
  d'Arden ;
- `to_regex_optimum` et `to_regex_arden_optimum` : essaient plusieurs
  ordres d'élimination, simplifient, et gardent l'expression la plus
  courte.

Phase 3c :
- `reverse` : automate du langage miroir ;
- `brzozowski_minimize` : minimisation par double inversion et
  déterminisation ;
- la construction de Thompson (regex -> NFA) est `ExtendedNFA.from_regex`
  (voir `nfa.py` et `regex/regex.py`).

Les expressions écrites utilisent la syntaxe d'automata-lib : `|`
(union), `*`, `()` (mot vide). Le langage vide s'écrit `∅`.

Convention d'automata-lib : une epsilon-transition est une transition
étiquetée par la chaîne vide `""` (et non par un symbole 'ϵ' : celui-ci
n'est qu'un symbole ordinaire pour la bibliothèque).
"""
from itertools import permutations

from automata.fa.dfa import DFA
from automata.fa.nfa import NFA

from ...regex.regex import (
    EMPTY, EPS, Sym, alt, cat, simplify, star, to_string, verifier_lettre,
)
from ..fa import _as_set, _cle_tri

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
        return self._determinize_depuis({self.initial_state})

    def _determinize_depuis(self, etats_initiaux):
        """Construction par sous-ensembles à partir d'un ENSEMBLE d'états
        initiaux (le sous-ensemble de départ est la fermeture epsilon de
        cet ensemble). Sert à `determinize` (un seul état initial) et à
        `brzozowski_minimize` (plusieurs). Même résultat et même
        complexité que `determinize`."""
        from ..dfa import ExtendedDFA  # import local : évite un cycle

        symboles = set(self.input_symbols) - {EPSILON}
        initial = frozenset(self.epsilon_closure_of_set(etats_initiaux))
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

    # ------------------------------------------------------------------
    # Automate -> expression régulière
    # ------------------------------------------------------------------

    def _verifier_symboles_pour_regex(self):
        """Lève ValueError si un symbole ne peut pas s'écrire dans une
        expression régulière (voir `regex.verifier_lettre`)."""
        for symbole in self.input_symbols:
            if symbole != EPSILON:
                verifier_lettre(symbole)

    def _etiquette(self, symbole):
        """Expression associée à une transition : `Eps` pour une
        epsilon-transition, sinon la lettre."""
        return EPS if symbole == EPSILON else Sym(symbole)

    def _eliminer_etats(self, ordre, simplificateur=None):
        """Élimination d'états : renvoie l'expression (noeud d'arbre) du
        langage reconnu.

        On ajoute un état de début (relié à l'état initial par epsilon)
        et un état de fin (relié depuis chaque état final par epsilon),
        puis on supprime les états de `ordre` un par un : pour chaque
        chemin p -> s -> q passant par l'état supprimé s, on ajoute à
        l'arête (p, q) l'expression R(p,s) · R(s,s)* · R(s,q). À la fin,
        il ne reste que l'arête début -> fin.

        `simplificateur`, s'il est donné, est appliqué à chaque arête
        modifiée (utilisé par les variantes `optimum`).

        Complexité : O(|Q|³) opérations sur des expressions (dont la
        taille peut croître exponentiellement dans le pire cas).
        """
        table = {}
        for source, symbole, cible in self._labeled_edges():
            cle = (source, cible)
            table[cle] = alt(table.get(cle, EMPTY), self._etiquette(symbole))

        debut, fin = object(), object()
        table[(debut, self.initial_state)] = EPS
        for final in self.final_states:
            table[(final, fin)] = alt(table.get((final, fin), EMPTY), EPS)

        for supprime in ordre:
            boucle = table.pop((supprime, supprime), None)
            milieu = star(boucle) if boucle is not None else EPS
            entrants = [
                (p, r) for (p, q), r in table.items() if q == supprime
            ]
            sortants = [
                (q, r) for (p, q), r in table.items() if p == supprime
            ]
            for p, _ in entrants:
                del table[(p, supprime)]
            for q, _ in sortants:
                del table[(supprime, q)]
            for p, r_entrant in entrants:
                for q, r_sortant in sortants:
                    nouveau = alt(
                        table.get((p, q), EMPTY),
                        cat(r_entrant, milieu, r_sortant),
                    )
                    if simplificateur is not None:
                        nouveau = simplificateur(nouveau)
                    table[(p, q)] = nouveau

        return table.get((debut, fin), EMPTY)

    def _resoudre_arden(self, ordre, simplificateur=None):
        """Résolution du système d'équations du langage reconnu depuis
        chaque état par le lemme d'Arden : X = A·X | B  donne  X = A*·B.

        Pour chaque état i : X_i = somme des (lettre · X_j) pour les
        transitions i -> j, plus le mot vide si i est final. On élimine
        les inconnues dans l'ordre de `ordre` (méthode de Gauss-Jordan) ;
        à la fin, X_initial est l'expression cherchée.

        Complexité : O(|Q|³) opérations sur des expressions.
        """
        equations = {etat: {} for etat in self.states}
        constantes = {
            etat: (EPS if etat in self.final_states else EMPTY)
            for etat in self.states
        }
        for source, symbole, cible in self._labeled_edges():
            equations[source][cible] = alt(
                equations[source].get(cible, EMPTY), self._etiquette(symbole)
            )

        def appliquer(expression):
            return simplificateur(expression) if simplificateur else expression

        for k in ordre:
            auto = equations[k].pop(k, None)
            if auto is not None:
                etoile = star(auto)
                for j in equations[k]:
                    equations[k][j] = appliquer(cat(etoile, equations[k][j]))
                constantes[k] = appliquer(cat(etoile, constantes[k]))
            for i in self.states:
                if i == k or k not in equations[i]:
                    continue
                coefficient = equations[i].pop(k)
                for j, reste in equations[k].items():
                    equations[i][j] = appliquer(
                        alt(equations[i].get(j, EMPTY), cat(coefficient, reste))
                    )
                constantes[i] = appliquer(
                    alt(constantes[i], cat(coefficient, constantes[k]))
                )
        return constantes[self.initial_state]

    def _ordre_lexicographique(self):
        return sorted(self.states, key=_cle_tri)

    def _ordres_candidats(self):
        """Ordres d'élimination essayés par les variantes `optimum` :
        toutes les permutations jusqu'à 6 états (au plus 720), sinon
        trois ordres heuristiques (lexicographique, inverse, et par
        nombre croissant de transitions entrantes x sortantes)."""
        etats = self._ordre_lexicographique()
        if len(etats) <= 6:
            return [list(p) for p in permutations(etats)]
        entrants = {e: 0 for e in etats}
        sortants = {e: 0 for e in etats}
        for source, _, cible in self._labeled_edges():
            sortants[source] += 1
            entrants[cible] += 1
        par_degre = sorted(
            etats, key=lambda e: (entrants[e] * sortants[e], _cle_tri(e))
        )
        return [etats, etats[::-1], par_degre]

    def _meilleure_expression(self, methode):
        """Applique `methode(ordre, simplificateur)` pour chaque ordre
        candidat et garde l'expression écrite la plus courte (la
        première en cas d'égalité)."""
        meilleure = None
        for ordre in self._ordres_candidats():
            texte = to_string(simplify(methode(ordre, simplify)))
            if meilleure is None or len(texte) < len(meilleure):
                meilleure = texte
        return meilleure

    def to_regex(self):
        """Expression régulière du langage, par élimination d'états dans
        l'ordre lexicographique des états. La sortie n'est volontairement
        pas simplifiée (pédagogique : chaque morceau correspond à une
        étape de l'algorithme), et écrite dans le style du cours : toute
        union entre parenthèses, parenthèses doublées sous une étoile
        (`(b*|b*ab*a((b|ab*ab*a))*ab*)`). Le langage vide donne `"∅"`.

        Lève `ValueError` si un symbole de l'alphabet ne peut pas
        s'écrire dans une expression régulière (voir
        `regex.verifier_lettre`).

        Complexité : celle de `_eliminer_etats`, soit O(|Q|³).
        """
        self._verifier_symboles_pour_regex()
        return to_string(
            self._eliminer_etats(self._ordre_lexicographique()), verbeux=True
        )

    def to_regex_arden(self):
        """Expression régulière du langage, par résolution du système
        d'équations avec le lemme d'Arden (ordre lexicographique), écrite
        dans le même style que `to_regex()`. Même langage que `to_regex()`,
        mais l'écriture peut différer.

        Complexité : celle de `_resoudre_arden`, soit O(|Q|³).
        """
        self._verifier_symboles_pour_regex()
        return to_string(
            self._resoudre_arden(self._ordre_lexicographique()), verbeux=True
        )

    def to_regex_optimum(self):
        """Comme `to_regex()`, mais en essayant plusieurs ordres
        d'élimination (voir `_ordres_candidats`) avec simplification des
        expressions, et en gardant la plus courte. Aucune garantie
        d'optimalité au-delà de 6 états.

        Complexité : O(k · |Q|³) opérations sur des expressions, avec
        k = min(|Q|!, ...) ordres essayés (k = 720 au plus).
        """
        self._verifier_symboles_pour_regex()
        return self._meilleure_expression(self._eliminer_etats)

    def to_regex_arden_optimum(self):
        """Comme `to_regex_arden()`, mais avec plusieurs ordres de
        résolution et simplification, en gardant l'expression la plus
        courte. Même complexité que `to_regex_optimum()`."""
        self._verifier_symboles_pour_regex()
        return self._meilleure_expression(self._resoudre_arden)

    # ------------------------------------------------------------------
    # Miroir et minimisation de Brzozowski
    # ------------------------------------------------------------------

    def reverse(self):
        """NFA du langage miroir (les mots lus à l'envers).

        On retourne toutes les transitions (p --a--> q devient
        q --a--> p), l'ancien état initial devient l'unique état final,
        et un nouvel état initial est relié par epsilon à chaque ancien
        état final. Le résultat est toujours un `ExtendedNFA`, même à
        partir d'un DFA.

        Complexité : O(|Q| + |E|).
        """
        from ..nfa import ExtendedNFA  # import local : évite un cycle

        nouvel_initial = "init"
        while nouvel_initial in self.states:
            nouvel_initial += "'"

        transitions = {etat: {} for etat in self.states}
        transitions[nouvel_initial] = {}
        for source, symbole, cible in self._labeled_edges():
            transitions[cible].setdefault(symbole, set()).add(source)
        for final in self.final_states:
            transitions[nouvel_initial].setdefault(EPSILON, set()).add(final)

        return ExtendedNFA(
            states=set(self.states) | {nouvel_initial},
            input_symbols=set(self.input_symbols) - {EPSILON},
            transitions=transitions,
            initial_state=nouvel_initial,
            final_states={self.initial_state},
        )

    def brzozowski_minimize(self):
        """DFA minimal complet du même langage, par l'algorithme de
        Brzozowski : miroir, déterminisation, miroir, déterminisation.

        Le miroir d'un automate a plusieurs états initiaux (les anciens
        états finaux) ; on déterminise donc directement à partir de cet
        ensemble, sans passer par l'état initial artificiel de
        `reverse()` (qui se retrouverait dans le premier sous-ensemble
        et créerait un état en double). La première déterminisation ne
        garde que les états accessibles du miroir, ce qui élimine les
        états inutiles ; la seconde donne directement l'automate minimal.

        Fonctionne sur un DFA (même incomplet) comme sur un NFA, avec ou
        sans epsilon-transitions. Les états du résultat sont des
        ensembles d'ensembles d'états : peu lisibles, mais le nombre
        d'états est celui du minimum.

        Complexité : exponentielle dans le pire cas (deux
        déterminisations successives).
        """
        def miroir_deterministe(automate):
            return automate.reverse()._determinize_depuis(
                automate.final_states
            )

        return miroir_deterministe(miroir_deterministe(self))
