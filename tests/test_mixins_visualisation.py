# -*- coding: utf-8 -*-
"""
Tests de la visualisation (phase 6) : DOT, rendus Graphviz, TikZ/LaTeX,
table de transitions, trace d'exécution, animation HTML.

- Les parties « texte pur » (dot, tikz, latex, table, trace) sont toujours
  testées ; `dot()` est comparé aux lignes exactes de la documentation.
- Les rendus qui appellent le binaire Graphviz (`svg`, `png`, `pdf`,
  `animate`...) sont ignorés (`skipif`) si `dot` n'est pas installé.
"""
import shutil

import pytest

from automata_extensions.fa import ExtendedDFA
from automata_extensions.fa.mixins.visualisation import (
    _id_dot, _trouver_graphviz,
)

requires_dot = pytest.mark.skipif(
    shutil.which("dot") is None,
    reason="le binaire Graphviz 'dot' n'est pas installé",
)


# ---------------------------------------------------------------------
# dot()
# ---------------------------------------------------------------------

def test_dot_est_identique_a_la_documentation(dfa_mod3):
    attendu = [
        'digraph {',
        '\trankdir=LR',
        '\t__start__ [shape=point style=invis]',
        '\t__start__ -> s0',
        '\ts0 [label=0 shape=doublecircle]',
        '\ts1 [label=1 shape=circle]',
        '\ts2 [label=2 shape=circle]',
        '\ts0 -> s0 [label=b]',
        '\ts0 -> s1 [label=a]',
        '\ts1 -> s1 [label=b]',
        '\ts1 -> s2 [label=a]',
        '\ts2 -> s0 [label=a]',
        '\ts2 -> s2 [label=b]',
        '}',
    ]
    assert dfa_mod3.dot().splitlines() == attendu


def test_dot_nfa_avec_epsilon_transition(nfa_epsilon):
    attendu = [
        'digraph {',
        '\trankdir=LR',
        '\t__start__ [shape=point style=invis]',
        '\t__start__ -> s0',
        '\ts0 [label=p shape=circle]',
        '\ts1 [label=q shape=doublecircle]',
        '\ts2 [label=r shape=doublecircle]',
        '\ts0 -> s0 [label=a]',
        '\ts0 -> s1 [label=a]',
        '\ts0 -> s2 [label="ε"]',
        '\ts1 -> s1 [label=b]',
        '\ts2 -> s2 [label=a]',
        '}',
    ]
    assert nfa_epsilon.dot().splitlines() == attendu


def test_dot_fusionne_les_symboles_entre_deux_memes_etats(dfa_fig_3_1_a):
    lignes = dfa_fig_3_1_a.dot().splitlines()
    assert '\ts2 -> s2 [label="a,b"]' in lignes      # boucle sur l'état 3
    assert '\ts0 -> s1 [label=a]' in lignes
    assert '\ts0 -> s2 [label=b]' in lignes


def test_dot_met_les_noms_non_simples_entre_guillemets(nfa_epsilon):
    # Après déterminisation, les états sont des ensembles : "{p,r}".
    dfa = nfa_epsilon.determinize()
    assert 'label="{p,r}"' in dfa.dot()


def test_id_dot():
    assert _id_dot("ab") == "ab"
    assert _id_dot("q0") == "q0"
    assert _id_dot("12") == "12"
    assert _id_dot("q 0") == '"q 0"'
    assert _id_dot("a,b") == '"a,b"'
    assert _id_dot("ε") == '"ε"'
    assert _id_dot('a"b') == '"a\\"b"'


def test_dot_highlight_colorie_le_parcours(dfa_mod3):
    lignes = dfa_mod3.dot(highlight="aab").splitlines()
    # parcours : 0 -a-> 1 -a-> 2 -b-> 2
    assert '\ts0 -> s1 [label=a color=red penwidth=2]' in lignes
    assert '\ts1 -> s2 [label=a color=red penwidth=2]' in lignes
    assert '\ts2 -> s2 [label=b color=red penwidth=2]' in lignes
    # transitions non suivies : inchangées
    assert '\ts0 -> s0 [label=b]' in lignes
    assert '\ts2 -> s0 [label=a]' in lignes
    # les trois états visités sont entourés en rouge
    assert sum('shape=' in l and 'color=red' in l for l in lignes) == 3


def test_dot_highlight_mot_vide_ne_colorie_que_letat_initial(dfa_mod3):
    lignes = dfa_mod3.dot(highlight="").splitlines()
    assert '\ts0 [label=0 shape=doublecircle color=red]' in lignes
    assert sum('color=red' in l for l in lignes) == 1


