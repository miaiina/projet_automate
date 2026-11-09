# -*- coding: utf-8 -*-
"""
Tests du graphe sous-jacent d'un automate (accessibilité d'un état, parcours,
cycles, composantes fortement connexes, sous-automate, copie) et de
`is_deterministic`.

Arbitre indépendant pour les composantes fortement connexes : une fermeture
transitive de Floyd-Warshall, calculée ici même.
"""
import pytest

from automata_extensions.fa import ExtendedDFA, ExtendedNFA


def dfa_ramifie():
    """0 -a-> 1, 0 -b-> 2 ; 1 -> 3 ; 2 -> 4 ; 3 et 4 bouclent. Final : 3."""
    return ExtendedDFA(
        states={'0', '1', '2', '3', '4'},
        input_symbols={'a', 'b'},
        transitions={
            '0': {'a': '1', 'b': '2'},
            '1': {'a': '3', 'b': '3'},
            '2': {'a': '4', 'b': '4'},
            '3': {'a': '3', 'b': '3'},
            '4': {'a': '4', 'b': '4'},
        },
        initial_state='0',
        final_states={'3'},
    )


def dfa_acyclique():
    return ExtendedDFA(
        states={'0', '1', '2'},
        input_symbols={'a', 'b'},
        transitions={'0': {'a': '1'}, '1': {'b': '2'}, '2': {}},
        initial_state='0',
        final_states={'2'},
        allow_partial=True,
    )


def dfa_cycle_inatteignable():
    """Le cycle sur l'état 2 n'est pas atteignable depuis l'état initial."""
    return ExtendedDFA(
        states={'0', '1', '2'},
        input_symbols={'a'},
        transitions={'0': {'a': '1'}, '1': {}, '2': {'a': '2'}},
        initial_state='0',
        final_states={'1'},
        allow_partial=True,
    )


# ---------------------------------------------------------------------
# Accessibilité d'un état donné
# ---------------------------------------------------------------------

def test_is_accessible_et_is_coaccessible(dfa_fig_3_1_a):
    # fig 3.1.a : 1 -> 2 (final), 3 est un puits.
    assert dfa_fig_3_1_a.is_accessible('3')
    assert not dfa_fig_3_1_a.is_coaccessible('3')
    assert dfa_fig_3_1_a.is_coaccessible('1')
    assert dfa_fig_3_1_a.is_coaccessible('2')
    with pytest.raises(ValueError):
        dfa_fig_3_1_a.is_accessible('inconnu')


def test_reachable_states(dfa_fig_3_1_a, dfa_mod3):
    assert dfa_fig_3_1_a.reachable_states('1') == {'1', '2', '3'}
    assert dfa_fig_3_1_a.reachable_states('2') == {'2', '3'}
    assert dfa_fig_3_1_a.reachable_states('3') == {'3'}
    assert dfa_mod3.reachable_states('1') == {'0', '1', '2'}   # exemple de la doc


def test_reachable_states_generalise_accessible_states(dfa_mod3, nfa_epsilon):
    for automate in (dfa_mod3, nfa_epsilon):
        assert automate.reachable_states(automate.initial_state) == (
            automate.accessible_states()
        )


# ---------------------------------------------------------------------
# bfs et dfs
# ---------------------------------------------------------------------

def test_bfs_et_dfs_exemple_de_la_doc(dfa_mod3):
    assert dfa_mod3.bfs() == ['0', '1', '2']
    assert dfa_mod3.dfs() == ['0', '1', '2']


def test_bfs_et_dfs_donnent_des_ordres_differents():
    a = dfa_ramifie()
    assert a.bfs() == ['0', '1', '2', '3', '4']     # niveau par niveau
    assert a.dfs() == ['0', '1', '3', '2', '4']     # en profondeur
    assert a.bfs(start='2') == ['2', '4']
    assert a.dfs(start='1') == ['1', '3']


def test_dfs_recursif_donne_le_meme_ordre(
    dfa_mod3, dfa_fig_6_1_a, dfa_table_6_1_a, nfa_epsilon, nfa_fig_7_1_a,
):
    for automate in (dfa_mod3, dfa_fig_6_1_a, dfa_table_6_1_a, nfa_epsilon,
                     nfa_fig_7_1_a, dfa_ramifie()):
        assert automate.dfs() == automate.dfs(recursive=True)


def test_parcours_nfa_avec_epsilon(nfa_epsilon):
    assert nfa_epsilon.bfs() == ['p', 'q', 'r']
    assert nfa_epsilon.reachable_states('q') == {'q'}
    assert set(nfa_epsilon.dfs()) == {'p', 'q', 'r'}


def test_parcours_etat_inconnu(dfa_mod3):
    with pytest.raises(ValueError):
        dfa_mod3.bfs(start='zz')
    with pytest.raises(ValueError):
        dfa_mod3.dfs(start='zz')


# ---------------------------------------------------------------------
# Cycles
# ---------------------------------------------------------------------

def test_has_cycle(dfa_mod3):
    assert dfa_mod3.has_cycle()                      # exemple de la doc
    assert dfa_mod3.has_cycle_from('0')
    assert not dfa_acyclique().has_cycle()
    assert not dfa_acyclique().has_cycle_from('0')


def test_has_cycle_from_ne_voit_que_les_cycles_atteignables():
    a = dfa_cycle_inatteignable()
    assert a.has_cycle()
    assert not a.has_cycle_from('0')
    assert a.has_cycle_from('2')


