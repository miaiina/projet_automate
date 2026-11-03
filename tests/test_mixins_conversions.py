# -*- coding: utf-8 -*-
"""
Tests du mixin de conversions, phase 3a : fermeture epsilon,
suppression des epsilon-transitions, déterminisation, complétion.

Deux types de vérifications :
- des résultats calculés à la main (mots acceptés / rejetés connus) ;
- des comparaisons "même langage" sur tous les mots jusqu'à une
  certaine longueur, pour s'assurer qu'une conversion ne change pas
  le langage reconnu.
"""
from itertools import product

import pytest

from automata.fa.dfa import DFA
from automata.fa.nfa import NFA


def tous_les_mots(alphabet, longueur_max):
    for longueur in range(longueur_max + 1):
        for lettres in product(sorted(alphabet), repeat=longueur):
            yield "".join(lettres)


def meme_langage(a, b, alphabet=("a", "b"), longueur_max=6):
    return all(
        a.accepts_input(mot) == b.accepts_input(mot)
        for mot in tous_les_mots(alphabet, longueur_max)
    )


# ---------------------------------------------------------------------
# Langage de référence de nfa_epsilon (calculé à la main)
# ---------------------------------------------------------------------

def test_nfa_epsilon_langage_attendu(nfa_epsilon):
    for mot in ["", "a", "aa", "ab", "aab", "abb"]:
        assert nfa_epsilon.accepts_input(mot), mot
    for mot in ["b", "ba", "aba", "bb"]:
        assert not nfa_epsilon.accepts_input(mot), mot


# ---------------------------------------------------------------------
# Fermeture epsilon
# ---------------------------------------------------------------------

def test_epsilon_closure(nfa_epsilon):
    assert nfa_epsilon.epsilon_closure('p') == {'p', 'r'}
    assert nfa_epsilon.epsilon_closure('q') == {'q'}
    assert nfa_epsilon.epsilon_closure('r') == {'r'}


def test_epsilon_closure_of_set(nfa_epsilon):
    assert nfa_epsilon.epsilon_closure_of_set({'p', 'q'}) == {'p', 'q', 'r'}
    assert nfa_epsilon.epsilon_closure_of_set(set()) == set()


def test_epsilon_closure_dfa_est_triviale(dfa_fig_3_1_a):
    assert dfa_fig_3_1_a.epsilon_closure('1') == {'1'}


# ---------------------------------------------------------------------
# remove_epsilon_transitions
# ---------------------------------------------------------------------

def test_remove_epsilon_transitions_supprime_les_epsilon(nfa_epsilon):
    sans = nfa_epsilon.remove_epsilon_transitions()
    assert isinstance(sans, NFA)
    for table in sans.transitions.values():
        assert "" not in table


def test_remove_epsilon_transitions_etats_finaux(nfa_epsilon):
    # 'p' devient final : sa fermeture {p, r} contient l'état final 'r'.
    sans = nfa_epsilon.remove_epsilon_transitions()
    assert sans.final_states == {'p', 'q', 'r'}
    assert sans.states == nfa_epsilon.states


def test_remove_epsilon_transitions_conserve_le_langage(nfa_epsilon):
    assert meme_langage(nfa_epsilon, nfa_epsilon.remove_epsilon_transitions())


def test_remove_epsilon_transitions_sans_epsilon_renvoie_lautomate(nfa_fig_7_1_a):
    assert nfa_fig_7_1_a.remove_epsilon_transitions() is nfa_fig_7_1_a


def test_eliminate_lambda_est_redirige(nfa_epsilon):
    assert meme_langage(nfa_epsilon, nfa_epsilon.eliminate_lambda())


# ---------------------------------------------------------------------
# determinize / to_dfa
# ---------------------------------------------------------------------

def test_determinize_nfa_epsilon(nfa_epsilon):
    dfa = nfa_epsilon.determinize()
    assert isinstance(dfa, DFA)
    assert dfa.is_complete()
    assert meme_langage(nfa_epsilon, dfa)


def test_determinize_etat_initial_est_la_fermeture(nfa_epsilon):
    dfa = nfa_epsilon.determinize()
    assert dfa.initial_state == frozenset({'p', 'r'})


def test_determinize_nfa_sans_epsilon(nfa_fig_7_1_a):
    dfa = nfa_fig_7_1_a.determinize()
    assert dfa.is_complete()
    assert meme_langage(nfa_fig_7_1_a, dfa)
    # Langage : (a|b)*a(a|b), c'est-à-dire "l'avant-dernière lettre est a".
    assert dfa.accepts_input("aa")
    assert dfa.accepts_input("ab")
    assert dfa.accepts_input("bab")
    assert not dfa.accepts_input("a")
    assert not dfa.accepts_input("ba")
    assert not dfa.accepts_input("bb")


def test_to_dfa_est_un_alias(nfa_epsilon):
    assert nfa_epsilon.to_dfa().states == nfa_epsilon.determinize().states


def test_determinize_dfa_renvoie_lautomate(dfa_fig_3_1_a):
    assert dfa_fig_3_1_a.determinize() is dfa_fig_3_1_a


# ---------------------------------------------------------------------
# complete
# ---------------------------------------------------------------------

def test_complete_ajoute_un_etat_puits(dfa_partiel):
    complet = dfa_partiel.complete()
    assert complet.is_complete()
    assert complet.states == {'0', 'puits'}
    assert complet.final_states == {'0'}
    assert complet.accepts_input("aaa")
    assert not complet.accepts_input("b")
    assert not complet.accepts_input("aab")
    assert meme_langage_partiel_vs_complet(dfa_partiel, complet)


def meme_langage_partiel_vs_complet(partiel, complet, longueur_max=5):
    # accepts_input sur un DFA partiel peut lever une exception quand la
    # transition manque : on considère alors que le mot est rejeté.
    for mot in tous_les_mots(("a", "b"), longueur_max):
        try:
            attendu = partiel.accepts_input(mot)
        except Exception:
            attendu = False
        if attendu != complet.accepts_input(mot):
            return False
    return True


def test_complete_dfa_deja_complet_renvoie_lautomate(dfa_fig_3_1_a):
    assert dfa_fig_3_1_a.complete() is dfa_fig_3_1_a


def test_complete_nom_deja_pris(dfa_partiel):
    with pytest.raises(ValueError):
        dfa_partiel.complete(sink_state='0')


def test_complete_refuse_un_nfa(nfa_fig_7_1_a):
    with pytest.raises(NotImplementedError):
        nfa_fig_7_1_a.complete()


# ---------------------------------------------------------------------
# Enchaînement avec le mixin analyse (phase 2)
# ---------------------------------------------------------------------

def test_determinize_puis_minimize(nfa_fig_7_1_a):
    # Le DFA minimal de (a|b)*a(a|b) a exactement 4 états.
    minimal = nfa_fig_7_1_a.determinize().minimize()
    assert len(minimal.states) == 4
    assert meme_langage(nfa_fig_7_1_a, minimal)


def test_completer_puis_minimiser(dfa_partiel):
    minimal = dfa_partiel.complete().minimize()
    # a* : l'état '0' (final) et le puits sont distinguables.
    assert len(minimal.states) == 2
