# automata-etendu

Extension de [`automata-lib`](https://pypi.org/project/automata-lib/) 9.2.0
(non modifiée) pour se rapprocher des fonctionnalités d'
[AUDE](https://aude.imag.fr/), via héritage et mixins.

## Installation

Utilisez l'un des deux scripts fournis (conda ou venv classique), puis
ajoutez pytest dans l'environnement activé :

```bash
conda activate automate-env-clean   # ou l'équivalent venv
pip install -r requirements.txt
```

Vérification :

```bash
python -c "from automata.fa.dfa import DFA; print('ok')"
python -c "import pygraphviz; print('ok')"
dot -V
pytest --version
```

## Usage

```python
from automata_extensions.fa import ExtendedDFA

a = ExtendedDFA(
    states={'1', '2', '3'},
    input_symbols={'a', 'b'},
    transitions={
        '1': {'a': '2', 'b': '3'},
        '2': {'a': '2', 'b': '3'},
        '3': {'a': '3', 'b': '3'},
    },
    initial_state='1',
    final_states={'2'},
)
a.accessible_states()   # une fois le mixin analyse implémenté (phase 2)
```

## Visualisation (phase 6)

```python
a = ExtendedDFA(...)            # ou ExtendedNFA
a                               # dans un notebook : l'automate est dessiné tout seul
a.dot()                         # source DOT (texte pur)
a.svg(); a.png(); a.pdf()       # rendus Graphviz (binaire `dot` requis)
a.save("a.png")                 # .png .svg .pdf .dot .tex .tikz selon l'extension
a.svg(highlight="aab")          # parcours du mot en rouge (DFA)
a.tikz(); a.latex()             # TikZ / document LaTeX (se compile avec pdflatex)
a.transition_table()            # table de transitions en texte
a.execution_trace("aab")        # [('0','a','1'), ('1','a','2'), ('2','b','2')]

from IPython.display import HTML
HTML(a.animate("aab"))          # animation pas à pas (DFA)
```

Le rendu appelle directement le binaire `dot` (aucun paquet Python en plus,
pas de conflit pygraphviz/manim). `a.show_diagram()` d'automata-lib reste
disponible.

## Compatibilité avec les notebooks du cours

Les notebooks `Cours06`, `TD3`, `TD4` et `TD5` importent
`from automata_extensions.fa.dfa import ExtendedDFA as DFA` (et idem pour
`nfa`) : ces modules existent. Toutes les méthodes d'extension qu'ils
appellent sont implémentées, et leurs sorties enregistrées servent de
tests :

- `pair_table_str(show_round=...)` et `print_pair_table(show_round=...)`
  reproduisent exactement les tables de `Cours06` ;
- `to_regex()` reproduit exactement le texte des TD (toute union entre
  parenthèses, parenthèses doublées sous une étoile) ;
- `to_regex_optimum()` donne une expression de même langage que celle du
  cours, mais pas forcément écrite de la même façon.

Pour rejouer un notebook de bout en bout avec votre environnement :

```bash
PYTHONPATH=~/projet_automate/automata-etendu \
  jupyter nbconvert --to notebook --execute ~/projet_automate/ressources/TD3.ipynb \
  --output-dir /tmp/essai_notebooks
```

## Structure

```
automata_extensions/
├── fa/
│   ├── fa.py        # ExtendedFA : interface commune (_successors, ...)
│   ├── dfa.py        # ExtendedDFA
│   ├── nfa.py        # ExtendedNFA
│   ├── gnfa.py       # ExtendedGNFA
│   └── mixins/
│       ├── analyse.py         # accessibilité, trim, minimisation...
│       ├── conversions.py     # to_dfa, to_regex, epsilon-transitions, reverse, Brzozowski...
│       ├── operations.py      # produit, intersection, union, différence, complément, concaténation, étoile
│       ├── relations.py       # vide/fini/universel, plus court mot, inclusion, équivalence, isomorphisme
│       ├── graphe.py          # parcours, cycles, composantes fortement connexes, sous-automate
│       ├── quotients.py       # quotients par un mot, résiduels, fusion d'états
│       ├── algebre.py         # monoïde syntaxique, morphismes, projection, préfixes
│       ├── grammaire.py       # to_grammar, derivation_tree
│       └── visualisation.py   # dot, svg/png/pdf, tikz/latex, table, trace, animation
├── grammar/ # grammar.py : Grammar, Rule, DerivationStep (phase 5)
├── pda/   # squelette, phase 7 (algorithmes non précisés)
├── regex/ # regex.py : arbre d'expressions, analyseur, Thompson (phases 3b, 3c) ; mixins/ vide, phase 7
└── tm/    # squelette, phase 7

tests/
├── conftest.py                  # fixtures (automates du poly d'exercices)
├── test_dfa_algorithms.py       # tests de plomberie (phase 1)
├── test_mixins_analyse.py       # phase 2
├── test_mixins_conversions.py   # phases 3a, 3c (reverse, Brzozowski)
├── test_regex.py                # phases 3b, 3c (to_regex, Arden, analyseur, Thompson)
├── test_relations.py            # phase 4 (opérations et relations)
├── test_grammaire.py            # phase 5 (grammaires, dérivations)
├── test_graphe.py               # phase 7a (graphe, cycles, composantes connexes)
├── test_quotients_algebre.py    # phase 7a (quotients, monoïde, morphismes, préfixes)
└── test_mixins_visualisation.py # phase 6
```

## Tests

```bash
pytest tests/ -v                       # toute la suite
pytest tests/test_mixins_analyse.py -v # un mixin en particulier
```

## État d'avancement

- [x] Phase 1 — squelette, `ExtendedFA`, `ExtendedDFA/NFA/GNFA`, `conftest.py`
- [x] Phase 2 — mixin analyse (accessibilité, trim, distinguabilité, minimisation)
- [x] Phase 3a — conversions : fermeture epsilon, remove_epsilon_transitions, determinize/to_dfa, complete
- [x] Phase 3b — automate -> regex : to_regex, to_regex_arden, to_regex_optimum, to_regex_arden_optimum (arbre d'expressions dans `regex/regex.py`)
- [x] Phase 3c — reverse, brzozowski_minimize, Thompson (`ExtendedNFA.from_regex`, analyseur dans `regex/regex.py`)
- [x] Phase 4 — opérations (product, intersection, union, difference, symmetric_difference, complement, concatenation, kleene_star) et relations (is_empty, is_finite, shortest_word, is_included_in, is_equivalent, is_disjoint_from, is_isomorphic_to, contre-exemples)
- [x] Phase 5 — grammaires régulières : `to_grammar`, `derivation_tree`, `ExtendedNFA.from_grammar` / `from_grammar_string` (paquet `automata_extensions/grammar/`)
- [x] Phase 6 — visualisation : `dot`, `svg`/`png`/`pdf`/`save` (Graphviz), `tikz`/`latex`, `transition_table`, `execution_trace`, `animate`, affichage automatique en notebook
- [x] Phase 7a — rattrapage de la doc : graphe (`is_accessible`, `reachable_states`, `bfs`, `dfs`, `has_cycle`, `strongly_connected_components`, `induced_subautomaton`, `copy`...), quotients (`left_quotient_word`, `right_quotient_word`, `residual_automaton`, `quotient_by`), algèbre (`syntactic_monoid`, `is_morphism_to`, `project`, `is_prefix_closed`, `prefix_closed_sublanguage`), `is_deterministic`, `is_universal`
- [ ] Phase 7b — squelettes pda/regex/tm (en attente de précisions)