def test_une_boucle_sur_un_etat_est_un_cycle():
    seul = ExtendedDFA(
        states={'0'}, input_symbols={'a'}, transitions={'0': {'a': '0'}},
        initial_state='0', final_states={'0'},
    )
    assert seul.has_cycle()


# ---------------------------------------------------------------------
# Composantes fortement connexes
# ---------------------------------------------------------------------

def fermeture_transitive(automate):
    """Floyd-Warshall : atteint[(p, q)] vaut vrai si q est atteignable
    depuis p (tout état est atteignable depuis lui-même)."""
    etats = list(automate.states)
    atteint = {(p, q): p == q for p in etats for q in etats}
    for p, _, q in automate._labeled_edges():
        atteint[(p, q)] = True
    for k in etats:
        for i in etats:
            for j in etats:
                if atteint[(i, k)] and atteint[(k, j)]:
                    atteint[(i, j)] = True
    return atteint


def composantes_de_reference(automate):
    atteint = fermeture_transitive(automate)
    composantes = []
    for etat in sorted(automate.states):
        for composante in composantes:
            representant = next(iter(composante))
            if atteint[(etat, representant)] and atteint[(representant, etat)]:
                composante.add(etat)
                break
        else:
            composantes.append({etat})
    return {frozenset(c) for c in composantes}


def test_strongly_connected_components_exemple_de_la_doc(dfa_mod3):
    assert dfa_mod3.strongly_connected_components() == [
        frozenset({'0', '1', '2'})
    ]
    assert dfa_mod3.is_strongly_connected()


def test_strongly_connected_components_contre_floyd_warshall(
    dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, nfa_epsilon,
    nfa_fig_7_1_a, dfa_vide, automate_cours_6, automate_cours_6_bis,
):
    for automate in (dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                     nfa_epsilon, nfa_fig_7_1_a, dfa_vide, dfa_ramifie(),
                     dfa_acyclique(), automate_cours_6, automate_cours_6_bis):
        obtenu = automate.strongly_connected_components()
        assert set(obtenu) == composantes_de_reference(automate)
        assert len(obtenu) == len(set(obtenu))           # pas de doublon
        # Les composantes partitionnent les états.
        assert set().union(*obtenu) == set(automate.states)


def test_strongly_connected_components_cas_simples(dfa_fig_3_1_a):
    # fig 3.1.a : 1 -> 2 -> 3, avec des boucles sur 2 et 3 : trois composantes.
    assert dfa_fig_3_1_a.strongly_connected_components() == [
        frozenset({'1'}), frozenset({'2'}), frozenset({'3'}),
    ]
    assert not dfa_fig_3_1_a.is_strongly_connected()


# ---------------------------------------------------------------------
# induced_subautomaton, copy, accepts
# ---------------------------------------------------------------------

def test_induced_subautomaton(dfa_mod3):
    sous = dfa_mod3.induced_subautomaton({'0', '1'})
    assert sous.states == {'0', '1'}
    assert sous.initial_state == '0'
    assert sous.final_states == {'0'}
    assert sous.transitions['0'] == {'a': '1', 'b': '0'}
    assert sous.transitions['1'] == {'b': '1'}       # 1 -a-> 2 a disparu


def test_induced_subautomaton_erreurs(dfa_mod3):
    with pytest.raises(ValueError):
        dfa_mod3.induced_subautomaton({'1', '2'})     # sans l'état initial
    with pytest.raises(ValueError):
        dfa_mod3.induced_subautomaton({'0', 'inconnu'})


def test_copy(dfa_mod3, nfa_epsilon):
    copie = dfa_mod3.copy()
    assert copie is not dfa_mod3
    assert isinstance(copie, ExtendedDFA)
    assert copie.states == dfa_mod3.states
    assert copie.transitions == dfa_mod3.transitions
    assert copie.initial_state == dfa_mod3.initial_state
    assert copie.final_states == dfa_mod3.final_states
    assert dfa_mod3.is_equivalent(copie)

    copie_nfa = nfa_epsilon.copy()
    assert copie_nfa is not nfa_epsilon
    assert isinstance(copie_nfa, ExtendedNFA)
    assert copie_nfa.states == nfa_epsilon.states
    assert nfa_epsilon.is_equivalent(copie_nfa)


def test_copy_garde_allow_partial(dfa_partiel):
    assert dfa_partiel.copy().allow_partial is True


def test_accepts_est_un_alias_de_accepts_input(dfa_mod3, nfa_epsilon):
    assert dfa_mod3.accepts("aaa")
    assert not dfa_mod3.accepts("a")
    assert nfa_epsilon.accepts("aab")
    assert not nfa_epsilon.accepts("ba")


# ---------------------------------------------------------------------
# is_deterministic
# ---------------------------------------------------------------------

def test_is_deterministic(dfa_mod3, nfa_fig_7_1_a, nfa_epsilon,
                          automate_fig_3_1_c):
    assert dfa_mod3.is_deterministic()
    assert not nfa_fig_7_1_a.is_deterministic()     # 'a' mène à deux états
    assert not nfa_epsilon.is_deterministic()       # epsilon-transition
    # Un NFA dont chaque symbole a une seule cible, sans epsilon.
    assert automate_fig_3_1_c.is_deterministic()
