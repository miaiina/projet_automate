# -*- coding: utf-8 -*-
"""
Tests des quotients, des résiduels, du monoïde syntaxique, des morphismes,
de la projection et de la clôture par préfixe.

Arbitre indépendant : énumération de tous les mots jusqu'à une certaine
longueur, avec des définitions directes (par exemple « le mot u est dans le
quotient si et seulement si mot·u est dans le langage »), sans construire
d'automate pour vérifier un automate.
"""
from itertools import product

import pytest

from automata.fa.nfa import NFA

from automata_extensions.fa import ExtendedDFA, ExtendedNFA


def tous_les_mots(alphabet, longueur_max):
    for longueur in range(longueur_max + 1):
        for lettres in product(sorted(alphabet), repeat=longueur):
            yield "".join(lettres)


def langage(automate, longueur_max=6, alphabet=("a", "b")):
    return {m for m in tous_les_mots(alphabet, longueur_max)
            if automate.accepts_input(m)}


MOTS = ["", "a", "b", "ab", "ba", "aab"]


# ---------------------------------------------------------------------
# Quotients par un mot
# ---------------------------------------------------------------------

def test_quotients_par_un_mot_contre_la_definition(
    dfa_mod3, dfa_fig_6_1_a, dfa_table_6_1_a, nfa_fig_7_1_a, nfa_epsilon,
):
    for automate in (dfa_mod3, dfa_fig_6_1_a, dfa_table_6_1_a,
                     nfa_fig_7_1_a, nfa_epsilon):
        for u in MOTS:
            gauche = automate.left_quotient_word(u)
            droite = automate.right_quotient_word(u)
            for w in tous_les_mots(("a", "b"), 5):
                assert gauche.accepts_input(w) == automate.accepts_input(u + w)
                assert droite.accepts_input(w) == automate.accepts_input(w + u)


def test_quotients_exemple_de_la_doc(dfa_mod3):
    assert dfa_mod3.left_quotient_word("a").accepts_input("aa")
    assert dfa_mod3.right_quotient_word("a").accepts_input("aa")
    assert not dfa_mod3.left_quotient_word("a").accepts_input("a")


def test_quotient_a_gauche_dun_mot_bloque_est_le_langage_vide(dfa_partiel):
    # dfa_partiel : a* sur {a,b}, sans transition 'b'.
    assert dfa_partiel.left_quotient_word("b").is_empty()
    assert not dfa_partiel.left_quotient_word("aa").is_empty()
    assert dfa_partiel.right_quotient_word("b").is_empty()


def test_quotient_par_le_mot_vide_ne_change_rien(dfa_mod3, nfa_epsilon):
    assert dfa_mod3.is_equivalent(dfa_mod3.left_quotient_word(""))
    assert dfa_mod3.is_equivalent(dfa_mod3.right_quotient_word(""))
    assert nfa_epsilon.is_equivalent(nfa_epsilon.left_quotient_word(""))


# ---------------------------------------------------------------------
# quotient_by (fusion d'états)
# ---------------------------------------------------------------------

def test_quotient_by_exemple_de_la_doc(dfa_mod3):
    quotient = dfa_mod3.quotient_by({"0": "0", "1": "0", "2": "2"})
    assert sorted(quotient.states) == ['0', '2']
    assert isinstance(quotient, NFA)               # la fusion peut perdre le déterminisme
    assert not quotient.is_deterministic()


def test_quotient_by_reconnait_au_moins_les_memes_mots(
    dfa_mod3, dfa_fig_6_1_a, nfa_epsilon,
):
    fusions = [
        (dfa_mod3, {"0": "0", "1": "0", "2": "2"}),
        (dfa_fig_6_1_a, {"1": "1", "2": "1", "3": "3", "4": "3"}),
        (nfa_epsilon, {"p": "p", "q": "p", "r": "r"}),
    ]
    for automate, application in fusions:
        quotient = automate.quotient_by(application)
        for mot in langage(automate):
            assert quotient.accepts_input(mot), mot


def test_quotient_by_application_identique(dfa_mod3, nfa_epsilon):
    for automate in (dfa_mod3, nfa_epsilon):
        identite = {e: e for e in automate.states}
        assert automate.is_equivalent(automate.quotient_by(identite))


def test_quotient_by_tout_fusionner_donne_tous_les_mots(dfa_mod3):
    # Un seul état final : tous les mots sur {a,b} sont acceptés.
    tout = dfa_mod3.quotient_by({"0": "x", "1": "x", "2": "x"})
    assert tout.is_universal()


