# -*- coding: utf-8 -*-
"""
Tests de la phase 1 : vérifient seulement que le squelette est bien
câblé (héritage, `_successors`, compatibilité avec automata-lib).

Les tests sur les algorithmes eux-mêmes (trim, minimize, to_regex...)
arrivent phase par phase dans les autres fichiers de ce dossier, au fur
et à mesure que les mixins correspondants sont implémentés.
"""
from automata.fa.dfa import DFA
from automata.fa.nfa import NFA
from automata.fa.gnfa import GNFA

from automata_extensions.fa import ExtendedDFA, ExtendedNFA, ExtendedGNFA
from automata_extensions.fa.fa import ExtendedFA


def test_extended_dfa_est_bien_un_dfa_et_un_extended_fa(dfa_fig_3_1_a):
    assert isinstance(dfa_fig_3_1_a, DFA)
    assert isinstance(dfa_fig_3_1_a, ExtendedFA)


def test_extended_dfa_accepte_les_memes_mots_que_le_dfa_original(dfa_fig_3_1_a):
    # fig 3.1.a du poly : ce DFA n'accepte que les mots composés
    # uniquement de 'a' (dès qu'un 'b' apparaît, l'automate tombe dans
    # l'état-piège '3', dont on ne sort jamais).
    assert dfa_fig_3_1_a.accepts_input("a")
    assert dfa_fig_3_1_a.accepts_input("aa")
    assert dfa_fig_3_1_a.accepts_input("aaa")
    assert not dfa_fig_3_1_a.accepts_input("b")
    assert not dfa_fig_3_1_a.accepts_input("ab")
    assert not dfa_fig_3_1_a.accepts_input("ba")


def test_successors_dfa(dfa_fig_3_1_a):
    assert dfa_fig_3_1_a._successors('1') == {'2', '3'}
    assert dfa_fig_3_1_a._successors('3') == {'3'}


def test_is_final_dfa(dfa_fig_3_1_a):
    assert dfa_fig_3_1_a._is_final('2')
    assert not dfa_fig_3_1_a._is_final('1')


def test_extended_nfa_est_bien_un_nfa_et_un_extended_fa(nfa_fig_7_1_a):
    assert isinstance(nfa_fig_7_1_a, NFA)
    assert isinstance(nfa_fig_7_1_a, ExtendedFA)


def test_successors_nfa(nfa_fig_7_1_a):
    # état '1' : {'a': {'1', '2'}, 'b': '1'} -> successeurs {'1', '2'}
    assert nfa_fig_7_1_a._successors('1') == {'1', '2'}
    assert nfa_fig_7_1_a._successors('3') == set()


def test_extended_gnfa_est_un_sous_type_coherent():
    # Pas de fixture GNFA pour l'instant (pas d'exemple direct dans le
    # poly) : on vérifie juste que la classe est bien câblée.
    assert issubclass(ExtendedGNFA, ExtendedFA)
    assert issubclass(ExtendedGNFA, GNFA)
