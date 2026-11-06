# -*- coding: utf-8 -*-
"""
Tests de la phase 5 : grammaires régulières (linéaires à droite),
passage automate <-> grammaire, dérivations.

Arbitre indépendant : `Grammar.generates(mot)`, qui décide si une
grammaire engendre un mot en suivant directement ses règles, sans
construire d'automate. On compare ensuite l'automate et la grammaire sur
tous les mots jusqu'à une certaine longueur.
"""
from itertools import product

import pytest

from automata.fa.dfa import DFA
from automata.fa.nfa import NFA

from automata_extensions.fa import ExtendedNFA
from automata_extensions.grammar.grammar import (
    DerivationStep, Grammar, Rule,
)


def tous_les_mots(alphabet, longueur_max):
    for longueur in range(longueur_max + 1):
        for lettres in product(sorted(alphabet), repeat=longueur):
            yield "".join(lettres)


# ---------------------------------------------------------------------
# Grammar : analyse d'un texte, affichage, langage engendré
# ---------------------------------------------------------------------

def test_from_string_regles():
    g = Grammar.from_string("S -> aS | b")
    assert g.start == "S"
    assert g.rules == (Rule("S", "a", "S"), Rule("S", "b", None))
    assert g.non_terminals == {"S"}
    assert g.terminals == {"a", "b"}


def test_from_string_plusieurs_lignes_epsilon_et_espaces():
    g = Grammar.from_string("S -> a S | b T | ε\nT -> b T | a")
    assert g.start == "S"
    assert g.rules == (
        Rule("S", "a", "S"), Rule("S", "b", "T"), Rule("S", "", None),
        Rule("T", "b", "T"), Rule("T", "a", None),
    )
    # Alternative vide = mot vide ; ';' sépare aussi les règles.
    assert Grammar.from_string("S -> aS |").rules == (
        Rule("S", "a", "S"), Rule("S", "", None),
    )
    assert Grammar.from_string("S -> aT; T -> b").start == "S"


def test_from_string_noms_de_plusieurs_caracteres_et_chiffres():
    g = Grammar.from_string("q0 -> aq1 | b\nq1 -> bq0")
    assert g.rules == (
        Rule("q0", "a", "q1"), Rule("q0", "b", None), Rule("q1", "b", "q0"),
    )
    g = Grammar.from_string("0 -> a1 | b0 | ε\n1 -> a0")
    assert Rule("0", "a", "1") in g.rules and Rule("1", "a", "0") in g.rules


def test_from_string_mot_de_plusieurs_terminaux():
    g = Grammar.from_string("S -> abS | c")
    assert g.rules == (Rule("S", "ab", "S"), Rule("S", "c", None))


def test_str_est_le_format_classique_et_se_relit():
    for texte in ["S -> aS | b", "S -> aS | bT | ε\nT -> bT | a"]:
        g = Grammar.from_string(texte)
        assert str(g) == texte
        assert Grammar.from_string(str(g)) == g


def test_from_string_erreurs():
    for texte in ["", "S aS", "S -> aSb", "S T -> a", "-> a"]:
        with pytest.raises(ValueError):
            Grammar.from_string(texte)


def test_generates():
    g = Grammar.from_string("S -> aS | b")          # langage a*b
    for mot in ["b", "ab", "aab", "aaaab"]:
        assert g.generates(mot), mot
    for mot in ["", "a", "ba", "abb", "bb"]:
        assert not g.generates(mot), mot


def test_generates_ne_boucle_pas_sur_des_regles_unitaires():
    g = Grammar.from_string("A -> B | a\nB -> A")
    assert g.generates("a")
    assert not g.generates("b")
    assert not g.generates("")


# ---------------------------------------------------------------------
# to_grammar
# ---------------------------------------------------------------------

def test_to_grammar_est_une_grammar(dfa_mod3):
    assert type(dfa_mod3.to_grammar()).__name__ == "Grammar"


def test_to_grammar_texte_attendu(dfa_mod3, dfa_fig_3_1_a):
    assert str(dfa_mod3.to_grammar()) == (
        "0 -> a1 | b0 | ε\n"
        "1 -> a2 | b1\n"
        "2 -> a0 | b2"
    )
    # fig 3.1.a : états 1 (initial), 2 (final), 3 (puits).
    assert str(dfa_fig_3_1_a.to_grammar()) == (
        "1 -> a2 | b3\n"
        "2 -> a2 | b3 | ε\n"
        "3 -> a3 | b3"
    )


def test_to_grammar_meme_langage_que_lautomate(
    dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, dfa_mod3, dfa_vide,
    dfa_mot_vide_seul, nfa_fig_7_1_a, nfa_epsilon,
):
    for automate in (dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                     dfa_mod3, dfa_vide, dfa_mot_vide_seul,
                     nfa_fig_7_1_a, nfa_epsilon):
        grammaire = automate.to_grammar()
        for mot in tous_les_mots(automate.input_symbols, 6):
            assert grammaire.generates(mot) == automate.accepts_input(mot), mot


