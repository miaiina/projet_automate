# -*- coding: utf-8 -*-
"""
Tests des conversions automate -> expression régulière (phase 3b) et
de l'arbre d'expressions (`automata_extensions.regex.regex`).

Arbitre indépendant : le module `re` de la bibliothèque standard. Les
expressions produites utilisent seulement `|`, `*`, `()` et des lettres,
qui ont le même sens en syntaxe `re` et en syntaxe automata-lib. On
vérifie que l'expression reconnaît exactement les mêmes mots que
l'automate, pour tous les mots jusqu'à une certaine longueur.
"""
import re
from itertools import product

import pytest

from automata_extensions.fa import ExtendedDFA, ExtendedNFA
from automata_extensions.regex.regex import (
    Alt, Cat, EMPTY, EPS, Star, Sym, alt, cat, parse, simplify, star,
    to_string,
)


def tous_les_mots(alphabet, longueur_max):
    for longueur in range(longueur_max + 1):
        for lettres in product(sorted(alphabet), repeat=longueur):
            yield "".join(lettres)


def accepte(expression, mot):
    if expression == "∅":
        return False
    return re.fullmatch(expression, mot) is not None


def meme_langage(automate, expression, longueur_max=6):
    return all(
        automate.accepts_input(mot) == accepte(expression, mot)
        for mot in tous_les_mots(automate.input_symbols, longueur_max)
    )


# ---------------------------------------------------------------------
# to_regex, to_regex_arden, variantes optimum : même langage que l'automate
# ---------------------------------------------------------------------

def test_to_regex_meme_langage(
    dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, dfa_mod3,
    nfa_fig_7_1_a, nfa_epsilon,
):
    for automate in (dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                     dfa_mod3, nfa_fig_7_1_a, nfa_epsilon):
        assert meme_langage(automate, automate.to_regex())


def test_to_regex_arden_meme_langage(
    dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, dfa_mod3,
    nfa_fig_7_1_a, nfa_epsilon,
):
    for automate in (dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                     dfa_mod3, nfa_fig_7_1_a, nfa_epsilon):
        assert meme_langage(automate, automate.to_regex_arden())


def test_to_regex_optimum_meme_langage(
    dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, dfa_mod3,
    nfa_fig_7_1_a, nfa_epsilon,
):
    for automate in (dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                     dfa_mod3, nfa_fig_7_1_a, nfa_epsilon):
        assert meme_langage(automate, automate.to_regex_optimum())


def test_to_regex_arden_optimum_meme_langage(
    dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, dfa_mod3,
    nfa_fig_7_1_a, nfa_epsilon,
):
    for automate in (dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                     dfa_mod3, nfa_fig_7_1_a, nfa_epsilon):
        assert meme_langage(automate, automate.to_regex_arden_optimum())


def test_optimum_nest_jamais_plus_long(dfa_fig_6_1_a, dfa_mod3, nfa_epsilon):
    for automate in (dfa_fig_6_1_a, dfa_mod3, nfa_epsilon):
        assert len(automate.to_regex_optimum()) <= len(automate.to_regex())
        assert (
            len(automate.to_regex_arden_optimum())
            <= len(automate.to_regex_arden())
        )


def test_to_regex_optimum_dfa_mod3_est_court(dfa_mod3):
    # (b|ab*ab*a)* est connue ; on exige seulement une expression pas
    # plus longue que celle-là.
    assert len(dfa_mod3.to_regex_optimum()) <= len("(b|ab*ab*a)*")


# ---------------------------------------------------------------------
# Cas limites : langage vide, mot vide seul
# ---------------------------------------------------------------------

def test_langage_vide(dfa_vide):
    assert dfa_vide.to_regex() == "∅"
    assert dfa_vide.to_regex_arden() == "∅"
    assert dfa_vide.to_regex_optimum() == "∅"
    assert dfa_vide.to_regex_arden_optimum() == "∅"


def test_mot_vide_seul(dfa_mot_vide_seul):
    assert dfa_mot_vide_seul.to_regex() == "()"
    assert dfa_mot_vide_seul.to_regex_arden() == "()"
    assert dfa_mot_vide_seul.to_regex_optimum() == "()"
    assert dfa_mot_vide_seul.to_regex_arden_optimum() == "()"


def test_symbole_non_ecrivable_leve_valueerror():
    automate = ExtendedDFA(
        states={'0'},
        input_symbols={'*'},
        transitions={'0': {'*': '0'}},
        initial_state='0',
        final_states={'0'},
    )
    with pytest.raises(ValueError):
        automate.to_regex()


# ---------------------------------------------------------------------
# Arbre d'expressions : constructeurs, simplification, affichage
# ---------------------------------------------------------------------

a, b, c = Sym('a'), Sym('b'), Sym('c')


def test_to_string_parentheses():
    assert to_string(a) == "a"
    assert to_string(EPS) == "()"
    assert to_string(EMPTY) == "∅"
    assert to_string(alt(a, b)) == "a|b"
    assert to_string(cat(a, alt(b, c))) == "a(b|c)"
    assert to_string(star(alt(a, b))) == "(a|b)*"
    assert to_string(star(cat(a, b))) == "(ab)*"
    assert to_string(star(a)) == "a*"
    assert to_string(alt(a, EPS)) == "a|()"


