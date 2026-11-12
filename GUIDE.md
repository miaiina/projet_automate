# Guide d'utilisation

Ce guide montre chaque famille de méthodes avec un exemple. **Les résultats affichés sont ceux obtenus en exécutant les extraits** (le guide est généré, pas écrit à la main). Les extraits sont à exécuter dans l'ordre : chacun réutilise les automates des précédents.

## Prise en main

Un automate se construit comme avec `automata-lib` ; les classes `Extended...` ajoutent les méthodes de ce guide. Les notebooks du cours importent `ExtendedDFA` et `ExtendedNFA` sous les noms `DFA` et `NFA`.

```python
from automata_extensions.fa.dfa import ExtendedDFA as DFA
from automata_extensions.fa.nfa import ExtendedNFA as NFA

# Nombre de 'a' multiple de 3
d = DFA(
    states={"0", "1", "2"},
    input_symbols={"a", "b"},
    transitions={
        "0": {"a": "1", "b": "0"},
        "1": {"a": "2", "b": "1"},
        "2": {"a": "0", "b": "2"},
    },
    initial_state="0",
    final_states={"0"},
)
print(d.accepts_input("aaa"), d.accepts_input("ab"))
```

Résultat :

```text
True False
```

## Analyse d'un automate

Accessibilité, nettoyage, minimisation, table des paires du cours.

```python
print(d.accessible_states() == {"0", "1", "2"})
print(d.is_complete(), d.is_deterministic(), d.is_minimal())
m = d.minimize()
print(len(m.states))
```

Résultat :

```text
True
True True True
3
```

```python
# L'automate du notebook Cours06
c6 = DFA(
    states={"1", "2", "3", "4", "5", "6", "7", "8"},
    input_symbols={"a", "b"},
    transitions={
        "1": {"a": "2", "b": "6"}, "2": {"a": "7", "b": "3"},
        "3": {"a": "1", "b": "3"}, "4": {"a": "3", "b": "7"},
        "5": {"a": "8", "b": "6"}, "6": {"a": "3", "b": "7"},
        "7": {"a": "7", "b": "5"}, "8": {"a": "7", "b": "3"},
    },
    initial_state="1",
    final_states={"3"},
)
c6.print_pair_table()
print()
c6.print_pair_table(show_round=True)   # numéro de passage de chaque paire
```

Résultat :

```text
   1  2  3  4  5  6  7
2  X
3  X  X
4  X  X  X
5  .  X  X  X
6  X  X  X  .  X
7  X  X  X  X  X  X
8  X  .  X  X  X  X  X

   1  2  3  4  5  6  7
2  1
3  0  0
4  1  1  0
5  .  1  0  1
6  1  1  0  .  1
7  2  1  0  1  1  1
8  1  .  0  1  1  1  1
```

```python
print(sorted(map(sorted, c6.equivalence_classes())))
print(len(c6.minimize().states))
```

Résultat :

```text
[['1', '5'], ['2', '8'], ['3'], ['4', '6'], ['7']]
5
```

## Conversions

NFA avec epsilon-transitions, déterminisation, expressions régulières.

```python
# Une epsilon-transition s'écrit avec la clé "" (chaîne vide)
n = NFA(
    states={"p", "q", "r"},
    input_symbols={"a", "b"},
    transitions={
        "p": {"a": {"p", "q"}, "": {"r"}},
        "q": {"b": {"q"}},
        "r": {"a": {"r"}},
    },
    initial_state="p",
    final_states={"q", "r"},
)
print(n.epsilon_closure("p") == {"p", "r"})
dfa = n.to_dfa()
print(len(dfa.states), dfa.is_complete())
print(n.remove_epsilon_transitions().is_equivalent(n))
```

Résultat :

```text
True
4 True
True
```

```python
print(d.to_regex())            # style du cours
print(d.to_regex_optimum())    # essaie plusieurs ordres d'élimination
```

Résultat :

```text
(b*|b*ab*a((b|ab*ab*a))*ab*)
(b|ab*ab*a)*
```

```python
r = NFA.from_regex("(a|b)*abb", input_symbols={"a", "b"})   # construction de Thompson
print(r.accepts_input("aabb"), r.accepts_input("abab"))
```

Résultat :

```text
True False
```

## Opérations et relations entre langages

Produit, complément, inclusion, équivalence avec contre-exemple.

```python
sans_a = DFA(
    states={"0", "1"}, input_symbols={"a", "b"},
    transitions={"0": {"a": "1", "b": "0"}, "1": {"a": "1", "b": "1"}},
    initial_state="0", final_states={"0"},
)   # mots sans 'a'
print(d.intersection(sans_a).accepts_input("bbb"), d.intersection(sans_a).accepts_input("aaa"))
print(sans_a.is_included_in(d), d.is_included_in(sans_a))
print(d.inclusion_counterexample(sans_a))      # plus court mot de d qui n'est pas dans sans_a
print(d.is_equivalent(d.minimize()), d.complement().accepts_input("a"))
print(repr(d.shortest_word()), repr(d.complement().shortest_word()))
```

Résultat :

```text
True False
True False
aaa
True True
'' 'a'
```

