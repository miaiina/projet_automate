# -*- coding: utf-8 -*-
"""
Tests des opérations (produit, intersection, union, différence, complément,
concaténation, étoile) et des relations (langage vide/fini, plus court mot,
inclusion, équivalence, isomorphisme) : phase 4.

Arbitre indépendant : on calcule l'ensemble des mots acceptés jusqu'à une
longueur donnée, et on compare avec les opérations ensemblistes de Python
(&, |, -, ^) ou avec une définition directe (découpage d'un mot pour la
concaténation et l'étoile). Aucun produit d'automates n'intervient dans
la vérification.
"""
from itertools import product as produit_cartesien

import pytest

from automata.fa.dfa import DFA
from automata.fa.nfa import NFA

from automata_extensions.fa import ExtendedDFA, ExtendedNFA


def tous_les_mots(alphabet, longueur_max):
    for longueur in range(longueur_max + 1):
        for lettres in produit_cartesien(sorted(alphabet), repeat=longueur):
            yield "".join(lettres)


def langage(automate, alphabet=("a", "b"), longueur_max=6):
    """Ensemble des mots acceptés, de longueur au plus `longueur_max`."""
    return {
        mot for mot in tous_les_mots(alphabet, longueur_max)
        if automate.accepts_input(mot)
    }


# ---------------------------------------------------------------------
# Opérations booléennes
# ---------------------------------------------------------------------

def test_operations_booleennes_meme_langage_que_les_ensembles(
    dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_mod3, nfa_fig_7_1_a, nfa_epsilon,
):
    automates = (dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_mod3,
                 nfa_fig_7_1_a, nfa_epsilon)
    for a in automates:
        for b in automates:
            la, lb = langage(a), langage(b)
            assert langage(a.intersection(b)) == la & lb
            assert langage(a.difference(b)) == la - lb
            assert langage(a.symmetric_difference(b)) == la ^ lb
            assert langage(a.union(b)) == la | lb


def test_operations_booleennes_renvoient_un_dfa_complet(dfa_mod3, nfa_epsilon):
    for resultat in (dfa_mod3.intersection(nfa_epsilon),
                     nfa_epsilon.difference(dfa_mod3),
                     dfa_mod3.union(dfa_mod3),
                     nfa_epsilon.complement()):
        assert isinstance(resultat, DFA)
        assert resultat.is_complete()


def test_complement(dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_mod3, nfa_fig_7_1_a,
                    nfa_epsilon):
    tous = {m for m in tous_les_mots(('a', 'b'), 6)}
    for automate in (dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_mod3,
                     nfa_fig_7_1_a, nfa_epsilon):
        assert langage(automate.complement()) == tous - langage(automate)


def test_complement_dun_dfa_partiel(dfa_partiel):
    # a* sur {a,b} : le complément est l'ensemble des mots qui contiennent b.
    complement = dfa_partiel.complement()
    assert complement.is_complete()
    for mot in tous_les_mots(('a', 'b'), 5):
        assert complement.accepts_input(mot) == ('b' in mot)


def test_product_avec_is_final_personnalise(dfa_mod3):
    # Produit de l'automate avec lui-même : seuls les couples diagonaux
    # sont accessibles (l'automate est déterministe).
    diagonal = dfa_mod3.product(dfa_mod3, is_final=lambda s1, s2: s1 == s2)
    assert sorted(diagonal.states) == [('0', '0'), ('1', '1'), ('2', '2')]
    assert diagonal.final_states == set(diagonal.states)


def test_operations_avec_des_alphabets_differents(dfa_unaire, dfa_mod3):
    # dfa_unaire : a* sur {a} ; dfa_mod3 : nombre de 'a' multiple de 3 sur
    # {a,b}. On travaille sur l'union des alphabets {a,b}.
    attendu = {
        mot for mot in tous_les_mots(('a', 'b'), 6)
        if set(mot) <= {'a'} and mot.count('a') % 3 == 0
    }
    assert langage(dfa_unaire.intersection(dfa_mod3)) == attendu
    # Sur {a} seulement, tout mot de a* est dans dfa_unaire ; dans la
    # différence il reste donc les mots de a* qui ne sont pas multiples de 3.
    difference = dfa_unaire.difference(dfa_mod3)
    for mot in tous_les_mots(('a', 'b'), 6):
        attendu_mot = set(mot) <= {'a'} and mot.count('a') % 3 != 0
        assert difference.accepts_input(mot) == attendu_mot


