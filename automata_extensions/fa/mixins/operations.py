"""
OperationsMixin
===============

Opérations sur les langages reconnus par des automates.

Opérations "booléennes", par produit synchronisé de DFA complets :
`product`, `intersection`, `union`, `difference`, `symmetric_difference`
et `complement`. Elles acceptent aussi bien des DFA que des NFA (un NFA
est d'abord déterminisé) et renvoient toujours un DFA complet. Si les
deux automates n'ont pas le même alphabet, on travaille sur l'union des
deux alphabets (un automate qui ne connaît pas une lettre va dans un
état-puits quand il la lit).

Opérations rationnelles, construites avec des epsilon-transitions :
`concatenation`, `kleene_star` (et `union` quand `self` est un NFA).
Elles renvoient un NFA.

Compatibilité avec automata-lib : la bibliothèque possède déjà des
méthodes de mêmes noms (`union`, `intersection`, `difference`,
`symmetric_difference`, `complement`, `kleene_star`) ; celles-ci les
remplacent sur les classes `Extended...`. Les paramètres `retain_names`
(ignoré : les états du produit sont toujours des couples) et `minify`
(minimise le résultat) sont acceptés pour que les appels existants
continuent de fonctionner.
"""
from automata.fa.dfa import DFA
from automata.fa.nfa import NFA

from ..fa import _as_set

EPSILON = ""


# ----------------------------------------------------------------------
# Fonctions utilitaires (valables aussi pour des DFA/NFA d'automata-lib
# qui ne sont pas des classes `Extended...`)
# ----------------------------------------------------------------------

def _aretes(automate):
    """Triplets (source, symbole, cible) d'un DFA ou d'un NFA."""
    for etat, table in automate.transitions.items():
        for symbole, cibles in table.items():
            if isinstance(automate, DFA):
                yield (etat, symbole, cibles)
            else:
                for cible in _as_set(cibles):
                    yield (etat, symbole, cible)


def _vers_dfa(automate):
    """DFA équivalent à `automate` : lui-même si c'est déjà un DFA,
    sinon sa déterminisation."""
    if isinstance(automate, DFA):
        return automate
    if isinstance(automate, NFA):
        from ..nfa import ExtendedNFA

        if not isinstance(automate, ExtendedNFA):
            automate = ExtendedNFA(
                states=automate.states,
                input_symbols=automate.input_symbols,
                transitions=automate.transitions,
                initial_state=automate.initial_state,
                final_states=automate.final_states,
            )
        return automate.determinize()
    raise TypeError(f"Un DFA ou un NFA est attendu, pas {type(automate)!r}.")


def _completer_sur(dfa, alphabet):
    """DFA complet sur `alphabet` (qui contient l'alphabet de `dfa`),
    équivalent à `dfa` : si des transitions manquent, ajoute un état-puits
    (nommé "puits", avec des apostrophes ajoutées si ce nom existe déjà).
    Renvoie `dfa` lui-même s'il est déjà complet. Complexité :
    O(|Q| · |Σ|)."""
    alphabet = list(alphabet)
    if all(
        symbole in dfa.transitions.get(etat, {})
        for etat in dfa.states
        for symbole in alphabet
    ):
        return dfa

    from ..dfa import ExtendedDFA

    puits = "puits"
    while puits in dfa.states:
        puits += "'"
    transitions = {
        etat: {
            symbole: dfa.transitions.get(etat, {}).get(symbole, puits)
            for symbole in alphabet
        }
        for etat in dfa.states
    }
    transitions[puits] = {symbole: puits for symbole in alphabet}
    return ExtendedDFA(
        states=set(dfa.states) | {puits},
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=dfa.initial_state,
        final_states=set(dfa.final_states),
    )