def test_constructeurs_identites_triviales():
    assert alt(a, EMPTY) == a
    assert alt(a, a) == a
    assert alt(alt(a, b), c) == alt(a, b, c)
    assert cat(a, EPS) == a
    assert cat(a, EMPTY) == EMPTY
    assert cat(cat(a, b), c) == cat(a, b, c)
    assert star(EMPTY) == EPS
    assert star(EPS) == EPS
    assert star(star(a)) == star(a)


def test_simplify():
    assert simplify(alt(a, star(a))) == star(a)
    assert simplify(alt(star(a), EPS)) == star(a)
    assert simplify(star(alt(a, EPS))) == star(a)
    assert simplify(cat(star(a), star(a))) == star(a)
    # Une expression déjà simple ne change pas.
    assert simplify(cat(a, alt(b, c))) == cat(a, alt(b, c))


# ---------------------------------------------------------------------
# Analyseur d'expressions (phase 3c)
# ---------------------------------------------------------------------

def test_parse_arbre():
    assert parse("a") == a
    assert parse("(a|b)*a") == cat(star(alt(a, b)), a)
    assert parse("a+") == cat(a, star(a))
    assert parse("a?") == alt(a, EPS)
    assert parse("()") == EPS
    assert parse("") == EPS
    assert parse("a|") == alt(a, EPS)
    assert parse("∅") == EMPTY
    assert parse(".a", alphabet={'a', 'b'}) == cat(alt(a, b), a)


def test_parse_et_to_string_sont_coherents():
    for texte in ["a", "a|b", "ab", "a*", "(a|b)*a", "a(b|c)*", "(ab)*c",
                  "a|()", "()", "∅"]:
        assert to_string(parse(texte)) == texte


def test_parse_erreurs():
    for texte in ["(a", "a)", "*a", "+", "a&b", "a{2}", "a\\b"]:
        with pytest.raises(ValueError):
            parse(texte)
    with pytest.raises(ValueError):
        parse("c", alphabet={'a', 'b'})      # lettre hors de l'alphabet
    with pytest.raises(ValueError):
        parse(".a")                          # joker sans alphabet


# ---------------------------------------------------------------------
# Thompson : ExtendedNFA.from_regex (phase 3c)
# ---------------------------------------------------------------------

def from_regex_meme_langage(texte, alphabet=("a", "b"), longueur_max=6):
    nfa = ExtendedNFA.from_regex(texte, input_symbols=set(alphabet))
    return all(
        nfa.accepts_input(mot) == accepte(texte, mot)
        for mot in tous_les_mots(alphabet, longueur_max)
    )


def test_from_regex_meme_langage_que_re():
    for texte in ["a", "ab", "a|b", "a*", "(a|b)*a", "a*b?", "(ab)+",
                  "a|()", "()", "(a|b)*abb", ".a", "a.b", "((a|b)*)*",
                  "(a*|b)*", "a+b+", "(a|b)?a"]:
        assert from_regex_meme_langage(texte), texte


def test_from_regex_langage_vide():
    nfa = ExtendedNFA.from_regex("∅", input_symbols={'a', 'b'})
    for mot in tous_les_mots(('a', 'b'), 4):
        assert not nfa.accepts_input(mot)
    union = ExtendedNFA.from_regex("a|∅", input_symbols={'a', 'b'})
    assert union.accepts_input("a")
    assert not union.accepts_input("")


def test_from_regex_construit_un_extendednfa():
    nfa = ExtendedNFA.from_regex("a|b", input_symbols={'a', 'b'})
    assert isinstance(nfa, ExtendedNFA)
    assert len(nfa.final_states) == 1


def test_from_regex_alphabet_deduit_de_lexpression():
    nfa = ExtendedNFA.from_regex("ab|c")
    assert nfa.input_symbols == {'a', 'b', 'c'}
    assert nfa.accepts_input("c")


def test_thompson_nombre_detats():
    # Thompson : 2 états par lettre ou mot vide, 2 de plus par union ou
    # étoile, les concaténations n'en ajoutent pas.
    def taille(texte):
        return len(ExtendedNFA.from_regex(
            texte, input_symbols={'a', 'b'}).states)
    assert taille("a") == 2
    assert taille("()") == 2
    assert taille("ab") == 4
    assert taille("a|b") == 6
    assert taille("a*") == 4


def test_from_regex_erreurs():
    for texte in ["(a", "a)", "*a", "a&b", "a{2}", "c"]:
        with pytest.raises(ValueError):
            ExtendedNFA.from_regex(texte, input_symbols={'a', 'b'})
    with pytest.raises(ValueError):
        ExtendedNFA.from_regex(".a")


# ---------------------------------------------------------------------
# Aller-retour : automate -> expression -> automate
# ---------------------------------------------------------------------

def test_aller_retour_automate_regex_automate(
    dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, dfa_mod3, dfa_vide,
    dfa_mot_vide_seul, nfa_fig_7_1_a, nfa_epsilon,
):
    for automate in (dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, dfa_mod3,
                     dfa_vide, dfa_mot_vide_seul, nfa_fig_7_1_a, nfa_epsilon):
        retour = ExtendedNFA.from_regex(
            automate.to_regex_optimum(), input_symbols=automate.input_symbols
        )
        for mot in tous_les_mots(automate.input_symbols, 6):
            assert automate.accepts_input(mot) == retour.accepts_input(mot), mot