def test_option_minify(dfa_fig_6_1_a, dfa_mod3):
    brut = dfa_fig_6_1_a.union(dfa_mod3)
    minimal = dfa_fig_6_1_a.union(dfa_mod3, minify=True)
    assert langage(brut) == langage(minimal)
    assert len(minimal.states) <= len(brut.states)
    assert minimal.is_minimal()


def test_union_dun_nfa_est_un_nfa(nfa_fig_7_1_a, nfa_epsilon, dfa_mod3):
    union = nfa_fig_7_1_a.union(nfa_epsilon)
    assert isinstance(union, NFA)
    assert langage(union) == langage(nfa_fig_7_1_a) | langage(nfa_epsilon)
    assert isinstance(dfa_mod3.union(dfa_mod3), DFA)


# ---------------------------------------------------------------------
# Opérations rationnelles
# ---------------------------------------------------------------------

def appartient_a_la_concatenation(a, b, mot):
    return any(
        a.accepts_input(mot[:i]) and b.accepts_input(mot[i:])
        for i in range(len(mot) + 1)
    )


def appartient_a_letoile(a, mot):
    # atteignable[j] : le préfixe de longueur j est dans L*
    atteignable = [True] + [False] * len(mot)
    for j in range(1, len(mot) + 1):
        atteignable[j] = any(
            atteignable[i] and a.accepts_input(mot[i:j]) for i in range(j)
        )
    return atteignable[len(mot)]


def test_concatenation(dfa_fig_6_1_a, dfa_mod3, nfa_fig_7_1_a, nfa_epsilon):
    automates = (dfa_fig_6_1_a, dfa_mod3, nfa_fig_7_1_a, nfa_epsilon)
    for a in automates:
        for b in automates:
            produit = a.concatenation(b)
            assert isinstance(produit, ExtendedNFA)
            for mot in tous_les_mots(('a', 'b'), 5):
                assert produit.accepts_input(mot) == (
                    appartient_a_la_concatenation(a, b, mot)
                ), mot


def test_kleene_star(dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_mod3, nfa_fig_7_1_a,
                     nfa_epsilon):
    for automate in (dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_mod3,
                     nfa_fig_7_1_a, nfa_epsilon):
        etoile = automate.kleene_star()
        assert isinstance(etoile, ExtendedNFA)
        assert etoile.accepts_input("")
        for mot in tous_les_mots(('a', 'b'), 6):
            assert etoile.accepts_input(mot) == appartient_a_letoile(
                automate, mot
            ), mot


# ---------------------------------------------------------------------
# is_empty, is_finite, shortest_word
# ---------------------------------------------------------------------

def test_is_empty(dfa_vide, dfa_mod3, dfa_fig_3_1_a, nfa_epsilon):
    assert dfa_vide.is_empty()
    assert not dfa_mod3.is_empty()
    assert not nfa_epsilon.is_empty()
    assert dfa_fig_3_1_a.difference(dfa_fig_3_1_a).is_empty()


def test_is_finite(dfa_fini, dfa_vide, dfa_mot_vide_seul, dfa_mod3,
                   dfa_fig_3_1_a, nfa_epsilon):
    assert dfa_fini.is_finite()
    assert dfa_vide.is_finite()
    assert dfa_mot_vide_seul.is_finite()
    assert not dfa_mod3.is_finite()
    assert not dfa_fig_3_1_a.is_finite()
    assert not nfa_epsilon.is_finite()


def test_is_finite_ignore_un_cycle_inutile():
    # Le cycle sur 'x' est accessible mais ne mène à aucun état final :
    # le langage reste {a}, donc fini.
    automate = ExtendedDFA(
        states={'0', '1', 'x'},
        input_symbols={'a', 'b'},
        transitions={
            '0': {'a': '1', 'b': 'x'},
            '1': {'a': 'x', 'b': 'x'},
            'x': {'a': 'x', 'b': 'x'},
        },
        initial_state='0',
        final_states={'1'},
    )
    assert automate.is_finite()