def test_dot_highlight_refuse_un_nfa(nfa_epsilon):
    with pytest.raises(NotImplementedError):
        nfa_epsilon.dot(highlight="a")


# ---------------------------------------------------------------------
# execution_trace
# ---------------------------------------------------------------------

def test_execution_trace_exemple_de_la_doc(dfa_mod3):
    assert dfa_mod3.execution_trace("aab") == [
        ('0', 'a', '1'), ('1', 'a', '2'), ('2', 'b', '2'),
    ]
    assert dfa_mod3.execution_trace("") == []


def test_execution_trace_sarrete_quand_une_transition_manque(dfa_partiel):
    # dfa_partiel : un seul état '0', transition 'a' seulement.
    assert dfa_partiel.execution_trace("aab") == [
        ('0', 'a', '0'), ('0', 'a', '0'),
    ]


def test_execution_trace_refuse_un_nfa(nfa_fig_7_1_a):
    with pytest.raises(NotImplementedError):
        nfa_fig_7_1_a.execution_trace("a")


# ---------------------------------------------------------------------
# tikz() et latex()
# ---------------------------------------------------------------------

def test_tikz_structure(dfa_mod3):
    code = dfa_mod3.tikz()
    assert code.startswith("\\begin{tikzpicture}")
    assert code.rstrip().endswith("\\end{tikzpicture}")
    assert code.count("\\node[state") == 3
    assert code.count("initial text=") == 1
    assert code.count("accepting") == 1
    assert code.count("loop above") == 3          # une boucle 'b' par état
    # Cycle à sens unique 0->1->2->0 : aucune arête n'a de retour (pas de
    # "bend left"), mais 2->0 passerait sur l'état 1 (alignés) : elle est
    # courbée par en dessous.
    assert "bend left" not in code
    assert code.count("bend right=45") == 1


def test_tikz_courbe_les_aretes_dans_les_deux_sens():
    aller_retour = ExtendedDFA(
        states={'0', '1'},
        input_symbols={'a'},
        transitions={'0': {'a': '1'}, '1': {'a': '0'}},
        initial_state='0',
        final_states={'1'},
    )
    assert aller_retour.tikz().count("bend left") == 2


def test_tikz_evite_de_traverser_un_etat(nfa_epsilon):
    # p -ε-> r est sur la même ligne que q : on la courbe par en dessous.
    code = nfa_epsilon.tikz()
    assert code.count("bend right=45") == 1
    assert "\\varepsilon" in code


def test_tikz_accolades_equilibrees(
    dfa_mod3, dfa_fig_6_1_a, nfa_epsilon, nfa_fig_7_1_a,
):
    for automate in (dfa_mod3, dfa_fig_6_1_a, nfa_epsilon, nfa_fig_7_1_a,
                     nfa_epsilon.determinize()):
        code = automate.tikz().replace("\\{", "").replace("\\}", "")
        assert code.count("{") == code.count("}")


def test_tikz_echappe_les_caracteres_speciaux():
    automate = ExtendedDFA(
        states={'q_1', 'q#2'},
        input_symbols={'a'},
        transitions={'q_1': {'a': 'q#2'}, 'q#2': {'a': 'q_1'}},
        initial_state='q_1',
        final_states={'q#2'},
    )
    code = automate.tikz()
    assert "q\\_1" in code and "q\\#2" in code


def test_latex_est_un_document_complet(dfa_mod3):
    document = dfa_mod3.latex()
    assert document.startswith("\\documentclass")
    assert "\\usetikzlibrary{automata}" in document
    assert dfa_mod3.tikz() in document
    assert document.endswith("\\end{document}\n")


# ---------------------------------------------------------------------
# transition_table
# ---------------------------------------------------------------------

def test_transition_table_dfa(dfa_mod3):
    assert dfa_mod3.transition_table() == (
        "     | a | b\n"
        "-----+---+--\n"
        "->*0 | 1 | 0\n"
        "   1 | 2 | 1\n"
        "   2 | 0 | 2"
    )


def test_transition_table_nfa_avec_epsilon(nfa_epsilon):
    assert nfa_epsilon.transition_table() == (
        "    | a     | b | ε\n"
        "----+-------+---+--\n"
        "->p | {p,q} | - | r\n"
        " *q | -     | q | -\n"
        " *r | r     | - | -"
    )


