# -*- coding: utf-8 -*-
"""
Tests du mixin d'analyse (accessibilité, trim, distinguabilité,
minimisation). Les valeurs attendues sont calculées à la main à partir
des fixtures de `conftest.py` (elles-mêmes copiées de
`exemple_automates.py`).
"""
import pytest


# ---------------------------------------------------------------------
# accessible_states / coaccessible_states / useful_states / trim
# (génériques, testés sur un DFA et un NFA)
# ---------------------------------------------------------------------

def test_accessible_states_dfa(dfa_fig_3_1_a):
    # Les 3 états sont atteignables depuis '1'.
    assert dfa_fig_3_1_a.accessible_states() == {'1', '2', '3'}


def test_coaccessible_states_dfa(dfa_fig_3_1_a):
    # Depuis '3', on reste bloqué dans l'état-piège '3' : on ne peut
    # jamais atteindre l'état final '2'.
    assert dfa_fig_3_1_a.coaccessible_states() == {'1', '2'}


def test_useful_states_dfa(dfa_fig_3_1_a):
    assert dfa_fig_3_1_a.useful_states() == {'1', '2'}
    assert not dfa_fig_3_1_a.is_trim()


def test_trim_dfa_retire_letat_piege(dfa_fig_3_1_a):
    trimme = dfa_fig_3_1_a.trim()
    assert trimme.states == {'1', '2'}
    assert '3' not in trimme.states
    assert trimme.final_states == {'2'}
    assert trimme.initial_state == '1'
    # L'automate original avait 'a' et 'b' partout ; après trim(), la
    # transition 'b' (qui menait à l'état piège retiré) a disparu.
    assert not trimme.is_complete()


def test_accessible_coaccessible_nfa(nfa_fig_7_1_a):
    # Ce NFA est déjà "trim" : les 3 états sont utiles.
    assert nfa_fig_7_1_a.accessible_states() == {'1', '2', '3'}
    assert nfa_fig_7_1_a.coaccessible_states() == {'1', '2', '3'}
    assert nfa_fig_7_1_a.is_trim()


def test_trim_nfa_ne_change_rien_si_deja_trim(nfa_fig_7_1_a):
    trimme = nfa_fig_7_1_a.trim()
    assert trimme.states == nfa_fig_7_1_a.states
    assert trimme.final_states == nfa_fig_7_1_a.final_states


# ---------------------------------------------------------------------
# is_complete
# ---------------------------------------------------------------------

def test_is_complete(dfa_fig_3_1_a, dfa_fig_6_1_a):
    assert dfa_fig_3_1_a.is_complete()
    assert dfa_fig_6_1_a.is_complete()


# ---------------------------------------------------------------------
# distinguishable_states / equivalence_classes / minimize
# (DFA complet uniquement)
# ---------------------------------------------------------------------

def test_distinguishable_states_refuse_un_nfa(nfa_fig_7_1_a):
    with pytest.raises(NotImplementedError):
        nfa_fig_7_1_a.distinguishable_states()


def test_dfa_fig_3_1_a_est_deja_minimal_du_point_de_vue_des_distances(dfa_fig_3_1_a):
    # Les 3 états de fig 3.1.a sont deux à deux distinguables (aucune
    # fusion possible), même si l'automate n'est pas "trim" (l'état
    # piège '3' reste un état à part entière du point de vue de la
    # distinguabilité).
    classes = dfa_fig_3_1_a.equivalence_classes()
    assert classes == [{'1'}, {'2'}, {'3'}]
    # is_minimal() est quand même False : l'automate n'est pas trim.
    assert not dfa_fig_3_1_a.is_minimal()


def test_equivalence_classes_fusionne_les_etats_3_et_4(dfa_fig_6_1_a):
    # Dans fig 6.1.a, les états '3' et '4' ont exactement les mêmes
    # transitions (a->4/4, b->3/3) et sont tous les deux finaux : ils
    # sont indistinguables.
    classes = dfa_fig_6_1_a.equivalence_classes()
    assert {'3', '4'} in classes
    assert {'1'} in classes
    assert {'2'} in classes
    assert len(classes) == 3
    assert not dfa_fig_6_1_a.is_minimal()


def test_minimize_fusionne_3_et_4(dfa_fig_6_1_a):
    minimal = dfa_fig_6_1_a.minimize()
    assert len(minimal.states) == 3
    # L'état fusionné (représentant '3', le plus petit de {'3','4'})
    # reste le seul état final.
    assert minimal.final_states == {'3'}
    assert minimal.initial_state == '1'


def test_pair_table_str_contient_les_etats(dfa_fig_6_1_a):
    table = dfa_fig_6_1_a.pair_table_str()
    assert isinstance(table, str)
    for etat in dfa_fig_6_1_a.states:
        assert etat in table


def test_print_pair_table_ne_leve_pas_derreur(dfa_fig_6_1_a, capsys):
    dfa_fig_6_1_a.print_pair_table()
    sortie = capsys.readouterr().out
    assert sortie.strip() != ""