def _produit(a, b, est_final):
    """Produit synchronisé de deux DFA : DFA complet dont les états sont
    les couples (état de a, état de b) accessibles depuis le couple
    initial, et dont les états finaux sont les couples (p, q) pour
    lesquels `est_final(p, q)` est vrai.

    Complexité : O(|Q_a| · |Q_b| · |Σ|) dans le pire cas."""
    from ..dfa import ExtendedDFA

    alphabet = sorted(set(a.input_symbols) | set(b.input_symbols), key=str)
    a = _completer_sur(a, alphabet)
    b = _completer_sur(b, alphabet)

    initial = (a.initial_state, b.initial_state)
    transitions = {}
    a_traiter = [initial]
    while a_traiter:
        couple = a_traiter.pop()
        if couple in transitions:
            continue
        p, q = couple
        transitions[couple] = {}
        for symbole in alphabet:
            cible = (a.transitions[p][symbole], b.transitions[q][symbole])
            transitions[couple][symbole] = cible
            if cible not in transitions:
                a_traiter.append(cible)

    return ExtendedDFA(
        states=set(transitions),
        input_symbols=set(alphabet),
        transitions=transitions,
        initial_state=initial,
        final_states={c for c in transitions if est_final(*c)},
    )


def _copier_avec_etiquette(transitions, automate, etiquette):
    """Copie `automate` dans `transitions` en remplaçant chaque état e
    par le couple (etiquette, e), pour éviter les collisions de noms."""
    for etat in automate.states:
        transitions.setdefault((etiquette, etat), {})
    for source, symbole, cible in _aretes(automate):
        transitions[(etiquette, source)].setdefault(symbole, set()).add(
            (etiquette, cible)
        )


