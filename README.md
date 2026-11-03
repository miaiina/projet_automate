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
├── regex/ # squelette, phase 7
└── tm/    # squelette, phase 7

tests/
├── conftest.py                  # fixtures (automates du poly d'exercices)
├── test_dfa_algorithms.py       # tests de plomberie (phase 1)
├── test_mixins_analyse.py       # phase 2
├── test_regex.py                # phase 3
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
- [ ] Phase 3 — mixin conversions (to_dfa, to_regex, epsilon-transitions)
- [ ] Phase 4 — opérations et relations (produit, union, équivalence...)
- [ ] Phase 5 — mixin grammaire
- [ ] Phase 6 — mixin visualisation (dot, svg, tikz)
- [ ] Phase 7 — squelettes pda/regex/tm (en attente de précisions)