def test_transition_table_dfa_partiel(dfa_partiel):
    assert dfa_partiel.transition_table() == (
        "     | a | b\n"
        "-----+---+--\n"
        "->*0 | 0 | -"
    )


# ---------------------------------------------------------------------
# save (formats qui n'ont pas besoin de Graphviz)
# ---------------------------------------------------------------------

def test_save_dot_tex_tikz_sans_graphviz(dfa_mod3, tmp_path):
    chemin = dfa_mod3.save(tmp_path / "a.dot")
    assert chemin.read_text(encoding="utf-8") == dfa_mod3.dot()
    dfa_mod3.save(tmp_path / "a.tex")
    assert (tmp_path / "a.tex").read_text(encoding="utf-8") == dfa_mod3.latex()
    dfa_mod3.save(tmp_path / "a.tikz")
    assert (tmp_path / "a.tikz").read_text(encoding="utf-8") == dfa_mod3.tikz()
    dfa_mod3.save(tmp_path / "parcours.dot", highlight="aab")
    assert "color=red" in (tmp_path / "parcours.dot").read_text(
        encoding="utf-8")


def test_graphviz_introuvable_leve_runtimeerror():
    with pytest.raises(RuntimeError):
        _trouver_graphviz("programme-graphviz-qui-nexiste-pas-xyz")


# ---------------------------------------------------------------------
# Rendus (binaire Graphviz requis)
# ---------------------------------------------------------------------

@requires_dot
def test_svg_png_pdf(dfa_mod3):
    svg = dfa_mod3.svg()
    assert isinstance(svg, str) and "<svg" in svg
    assert "<title>s0</title>" in svg
    assert dfa_mod3.png().startswith(b"\x89PNG\r\n\x1a\n")
    assert dfa_mod3.pdf().startswith(b"%PDF")


@requires_dot
def test_svg_nfa_avec_epsilon(nfa_epsilon):
    assert "<svg" in nfa_epsilon.svg()


@requires_dot
def test_svg_highlight_contient_du_rouge(dfa_mod3):
    assert "red" in dfa_mod3.svg(highlight="aab")
    assert "red" not in dfa_mod3.svg()


@requires_dot
def test_save_rendus(dfa_mod3, tmp_path):
    for nom, signature in (("a.png", b"\x89PNG"), ("a.pdf", b"%PDF"),
                           ("a.svg", b"<?xml")):
        chemin = dfa_mod3.save(tmp_path / nom)
        contenu = chemin.read_bytes()
        assert contenu.startswith(signature) or signature in contenu[:200]


@requires_dot
def test_repr_svg_pour_les_notebooks(dfa_mod3):
    assert "<svg" in dfa_mod3._repr_svg_()


# ---------------------------------------------------------------------
# animate (binaire Graphviz requis)
# ---------------------------------------------------------------------

@requires_dot
def test_animate_une_image_par_etape(dfa_mod3):
    page = dfa_mod3.animate("aab")
    assert page.count("<svg") == 4                 # départ + 3 lettres
    assert "Mot rejeté" in page                    # l'état 2 n'est pas final
    assert "Lecture de « b » : état 2" in page
    assert "<script>" in page and "</script>" in page
    assert "Précédent" in page and "Suivant" in page and "Lecture" in page


@requires_dot
def test_animate_mot_accepte_et_mot_vide(dfa_mod3):
    assert "Mot accepté" in dfa_mod3.animate("aaa")
    vide = dfa_mod3.animate("")
    assert vide.count("<svg") == 1
    assert "Mot accepté" in vide


@requires_dot
def test_animate_mot_bloque_sur_un_dfa_partiel(dfa_partiel):
    page = dfa_partiel.animate("ab")
    assert page.count("<svg") == 2
    assert "aucune transition pour" in page


@requires_dot
def test_animate_identifiants_distincts_et_script_non_casse(dfa_mod3):
    a, b = dfa_mod3.animate("a"), dfa_mod3.animate("a")
    assert a != b                                  # identifiants différents
    assert a.count("</script>") == 1

    piege = ExtendedDFA(
        states={'</script>', 'x'},
        input_symbols={'a'},
        transitions={'</script>': {'a': 'x'}, 'x': {'a': 'x'}},
        initial_state='</script>',
        final_states={'x'},
    )
    assert piege.animate("a").count("</script>") == 1


def test_animate_refuse_un_nfa(nfa_epsilon):
    with pytest.raises(NotImplementedError):
        nfa_epsilon.animate("a")