def test_quotient_by_exige_une_image_pour_chaque_etat(dfa_mod3):
    with pytest.raises(ValueError):
        dfa_mod3.quotient_by({"0": "0", "1": "0"})


# ---------------------------------------------------------------------
# residual_automaton
# ---------------------------------------------------------------------

def nombre_de_residuels_par_enumeration(automate, longueur_u=5, longueur_w=4,
                                        alphabet=("a", "b")):
    """Nombre de quotients à gauche distincts, par comparaison des
    ensembles {w : u·w dans L} pour tous les mots u courts."""
    signatures = set()
    for u in tous_les_mots(alphabet, longueur_u):
        signatures.add(frozenset(
            w for w in tous_les_mots(alphabet, longueur_w)
            if automate.accepts_input(u + w)
        ))
    return len(signatures)


def test_residual_automaton_exemple_de_la_doc(dfa_mod3):
    residuel = dfa_mod3.residual_automaton()
    assert sorted(map(str, residuel.states)) == ['q0', 'q1', 'q2']
    assert residuel.initial_state == 'q0'


def test_residual_automaton_meme_langage_et_bon_nombre_detats(
    dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, nfa_fig_7_1_a,
    nfa_epsilon,
):
    for automate in (dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                     nfa_fig_7_1_a, nfa_epsilon):
        residuel = automate.residual_automaton()
        assert residuel.is_complete()
        assert automate.is_equivalent(residuel)
        assert len(residuel.states) == nombre_de_residuels_par_enumeration(
            automate
        )


def test_residual_automaton_ignore_les_etats_inaccessibles():
    avec_inaccessible = ExtendedDFA(
        states={'0', '1', 'x'},
        input_symbols={'a'},
        transitions={'0': {'a': '1'}, '1': {'a': '1'}, 'x': {'a': 'x'}},
        initial_state='0',
        final_states={'1'},
    )
    assert len(avec_inaccessible.residual_automaton().states) == 2


# ---------------------------------------------------------------------
# syntactic_monoid
# ---------------------------------------------------------------------

def nombre_de_classes_syntaxiques(automate, longueur_u=9, longueur_xy=3,
                                  alphabet=("a", "b")):
    """Nombre de classes de la congruence syntaxique : u ~ v si et
    seulement si x·u·y et x·v·y sont toujours acceptés ensemble. On
    compare les mots u par leur ensemble de contextes (x, y).

    Les bornes comptent : l'énumération ne peut que SOUS-ESTIMER le nombre
    de classes (deux mots qui ont des signatures différentes sont bien
    différents), et il faut des mots u assez longs pour atteindre tous les
    éléments du monoïde (pour dfa_table_6_1_a, le plus court représentant
    d'un élément a 8 lettres ; avec des mots de longueur <= 5 on ne trouve
    que 18 classes sur 24). Les contextes, eux, peuvent rester courts."""
    contextes = list(tous_les_mots(alphabet, longueur_xy))
    signatures = set()
    for u in tous_les_mots(alphabet, longueur_u):
        signatures.add(frozenset(
            (x, y) for x in contextes for y in contextes
            if automate.accepts_input(x + u + y)
        ))
    return len(signatures)


def test_syntactic_monoid_exemple_de_la_doc(dfa_mod3):
    monoide = dfa_mod3.syntactic_monoid()
    assert len(monoide) == 3
    assert set(monoide) == {"", "a", "aa"}              # plus courts mots
    assert monoide[""] == {'0': '0', '1': '1', '2': '2'}  # identité
    assert monoide["a"] == {'0': '1', '1': '2', '2': '0'}
    assert monoide["aa"] == {'0': '2', '1': '0', '2': '1'}


def test_syntactic_monoid_est_ferme_par_produit(dfa_mod3, dfa_fig_6_1_a,
                                                nfa_fig_7_1_a):
    for automate in (dfa_mod3, dfa_fig_6_1_a, nfa_fig_7_1_a):
        monoide = automate.syntactic_monoid()
        actions = list(monoide.values())
        for x in actions:
            for y in actions:
                produit = {q: y[x[q]] for q in x}      # lire x puis y
                assert produit in actions