class OperationsMixin:
    """Mixin d'opérations sur les langages, à utiliser avec `ExtendedFA`."""

    # ------------------------------------------------------------------
    # Opérations booléennes (résultat : DFA complet)
    # ------------------------------------------------------------------

    def _finaliser(self, resultat, minify):
        return resultat.minimize() if minify else resultat

    def product(self, other, is_final, *, retain_names=False, minify=False):
        """Produit synchronisé de `self` et `other` : DFA complet dont les
        états sont des couples (état de self, état de other) et dont les
        états finaux sont ceux pour lesquels `is_final(s1, s2)` est vrai
        (`s1` et `s2` sont les deux états du couple).

        Pour un NFA, on déterminise d'abord. Les alphabets peuvent
        différer (voir la docstring du module).

        Complexité : O(|Q_1| · |Q_2| · |Σ|) après déterminisation
        éventuelle.
        """
        resultat = _produit(_vers_dfa(self), _vers_dfa(other), is_final)
        return self._finaliser(resultat, minify)

    def _produit_booleen(self, other, regle, minify):
        """Produit dont l'état (p, q) est final selon `regle(p est final,
        q est final)`."""
        a, b = _vers_dfa(self), _vers_dfa(other)
        resultat = _produit(
            a, b,
            lambda p, q: regle(p in a.final_states, q in b.final_states),
        )
        return self._finaliser(resultat, minify)

    def intersection(self, other, *, retain_names=False, minify=False):
        """DFA de L(self) ∩ L(other), par produit (final si les deux
        états sont finaux). Complexité : celle de `product`."""
        return self._produit_booleen(other, lambda f, g: f and g, minify)

    def difference(self, other, *, retain_names=False, minify=False):
        """DFA de L(self) \\ L(other), par produit (final si le premier
        état est final et pas le second). Complexité : celle de
        `product`."""
        return self._produit_booleen(other, lambda f, g: f and not g, minify)

    def symmetric_difference(self, other, *, retain_names=False,
                             minify=False):
        """DFA de la différence symétrique des deux langages, par produit
        (final si exactement un des deux états est final). Complexité :
        celle de `product`."""
        return self._produit_booleen(other, lambda f, g: f != g, minify)

    def union(self, other, *, retain_names=False, minify=False):
        """Union des langages.

        - Si `self` est un DFA : DFA complet, par produit (final si l'un
          des deux états est final). Complexité : celle de `product`.
        - Si `self` est un NFA : NFA, avec un nouvel état initial relié
          par epsilon aux deux anciens états initiaux. Complexité :
          O(|Q_1| + |Q_2| + |E_1| + |E_2|).
        """
        if isinstance(self, DFA):
            return self._produit_booleen(other, lambda f, g: f or g, minify)

        from ..nfa import ExtendedNFA

        nouvel_initial = ("union",)
        transitions = {}
        _copier_avec_etiquette(transitions, self, 0)
        _copier_avec_etiquette(transitions, other, 1)
        transitions[nouvel_initial] = {
            EPSILON: {(0, self.initial_state), (1, other.initial_state)}
        }
        return ExtendedNFA(
            states=set(transitions),
            input_symbols=(
                set(self.input_symbols) | set(other.input_symbols)
            ) - {EPSILON},
            transitions=transitions,
            initial_state=nouvel_initial,
            final_states={(0, f) for f in self.final_states}
            | {(1, f) for f in other.final_states},
        )

    def complement(self, *, retain_names=False, minify=False):
        """DFA complet du langage complémentaire (par rapport à tous les
        mots sur l'alphabet de `self`) : on complète, puis on échange
        états finaux et non finaux. Pour un NFA, on déterminise d'abord.
        Complexité : O(|Q| · |Σ|) après déterminisation éventuelle.
        """
        from ..dfa import ExtendedDFA

        dfa = _vers_dfa(self)
        dfa = _completer_sur(dfa, dfa.input_symbols)
        resultat = ExtendedDFA(
            states=set(dfa.states),
            input_symbols=set(dfa.input_symbols),
            transitions={
                etat: dict(table) for etat, table in dfa.transitions.items()
            },
            initial_state=dfa.initial_state,
            final_states=set(dfa.states) - set(dfa.final_states),
        )
        return self._finaliser(resultat, minify)

    # ------------------------------------------------------------------
    # Opérations rationnelles (résultat : NFA avec epsilon-transitions)
    # ------------------------------------------------------------------

    def concatenation(self, other):
        """NFA de la concaténation L(self) · L(other) : chaque état
        final de `self` est relié par epsilon à l'état initial de
        `other`. Les états sont renommés en couples (0, état) et
        (1, état). Complexité : O(|Q_1| + |Q_2| + |E_1| + |E_2|)."""
        from ..nfa import ExtendedNFA

        transitions = {}
        _copier_avec_etiquette(transitions, self, 0)
        _copier_avec_etiquette(transitions, other, 1)
        for final in self.final_states:
            transitions[(0, final)].setdefault(EPSILON, set()).add(
                (1, other.initial_state)
            )
        return ExtendedNFA(
            states=set(transitions),
            input_symbols=(
                set(self.input_symbols) | set(other.input_symbols)
            ) - {EPSILON},
            transitions=transitions,
            initial_state=(0, self.initial_state),
            final_states={(1, f) for f in other.final_states},
        )

    def kleene_star(self):
        """NFA de l'étoile L(self)* : un nouvel état, initial et final,
        est relié par epsilon à l'ancien état initial, et chaque ancien
        état final est relié par epsilon à ce nouvel état (ce qui accepte
        aussi le mot vide). Complexité : O(|Q| + |E|)."""
        from ..nfa import ExtendedNFA

        nouvel_etat = ("*",)
        transitions = {}
        _copier_avec_etiquette(transitions, self, 0)
        transitions[nouvel_etat] = {EPSILON: {(0, self.initial_state)}}
        for final in self.final_states:
            transitions[(0, final)].setdefault(EPSILON, set()).add(
                nouvel_etat
            )
        return ExtendedNFA(
            states=set(transitions),
            input_symbols=set(self.input_symbols) - {EPSILON},
            transitions=transitions,
            initial_state=nouvel_etat,
            final_states={nouvel_etat},
        )
