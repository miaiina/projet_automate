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
│       ├── conversions.py     # to_dfa, to_regex, epsilon-transitions...
│       ├── grammaire.py       # automate <-> grammaire régulière
│       └── visualisation.py   # dot, svg, tikz...
├── pda/   # squelette, phase 7 (algorithmes non précisés)
├── regex/ # regex.py : arbre d'expressions, analyseur, Thompson (phases 3b, 3c) ; mixins/ vide, phase 7
└── tm/    # squelette, phase 7

tests/
├── conftest.py                  # fixtures (automates du poly d'exercices)
├── test_dfa_algorithms.py       # tests de plomberie (phase 1)
├── test_mixins_analyse.py       # phase 2
├── test_mixins_conversions.py   # phases 3a, 3c (reverse, Brzozowski)
├── test_regex.py                # phases 3b, 3c (to_regex, Arden, analyseur, Thompson)
├── test_relations.py            # phase 4
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
- [ ] Phase 4 — opérations et relations (produit, union, équivalence...)
- [ ] Phase 5 — mixin grammaire
- [ ] Phase 6 — mixin visualisation (dot, svg, tikz)
- [ ] Phase 7 — squelettes pda/regex/tm (en attente de précisions)