def test_to_grammar_sans_epsilon_transition(nfa_epsilon):
    # Les epsilon-transitions sont supprimées avant la construction : il
    # n'y a donc que des règles A -> a B ou A -> ε.
    for regle in nfa_epsilon.to_grammar().rules:
        assert len(regle.word) <= 1
        assert regle.word != "" or regle.right is None


# ---------------------------------------------------------------------
# from_grammar / from_grammar_string
# ---------------------------------------------------------------------

def test_from_grammar_string_exemple_de_la_doc():
    nfa = ExtendedNFA.from_grammar_string("S -> aS | b")
    assert isinstance(nfa, NFA)
    # Le langage est a*b : "aab" est bien engendré (S => aS => aaS => aab).
    assert nfa.accepts_input("aab")
    assert nfa.accepts_input("b")
    assert not nfa.accepts_input("aba")
    assert not nfa.accepts_input("")


def test_from_grammar_meme_langage_que_la_grammaire():
    for texte in [
        "S -> aS | b",
        "S -> aS | bT | ε\nT -> bT | a",
        "S -> abS | c",                     # règle à plusieurs lettres
        "S -> A | b\nA -> aS",              # règle unitaire (epsilon)
        "S -> ε",
        "S -> aS | bS | ab",                # mot terminal de 2 lettres
        "S -> aT\nT -> bS | ε",
    ]:
        grammaire = Grammar.from_string(texte)
        alphabet = {"a", "b", "c"}
        nfa = ExtendedNFA.from_grammar(grammaire, input_symbols=alphabet)
        for mot in tous_les_mots(alphabet, 6):
            assert nfa.accepts_input(mot) == grammaire.generates(mot), (
                texte, mot,
            )


def test_from_grammar_alphabet_par_defaut_et_erreur():
    nfa = ExtendedNFA.from_grammar_string("S -> aS | b")
    assert nfa.input_symbols == {"a", "b"}
    with pytest.raises(ValueError):
        ExtendedNFA.from_grammar_string("S -> aS | b", input_symbols={"a"})


def test_from_grammar_ne_reutilise_pas_un_nom_detat():
    # Le non-terminal "F" existe déjà : l'état final ajouté est renommé.
    nfa = ExtendedNFA.from_grammar_string("F -> aF | b")
    assert nfa.accepts_input("aab")
    assert len(nfa.states) == 2


def test_aller_retour_automate_grammaire_automate(
    dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, dfa_mod3, dfa_vide,
    dfa_mot_vide_seul, nfa_fig_7_1_a, nfa_epsilon,
):
    # Vraie équivalence de langages (pas seulement jusqu'à une longueur).
    for automate in (dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                     dfa_mod3, dfa_vide, dfa_mot_vide_seul,
                     nfa_fig_7_1_a, nfa_epsilon):
        retour = ExtendedNFA.from_grammar(
            automate.to_grammar(), input_symbols=automate.input_symbols
        )
        assert automate.is_equivalent(retour)


# ---------------------------------------------------------------------
# derivation_tree
# ---------------------------------------------------------------------

def test_derivation_tree_exemple_de_la_doc(dfa_mod3):
    etape = dfa_mod3.derivation_tree("aaa")
    assert isinstance(etape, DerivationStep)
    assert etape.word() == "aaa"
    assert etape.sequence() == "0 => a1 => aa2 => aaa0 => aaa"


def test_derivation_tree_mot_vide_et_mot_avec_b(dfa_mod3):
    assert dfa_mod3.derivation_tree("").sequence() == "0 => ε"
    assert dfa_mod3.derivation_tree("ababab").word() == "ababab"   # 3 fois a
    # "ab" n'est pas accepté (un seul a) : pas de dérivation.
    with pytest.raises(ValueError):
        dfa_mod3.derivation_tree("ab")


def test_derivation_tree_chaque_etape_applique_une_regle_de_la_grammaire(
    dfa_mod3, nfa_fig_7_1_a, nfa_epsilon,
):
    cas = [(dfa_mod3, "aabaabaab"), (nfa_fig_7_1_a, "baab"),
           (nfa_epsilon, "aab"), (nfa_epsilon, "")]
    for automate, mot in cas:
        grammaire = automate.to_grammar()
        etapes = automate.derivation_tree(mot).steps()
        assert etapes[0].form() == grammaire.start
        assert etapes[-1].word() == mot
        assert etapes[-1].non_terminal is None
        for etape, suivante in zip(etapes, etapes[1:]):
            regle = etape.rule
            assert regle in grammaire.rules
            assert etape.non_terminal == regle.left
            assert suivante.prefix == etape.prefix + regle.word
            assert suivante.non_terminal == regle.right


def test_derivation_tree_refuse_un_mot_hors_langage(nfa_fig_7_1_a):
    with pytest.raises(ValueError):
        nfa_fig_7_1_a.derivation_tree("ba")   # l'avant-dernière lettre est b