## Grammaires et dérivations

Grammaire régulière linéaire à droite équivalente à un automate, et inversement.

```python
print(d.to_grammar())
print(d.derivation_tree("aaa").sequence())
```

Résultat :

```text
0 -> a1 | b0 | ε
1 -> a2 | b1
2 -> a0 | b2
0 => a1 => aa2 => aaa0 => aaa
```

```python
g = NFA.from_grammar_string("S -> aS | b")
print(g.accepts_input("aab"), g.accepts_input("aba"))
```

Résultat :

```text
True False
```

## Mode pas à pas

Les algorithmes du cours montrés étape par étape, comme sur une copie.

```python
print(n.determinization_table())     # construction par sous-ensembles
```

Résultat :

```text
         | a       | b
---------+---------+----
->*{p,r} | {p,q,r} | ∅
*{p,q,r} | {p,q,r} | {q}
       ∅ | ∅       | ∅
    *{q} | ∅       | {q}
```

```python
print(c6.moore_partitions_str())     # partitions successives de Moore
```

Résultat :

```text
P0 : {1,2,4,5,6,7,8} | {3}
P1 : {1,5,7} | {2,8} | {3} | {4,6}
P2 : {1,5} | {2,8} | {3} | {4,6} | {7}
```

```python
small = DFA(
    states={"1", "2", "3"}, input_symbols={"a", "b"},
    transitions={"1": {"a": "2", "b": "3"}, "2": {"a": "2", "b": "3"}, "3": {"a": "3", "b": "3"}},
    initial_state="1", final_states={"2"},
)
print(small.to_regex_steps_str())                       # élimination d'états
print()
print(small.to_regex_steps_str(order=["3", "2", "1"]))  # avec l'ordre de votre choix
```

Résultat :

```text
Départ :
  début -> 1 : ()
  1 -> 2 : a
  1 -> 3 : b
  2 -> 2 : a
  2 -> 3 : b
  2 -> fin : ()
  3 -> 3 : (a|b)
Suppression de 1 :
  début -> 2 : a
  début -> 3 : b
  2 -> 2 : a
  2 -> 3 : b
  2 -> fin : ()
  3 -> 3 : (a|b)
Suppression de 2 :
  début -> 3 : (b|aa*b)
  début -> fin : aa*
  3 -> 3 : (a|b)
Suppression de 3 :
  début -> fin : aa*

Départ :
  début -> 1 : ()
  1 -> 2 : a
  1 -> 3 : b
  2 -> 2 : a
  2 -> 3 : b
  2 -> fin : ()
  3 -> 3 : (a|b)
Suppression de 3 :
  début -> 1 : ()
  1 -> 2 : a
  2 -> 2 : a
  2 -> fin : ()
Suppression de 2 :
  début -> 1 : ()
  1 -> fin : aa*
Suppression de 1 :
  début -> fin : aa*
```

## Graphe, quotients, algèbre

L'automate vu comme un graphe, quotients par un mot, monoïde syntaxique.

```python
print(d.bfs(), d.dfs())
print([sorted(c) for c in d.strongly_connected_components()])
print(d.reachable_states("1") == {"0", "1", "2"}, d.has_cycle())
```

Résultat :

```text
['0', '1', '2'] ['0', '1', '2']
[['0', '1', '2']]
True True
```

```python
print(d.left_quotient_word("a").accepts_input("aa"))
print(sorted(d.residual_automaton().states))
print(list(d.syntactic_monoid()))      # plus courts mots représentant chaque élément
print(d.is_prefix_closed(), d.prefix_closed_sublanguage().accepts_input(""))
```

Résultat :

```text
True
['q0', 'q1', 'q2']
['', 'a', 'aa']
False True
```

## Visualisation

Le rendu appelle directement le binaire Graphviz `dot` (vérifiez `dot -V`).

```python
print(small.transition_table())
print(small.execution_trace("aab"))
```

Résultat :

```text
    | a | b
----+---+--
->1 | 2 | 3
 *2 | 2 | 3
  3 | 3 | 3
[('1', 'a', '2'), ('2', 'a', '2'), ('2', 'b', '3')]
```

```python
print(small.dot())      # source DOT, texte pur
```

Résultat :

```text
digraph {
	rankdir=LR
	__start__ [shape=point style=invis]
	__start__ -> s0
	s0 [label=1 shape=circle]
	s1 [label=2 shape=doublecircle]
	s2 [label=3 shape=circle]
	s0 -> s1 [label=a]
	s0 -> s2 [label=b]
	s1 -> s1 [label=a]
	s1 -> s2 [label=b]
	s2 -> s2 [label="a,b"]
}
```

```python
# Dans un notebook : écrire `d` seul dans une cellule dessine l'automate.
d.save("automate.svg")                 # .svg .png .pdf, ou .dot .tex .tikz sans Graphviz
d.svg(highlight="aab")                 # parcours du mot en rouge (DFA)
print(d.tikz())                        # code TikZ ; d.latex() = document complet

from IPython.display import HTML
HTML(d.animate("aab"))                 # animation pas à pas de la lecture d'un mot
```

