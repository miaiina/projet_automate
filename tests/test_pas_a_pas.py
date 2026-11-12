# -*- coding: utf-8 -*-
"""
Tests du mode pas à pas : déterminisation, partitions de Moore, élimination
d'états. Les valeurs exactes ont été vérifiées à la main (voir les
commentaires) ; on recoupe aussi avec les méthodes « résultat » existantes
(`determinize`, `equivalence_classes`, `to_regex`), qui sont calculées par
d'autres chemins.
"""
import pytest

from automata_extensions.fa import ExtendedDFA, ExtendedNFA


def F(*etats):
    return frozenset(etats)


# ---------------------------------------------------------------------
# determinization_steps / determinization_table
# ---------------------------------------------------------------------

def test_determinization_steps_calcul_a_la_main(nfa_fig_7_1_a):
    # 1 -a-> {1,2}, 1 -b-> 1, 2 -a,b-> 3 ; final : 3.
    assert nfa_fig_7_1_a.determinization_steps() == [
        (F('1'),           {'a': F('1', '2'),      'b': F('1')}),
        (F('1', '2'),      {'a': F('1', '2', '3'), 'b': F('1', '3')}),
        (F('1', '2', '3'), {'a': F('1', '2', '3'), 'b': F('1', '3')}),
        (F('1', '3'),      {'a': F('1', '2'),      'b': F('1')}),
    ]


def test_determinization_steps_avec_epsilon_et_ensemble_vide(nfa_epsilon):
    # L'état initial est la fermeture epsilon de p : {p, r}.
    etapes = nfa_epsilon.determinization_steps()
    assert etapes[0][0] == F('p', 'r')
    assert etapes[0][1] == {'a': F('p', 'q', 'r'), 'b': F()}
    assert [s for s, _ in etapes] == [
        F('p', 'r'), F('p', 'q', 'r'), F(), F('q'),
    ]


def test_determinization_table_texte_exact(nfa_fig_7_1_a, nfa_epsilon):
    assert nfa_fig_7_1_a.determinization_table() == (
        "         | a       | b\n"
        "---------+---------+------\n"
        "   ->{1} | {1,2}   | {1}\n"
        "   {1,2} | {1,2,3} | {1,3}\n"
        "*{1,2,3} | {1,2,3} | {1,3}\n"
        "  *{1,3} | {1,2}   | {1}"
    )
    assert nfa_epsilon.determinization_table() == (
        "         | a       | b\n"
        "---------+---------+----\n"
        "->*{p,r} | {p,q,r} | ∅\n"
        "*{p,q,r} | {p,q,r} | {q}\n"
        "       ∅ | ∅       | ∅\n"
        "    *{q} | ∅       | {q}"
    )


def test_determinization_steps_coincide_avec_determinize(
    nfa_fig_7_1_a, nfa_epsilon, automate_fig_3_1_c, automate_fig_3_1_e,
    automate_fig_3_1_f,
):
    for nfa in (nfa_fig_7_1_a, nfa_epsilon, automate_fig_3_1_c,
                automate_fig_3_1_e, automate_fig_3_1_f):
        dfa = nfa.determinize()
        etapes = nfa.determinization_steps()
        assert {s for s, _ in etapes} == set(dfa.states)
        assert etapes[0][0] == dfa.initial_state
        for sous_ensemble, cibles in etapes:
            assert cibles == dfa.transitions[sous_ensemble]


def test_determinization_steps_refuse_un_dfa(dfa_mod3):
    with pytest.raises(NotImplementedError):
        dfa_mod3.determinization_steps()


# ---------------------------------------------------------------------
# moore_partitions
# ---------------------------------------------------------------------

def test_moore_partitions_cours_6_calcul_a_la_main(automate_cours_6):
    assert automate_cours_6.moore_partitions() == [
        [F('1', '2', '4', '5', '6', '7', '8'), F('3')],
        [F('1', '5', '7'), F('2', '8'), F('3'), F('4', '6')],
        [F('1', '5'), F('2', '8'), F('3'), F('4', '6'), F('7')],
    ]
    assert automate_cours_6.moore_partitions_str() == (
        "P0 : {1,2,4,5,6,7,8} | {3}\n"
        "P1 : {1,5,7} | {2,8} | {3} | {4,6}\n"
        "P2 : {1,5} | {2,8} | {3} | {4,6} | {7}"
    )


def test_moore_partitions_petit_exemple(dfa_fig_6_1_a):
    assert dfa_fig_6_1_a.moore_partitions() == [
        [F('1', '2'), F('3', '4')],
        [F('1'), F('2'), F('3', '4')],
    ]