def test_syntactic_monoid_contre_la_congruence_syntaxique(
    dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, nfa_fig_7_1_a,
    nfa_epsilon,
):
    for automate in (dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                     nfa_fig_7_1_a, nfa_epsilon):
        assert len(automate.syntactic_monoid()) == (
            nombre_de_classes_syntaxiques(automate)
        )


# ---------------------------------------------------------------------
# is_morphism_to
# ---------------------------------------------------------------------

def test_is_morphism_to_exemple_de_la_doc(dfa_mod3):
    assert dfa_mod3.is_morphism_to(dfa_mod3, {"0": "0", "1": "1", "2": "2"})


def test_is_morphism_vers_lautomate_minimal(dfa_fig_6_1_a):
    minimal = dfa_fig_6_1_a.minimize()
    # Les états 3 et 4 (équivalents) sont envoyés sur le même état.
    assert dfa_fig_6_1_a.is_morphism_to(
        minimal, {"1": "1", "2": "2", "3": "3", "4": "3"})


def test_is_morphism_to_refuse_les_applications_invalides(
    dfa_mod3, dfa_fig_6_1_a,
):
    minimal = dfa_fig_6_1_a.minimize()
    # 4 envoyé sur 2 : un état final ne peut pas aller sur un non final.
    assert not dfa_fig_6_1_a.is_morphism_to(
        minimal, {"1": "1", "2": "2", "3": "3", "4": "2"})
    # l'état initial n'a pas pour image l'état initial
    assert not dfa_mod3.is_morphism_to(
        dfa_mod3, {"0": "1", "1": "2", "2": "0"})
    # une transition n'a pas d'image (0 -a-> 1 devient 0 -a-> 0, absente)
    assert not dfa_mod3.is_morphism_to(
        dfa_mod3, {"0": "0", "1": "0", "2": "2"})
    # état sans image / image hors de l'automate d'arrivée
    assert not dfa_mod3.is_morphism_to(dfa_mod3, {"0": "0", "1": "1"})
    assert not dfa_mod3.is_morphism_to(
        dfa_mod3, {"0": "0", "1": "1", "2": "inconnu"})


def test_is_morphism_to_verifie_les_etats_finaux_a_eux_seuls(dfa_mod3, dfa_vide):
    # dfa_vide : un seul état '0', non final, qui boucle sur a et b. En
    # envoyant tout sur '0', l'état initial est respecté et chaque
    # transition a une image (une boucle) : SEULE la finalité de l'état
    # '0' de dfa_mod3 (final) n'est pas respectée.
    assert not dfa_mod3.is_morphism_to(dfa_vide, {"0": "0", "1": "0", "2": "0"})
    # Même chose dans l'autre sens : un seul état final qui boucle ; les
    # états 1 et 2 (non finaux) auraient une image finale.
    tout = ExtendedDFA(
        states={'0'}, input_symbols={'a', 'b'},
        transitions={'0': {'a': '0', 'b': '0'}},
        initial_state='0', final_states={'0'},
    )
    assert not dfa_mod3.is_morphism_to(tout, {"0": "0", "1": "0", "2": "0"})


def test_is_morphism_to_conserve_le_langage(dfa_fig_6_1_a):
    minimal = dfa_fig_6_1_a.minimize()
    assert dfa_fig_6_1_a.is_morphism_to(
        minimal, {"1": "1", "2": "2", "3": "3", "4": "3"})
    assert dfa_fig_6_1_a.is_equivalent(minimal)


# ---------------------------------------------------------------------
# project
# ---------------------------------------------------------------------

def test_project_exemple_de_la_doc(dfa_mod3):
    image = dfa_mod3.project({"a": "x", "b": None})
    assert isinstance(image, ExtendedNFA)
    assert image.input_symbols == {"x"}
    assert image.accepts_input("xxx")
    # Image de {w : nombre de a multiple de 3} : x^n avec n multiple de 3.
    for n in range(10):
        assert image.accepts_input("x" * n) == (n % 3 == 0)


def test_project_renommage_bijectif(dfa_mod3, dfa_fig_6_1_a):
    renommage = {"a": "c", "b": "d"}
    for automate in (dfa_mod3, dfa_fig_6_1_a):
        image = automate.project(renommage)
        assert image.input_symbols == {"c", "d"}
        for mot in tous_les_mots(("a", "b"), 6):
            traduit = mot.translate(str.maketrans("ab", "cd"))
            assert image.accepts_input(traduit) == automate.accepts_input(mot)