def test_is_finite_un_cycle_depsilon_ne_rend_pas_le_langage_infini():
    automate = ExtendedNFA(
        states={'p', 'q'},
        input_symbols={'a'},
        transitions={'p': {'a': {'q'}}, 'q': {'': {'p'}}},
        initial_state='p',
        final_states={'q'},
    )
    # p -a-> q -eps-> p -a-> q ... : "a", "aa", "aaa"... : infini !
    assert not automate.is_finite()
    # Cycle d'epsilon seul : langage {""} .
    seul = ExtendedNFA(
        states={'p', 'q'},
        input_symbols={'a'},
        transitions={'p': {'': {'q'}}, 'q': {'': {'p'}}},
        initial_state='p',
        final_states={'q'},
    )
    assert seul.is_finite()
    assert seul.accepts_input("")


def test_shortest_word(dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a,
                       dfa_table_6_1_a, nfa_fig_7_1_a, nfa_epsilon, dfa_vide):
    assert dfa_mod3.shortest_word() == ""
    assert dfa_fig_3_1_a.shortest_word() == "a"
    assert dfa_fig_6_1_a.shortest_word() == "ab"
    assert dfa_table_6_1_a.shortest_word() == "bb"
    assert nfa_fig_7_1_a.shortest_word() == "aa"
    assert nfa_epsilon.shortest_word() == ""
    assert dfa_vide.shortest_word() is None


# ---------------------------------------------------------------------
# Inclusion, équivalence, disjonction
# ---------------------------------------------------------------------

def test_inclusion(dfa_unaire, dfa_fig_3_1_a):
    # a+ (fig 3.1.a) est inclus dans a* (dfa_unaire), pas l'inverse.
    assert dfa_fig_3_1_a.is_included_in(dfa_unaire)
    assert not dfa_unaire.is_included_in(dfa_fig_3_1_a)
    assert dfa_fig_3_1_a.inclusion_counterexample(dfa_unaire) is None
    # Le mot vide est dans a* mais pas dans a+ : c'est le plus court
    # contre-exemple (et "" est bien différent de None).
    assert dfa_unaire.inclusion_counterexample(dfa_fig_3_1_a) == ""


def test_inclusion_est_reflexive(dfa_mod3, nfa_epsilon):
    assert dfa_mod3.is_included_in(dfa_mod3)
    assert nfa_epsilon.is_included_in(nfa_epsilon)


def test_equivalence_avec_des_conversions_deja_testees(
    dfa_fig_6_1_a, dfa_mod3, nfa_fig_7_1_a, nfa_epsilon,
):
    # Vraie équivalence de langages (pas une comparaison jusqu'à une
    # longueur donnée) entre un automate et ses transformés.
    assert dfa_fig_6_1_a.is_equivalent(dfa_fig_6_1_a.minimize())
    assert dfa_mod3.is_equivalent(dfa_mod3.brzozowski_minimize())
    assert nfa_epsilon.is_equivalent(nfa_epsilon.determinize())
    assert nfa_epsilon.is_equivalent(nfa_epsilon.remove_epsilon_transitions())
    assert nfa_fig_7_1_a.is_equivalent(nfa_fig_7_1_a.reverse().reverse())


def test_equivalence_avec_les_expressions_regulieres(dfa_mod3, nfa_epsilon):
    for automate in (dfa_mod3, nfa_epsilon):
        for expression in (automate.to_regex(), automate.to_regex_arden(),
                           automate.to_regex_optimum()):
            retour = ExtendedNFA.from_regex(
                expression, input_symbols=automate.input_symbols
            )
            assert automate.is_equivalent(retour)


def test_equivalence_contre_exemple(dfa_mod3, dfa_fig_3_1_a):
    assert not dfa_mod3.is_equivalent(dfa_fig_3_1_a)
    # mod3 accepte le mot vide, pas a+.
    assert dfa_mod3.equivalence_counterexample(dfa_fig_3_1_a) == ""