def test_moore_partitions_derniere_partition_et_classes_dequivalence(
    dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
    automate_cours_6, automate_cours_6_bis,
):
    for automate in (dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                     automate_cours_6, automate_cours_6_bis):
        partitions = automate.moore_partitions()
        # Recoupement avec la table des paires (autre algorithme).
        assert set(partitions[-1]) == set(
            frozenset(c) for c in automate.equivalence_classes()
        )
        # Chaque partition raffine strictement la précédente.
        for avant, apres in zip(partitions, partitions[1:]):
            assert len(apres) > len(avant)
            assert all(any(b <= a for a in avant) for b in apres)
        # Chaque partition recouvre tous les états, sans chevauchement.
        for partition in partitions:
            assert sum(len(b) for b in partition) == len(automate.states)
            assert set().union(*partition) == set(automate.states)


def test_moore_partitions_exige_un_dfa_complet(nfa_epsilon, dfa_partiel):
    with pytest.raises(NotImplementedError):
        nfa_epsilon.moore_partitions()
    with pytest.raises(ValueError):
        dfa_partiel.moore_partitions()


# ---------------------------------------------------------------------
# to_regex_steps
# ---------------------------------------------------------------------

def test_to_regex_steps_texte_exact(dfa_fig_3_1_a):
    # 1 -a-> 2 (final), 3 est un puits ; calcul à la main (suppression de 2 :
    # début -> 3 devient b | a·a*·b, et début -> fin devient a·a*).
    assert dfa_fig_3_1_a.to_regex_steps_str() == (
        "Départ :\n"
        "  début -> 1 : ()\n"
        "  1 -> 2 : a\n"
        "  1 -> 3 : b\n"
        "  2 -> 2 : a\n"
        "  2 -> 3 : b\n"
        "  2 -> fin : ()\n"
        "  3 -> 3 : (a|b)\n"
        "Suppression de 1 :\n"
        "  début -> 2 : a\n"
        "  début -> 3 : b\n"
        "  2 -> 2 : a\n"
        "  2 -> 3 : b\n"
        "  2 -> fin : ()\n"
        "  3 -> 3 : (a|b)\n"
        "Suppression de 2 :\n"
        "  début -> 3 : (b|aa*b)\n"
        "  début -> fin : aa*\n"
        "  3 -> 3 : (a|b)\n"
        "Suppression de 3 :\n"
        "  début -> fin : aa*"
    )


def test_to_regex_steps_choix_de_lordre(dfa_fig_3_1_a):
    texte = dfa_fig_3_1_a.to_regex_steps_str(order=['3', '2', '1'])
    # Supprimer d'abord le puits 3 ne crée aucun chemin : on retire ses arêtes.
    assert "Suppression de 3 :\n  début -> 1 : ()\n  1 -> 2 : a\n" in texte
    assert texte.endswith("Suppression de 1 :\n  début -> fin : aa*")


def test_to_regex_steps_structure_et_resultat(
    dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, nfa_epsilon, nfa_fig_7_1_a,
    dfa_mot_vide_seul,
):
    for automate in (dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, nfa_epsilon,
                     nfa_fig_7_1_a, dfa_mot_vide_seul):
        etapes = automate.to_regex_steps()
        assert len(etapes) == len(automate.states) + 1
        assert etapes[0]["supprime"] is None
        assert [e["supprime"] for e in etapes[1:]] == sorted(automate.states)
        # La dernière étape n'a plus que l'arête début -> fin.
        derniere = etapes[-1]["aretes"]
        assert len(derniere) == 1 and derniere[0][:2] == ("début", "fin")
        # Son expression est celle de to_regex().
        assert derniere[0][2] == automate.to_regex()


def test_to_regex_steps_langage_vide(dfa_vide):
    # Aucun chemin de début à fin : plus aucune arête à la fin.
    assert dfa_vide.to_regex_steps()[-1]["aretes"] == []
    assert dfa_vide.to_regex() == "∅"


def test_to_regex_steps_un_autre_ordre_donne_le_meme_langage(dfa_mod3):
    for ordre in (['0', '1', '2'], ['2', '1', '0'], ['1', '0', '2']):
        resultat = dfa_mod3.to_regex_steps(order=ordre)[-1]["aretes"][0][2]
        retour = ExtendedNFA.from_regex(resultat, input_symbols={'a', 'b'})
        assert dfa_mod3.is_equivalent(retour)


def test_to_regex_steps_valide_lordre(dfa_mod3):
    for mauvais in (['0', '1'], ['0', '1', '1'], ['0', '1', '2', '3'],
                    ['0', '1', 'x']):
        with pytest.raises(ValueError):
            dfa_mod3.to_regex_steps(order=mauvais)


def test_to_regex_ne_change_pas_apres_lajout_du_journal(dfa_mod3):
    assert dfa_mod3.to_regex() == "(b*|b*ab*a((b|ab*ab*a))*ab*)"
