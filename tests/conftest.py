# -*- coding: utf-8 -*-
"""
Fixtures pytest du projet.

Les automates ci-dessous sont repris EXACTEMENT de `exemple_automates.py`
(poly d'exercices), pour que les tests utilisent les mêmes cas que vos
TD. On ne réimporte pas `exemple_automates.py` directement : ce fichier
dessine 40 diagrammes PNG dès son import (boucle en bas du fichier), ce
qui serait lent et dépendrait de Graphviz à chaque lancement de pytest.
Les définitions sont donc recopiées ici telles quelles, à la main.

Si vous voulez réutiliser un automate de `exemple_automates.py` qui n'a
pas encore de fixture ici, utilisez `vers_extended()` ci-dessous.
"""
import pytest

from automata.fa.dfa import DFA
from automata.fa.nfa import NFA

from automata_extensions.fa import ExtendedDFA, ExtendedNFA


def vers_extended(automate):
    """Convertit un DFA/NFA "normal" de automata-lib en sa version
    étendue (ExtendedDFA/ExtendedNFA), en conservant exactement sa
    définition (mêmes états, transitions, etc.).

    Permet de réutiliser directement un automate défini dans
    `exemple_automates.py` sans avoir à le recopier à la main.
    """
    if isinstance(automate, DFA):
        cls = ExtendedDFA
    elif isinstance(automate, NFA):
        cls = ExtendedNFA
    else:
        raise TypeError(f"Type non pris en charge : {type(automate)!r}")
    return cls(
        states=automate.states,
        input_symbols=automate.input_symbols,
        transitions=automate.transitions,
        initial_state=automate.initial_state,
        final_states=automate.final_states,
    )


# ---------------------------------------------------------------------
# DFA
# ---------------------------------------------------------------------

@pytest.fixture
def dfa_fig_3_1_a():
    """Poly, fig 3.1.a : accepte les mots sur {a,b} qui se terminent
    par 'a'. DFA complet, 3 états, tous accessibles."""
    return ExtendedDFA(
        states={'1', '2', '3'},
        input_symbols={'a', 'b'},
        transitions={
            '1': {'a': '2', 'b': '3'},
            '2': {'a': '2', 'b': '3'},
            '3': {'a': '3', 'b': '3'},
        },
        initial_state='1',
        final_states={'2'},
    )


@pytest.fixture
def dfa_fig_6_1_a():
    """Poly, fig 6.1.a : 4 états, 2 finaux. Utile pour tester la
    minimisation (états 3 et 4 potentiellement équivalents)."""
    return ExtendedDFA(
        states={'1', '2', '3', '4'},
        input_symbols={'a', 'b'},
        transitions={
            '1': {'a': '2', 'b': '1'},
            '2': {'a': '2', 'b': '3'},
            '3': {'a': '4', 'b': '3'},
            '4': {'a': '4', 'b': '3'},
        },
        initial_state='1',
        final_states={'3', '4'},
    )


@pytest.fixture
def dfa_table_6_1_a():
    """Poly, table 6.1.a : 5 états, 1 seul final."""
    return ExtendedDFA(
        states={'0', '1', '2', '3', '4'},
        input_symbols={'a', 'b'},
        transitions={
            '0': {'a': '0', 'b': '1'},
            '1': {'a': '2', 'b': '3'},
            '2': {'a': '2', 'b': '3'},
            '3': {'a': '2', 'b': '4'},
            '4': {'a': '0', 'b': '1'},
        },
        initial_state='0',
        final_states={'3'},
    )


# ---------------------------------------------------------------------
# NFA
# ---------------------------------------------------------------------

@pytest.fixture
def nfa_fig_7_1_a():
    """Poly, fig 7.1.a : NFA non déterministe (symbole 'a' menant à
    deux états depuis l'état '1')."""
    return ExtendedNFA(
        states={'1', '2', '3'},
        input_symbols={'a', 'b'},
        transitions={
            '1': {'a': {'1', '2'}, 'b': '1'},
            '2': {'a': '3', 'b': '3'},
            '3': {},
        },
        initial_state='1',
        final_states={'3'},
    )


@pytest.fixture
def nfa_fig_8_1_a():
    """Poly, fig 8.1.a : NFA avec des transitions notées 'ϵ' dans le
    poly. Attention : automata-lib attend la chaîne vide '' comme clé
    pour une véritable epsilon-transition ; ici 'ϵ' est repris tel
    quel comme symbole du poly, pas encore adapté à la convention de
    la bibliothèque (à clarifier en phase 3, epsilon_closure)."""
    return ExtendedNFA(
        states={'0', '1', '2', '3', '4'},
        input_symbols={'a', 'b', 'ϵ'},
        transitions={
            '0': {'a': '1', 'ϵ': '3'},
            '1': {'a': '2', 'b': '0'},
            '2': {'b': '1'},
            '3': {'a': '4'},
            '4': {'b': '3', 'ϵ': '2'},
        },
        initial_state='0',
        final_states={'1', '2', '3', '4'},
    )