def test_equivalence_distingue_deux_langages_proches(dfa_mod3):
    # Même automate, avec l'état 1 final en plus : le plus court mot qui
    # les distingue est "a" (qui mène à l'état 1).
    autre = ExtendedDFA(
        states={'0', '1', '2'},
        input_symbols={'a', 'b'},
        transitions=dfa_mod3.transitions,
        initial_state='0',
        final_states={'0', '1'},
    )
    assert dfa_mod3.equivalence_counterexample(autre) == "a"


def test_is_disjoint_from(dfa_fig_3_1_a, dfa_fini, dfa_mod3):
    # a+ et {a, ab} ont "a" en commun ; a+ et {ab} seraient disjoints.
    assert not dfa_fig_3_1_a.is_disjoint_from(dfa_fini)
    assert dfa_fig_3_1_a.is_disjoint_from(dfa_fig_3_1_a.complement())
    # mod3 contient le mot vide, fig 3.1.a non ; "aaa" est dans les deux.
    assert not dfa_mod3.is_disjoint_from(dfa_fig_3_1_a)


# ---------------------------------------------------------------------
# Isomorphisme
# ---------------------------------------------------------------------

def renommer(dfa, renommage):
    return ExtendedDFA(
        states={renommage[e] for e in dfa.states},
        input_symbols=dfa.input_symbols,
        transitions={
            renommage[e]: {s: renommage[t] for s, t in table.items()}
            for e, table in dfa.transitions.items()
        },
        initial_state=renommage[dfa.initial_state],
        final_states={renommage[e] for e in dfa.final_states},
    )


def test_isomorphisme_apres_renommage(dfa_mod3):
    copie = renommer(dfa_mod3, {'0': 'x', '1': 'y', '2': 'z'})
    assert dfa_mod3.is_isomorphic_to(copie)
    assert copie.is_isomorphic_to(dfa_mod3)
    assert dfa_mod3.is_isomorphic_to(dfa_mod3)


def test_isomorphisme_refuse_un_changement_de_structure(dfa_mod3):
    autre_final = ExtendedDFA(
        states=dfa_mod3.states,
        input_symbols=dfa_mod3.input_symbols,
        transitions=dfa_mod3.transitions,
        initial_state='0',
        final_states={'1'},
    )
    assert not dfa_mod3.is_isomorphic_to(autre_final)
    # Permuter deux lettres donne un automate de même forme ET de même
    # langage ici, mais pas le même automate : on teste un vrai changement.
    autre_transition = ExtendedDFA(
        states={'0', '1', '2'},
        input_symbols={'a', 'b'},
        transitions={
            '0': {'a': '1', 'b': '0'},
            '1': {'a': '2', 'b': '1'},
            '2': {'a': '1', 'b': '2'},
        },
        initial_state='0',
        final_states={'0'},
    )
    assert not dfa_mod3.is_isomorphic_to(autre_transition)


def test_deux_dfa_minimaux_dun_meme_langage_sont_isomorphes(
    dfa_fig_6_1_a, dfa_table_6_1_a,
):
    for automate in (dfa_fig_6_1_a, dfa_table_6_1_a):
        par_moore = automate.minimize()
        par_brzozowski = automate.brzozowski_minimize()
        par_moore_frozenset = automate.minimize(keep_original_names=False)
        assert par_moore.is_isomorphic_to(par_brzozowski)
        assert par_moore.is_isomorphic_to(par_moore_frozenset)
        # L'automate de départ a plus d'états : pas isomorphe au minimal.
        assert not automate.is_isomorphic_to(par_moore)


def test_isomorphisme_alphabets_differents(dfa_unaire, dfa_partiel):
    # Même forme (un état qui boucle sur 'a') mais pas le même alphabet.
    assert not dfa_unaire.is_isomorphic_to(dfa_partiel)


def test_isomorphisme_refuse_un_nfa(nfa_fig_7_1_a, dfa_mod3):
    with pytest.raises(NotImplementedError):
        nfa_fig_7_1_a.is_isomorphic_to(dfa_mod3)