def test_project_garde_les_lettres_absentes_de_lapplication(dfa_mod3):
    image = dfa_mod3.project({"a": "c"})
    assert image.input_symbols == {"b", "c"}
    assert image.accepts_input("cbcbc") == dfa_mod3.accepts_input("ababa")


def test_project_refuse_une_image_invalide(dfa_mod3):
    for mauvaise in ("ab", "", 3):
        with pytest.raises(ValueError):
            dfa_mod3.project({"a": mauvaise})


def test_project_nfa_avec_epsilon(nfa_epsilon):
    # effacer b : a*b+ devient a+, le langage a* | a+b+ devient a*.
    image = nfa_epsilon.project({"b": None})
    for n in range(6):
        assert image.accepts_input("a" * n)


# ---------------------------------------------------------------------
# is_prefix_closed et prefix_closed_sublanguage
# ---------------------------------------------------------------------

def est_clos_par_prefixe(mots):
    return all(m[:i] in mots for m in mots for i in range(len(m)))


def plus_grand_sous_langage_clos(mots):
    return {m for m in mots if all(m[:i] in mots for i in range(len(m) + 1))}


def prefixes_de_ab():
    """DFA de {"", "a", "ab"} : clos par préfixe."""
    return ExtendedDFA(
        states={'0', '1', '2', 'p'},
        input_symbols={'a', 'b'},
        transitions={
            '0': {'a': '1', 'b': 'p'},
            '1': {'a': 'p', 'b': '2'},
            '2': {'a': 'p', 'b': 'p'},
            'p': {'a': 'p', 'b': 'p'},
        },
        initial_state='0',
        final_states={'0', '1', '2'},
    )


def test_is_prefix_closed_exemple_de_la_doc(dfa_mod3):
    assert not dfa_mod3.is_prefix_closed()
    assert dfa_mod3.prefix_closed_sublanguage().accepts_input("")


def test_is_prefix_closed_contre_la_definition(
    dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, nfa_fig_7_1_a,
    nfa_epsilon, dfa_vide, dfa_mot_vide_seul, dfa_unaire,
):
    automates = [dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                 nfa_fig_7_1_a, nfa_epsilon, dfa_vide, dfa_mot_vide_seul,
                 prefixes_de_ab()]
    for automate in automates:
        assert automate.is_prefix_closed() == est_clos_par_prefixe(
            langage(automate))
    # a* sur l'alphabet {a} seulement
    assert dfa_unaire.is_prefix_closed()
    assert prefixes_de_ab().is_prefix_closed()
    assert dfa_vide.is_prefix_closed()                  # langage vide
    assert dfa_mot_vide_seul.is_prefix_closed()         # {""}


def test_prefix_closed_sublanguage_contre_la_definition(
    dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a, nfa_fig_7_1_a,
    nfa_epsilon, dfa_vide, dfa_mot_vide_seul,
):
    for automate in (dfa_mod3, dfa_fig_3_1_a, dfa_fig_6_1_a, dfa_table_6_1_a,
                     nfa_fig_7_1_a, nfa_epsilon, dfa_vide, dfa_mot_vide_seul,
                     prefixes_de_ab()):
        sous = automate.prefix_closed_sublanguage()
        assert langage(sous) == plus_grand_sous_langage_clos(langage(automate))
        assert sous.is_prefix_closed()


def test_prefix_closed_sublanguage_dun_langage_deja_clos():
    a = prefixes_de_ab()
    assert a.is_equivalent(a.prefix_closed_sublanguage())


def test_prefix_closed_sublanguage_sans_mot_vide_est_vide(dfa_fig_3_1_a):
    # fig 3.1.a : a+ ne contient pas le mot vide, donc aucun préfixe-clos non vide.
    assert dfa_fig_3_1_a.prefix_closed_sublanguage().is_empty()


# ---------------------------------------------------------------------
# is_universal
# ---------------------------------------------------------------------

def test_is_universal(dfa_mod3, dfa_unaire, dfa_vide, nfa_epsilon):
    assert not dfa_mod3.is_universal()                   # exemple de la doc
    assert dfa_unaire.is_universal()                     # a* sur {a}
    assert not dfa_vide.is_universal()
    assert not nfa_epsilon.is_universal()
    tout = ExtendedDFA(
        states={'0'}, input_symbols={'a', 'b'},
        transitions={'0': {'a': '0', 'b': '0'}},
        initial_state='0', final_states={'0'},
    )
    assert tout.is_universal()
