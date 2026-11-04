"""
Expressions régulières sous forme d'arbre (AST), indépendantes de tout
automate.

Ce module est utilisé par les conversions automate -> regex
(`ConversionsMixin.to_regex`, Arden, variantes `optimum`). Il définit :

- les noeuds : `Empty` (le langage vide), `Eps` (le mot vide), `Sym`
  (une lettre), `Cat` (concaténation), `Alt` (union), `Star` (étoile) ;
- des constructeurs "intelligents" `alt`, `cat`, `star`, qui appliquent
  uniquement les identités triviales (aplatir, retirer le vide et le mot
  vide là où c'est évident) ;
- `simplify`, qui applique en plus quelques règles algébriques ;
- `to_string`, qui écrit l'expression avec la syntaxe d'automata-lib :
  `|` pour l'union, `*` pour l'étoile, `()` pour le mot vide. Le langage
  vide s'écrit `∅` (symbole non reconnu par automata-lib : il ne peut
  apparaître qu'en résultat complet, jamais à l'intérieur d'une
  expression).

Attention : dans automata-lib, `+` est l'opérateur "un ou plus" (postfixe)
et non l'union ; on n'écrit donc jamais `a+b` pour une union.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

# Caractères qui ne peuvent pas être des lettres d'une expression écrite.
CARACTERES_RESERVES = set("()|*+?.&^~{}\\∅")


# ----------------------------------------------------------------------
# Noeuds
# ----------------------------------------------------------------------

class Regex:
    """Classe de base des noeuds d'expression régulière."""


@dataclass(frozen=True)
class Empty(Regex):
    """Le langage vide."""


@dataclass(frozen=True)
class Eps(Regex):
    """Le langage réduit au mot vide."""


@dataclass(frozen=True)
class Sym(Regex):
    """Une lettre."""
    char: str


@dataclass(frozen=True)
class Cat(Regex):
    """Concaténation (au moins deux facteurs)."""
    parts: Tuple[Regex, ...]


@dataclass(frozen=True)
class Alt(Regex):
    """Union (au moins deux termes)."""
    parts: Tuple[Regex, ...]


@dataclass(frozen=True)
class Star(Regex):
    """Étoile de Kleene."""
    inner: Regex


EMPTY = Empty()
EPS = Eps()


# ----------------------------------------------------------------------
# Constructeurs (identités triviales seulement)
# ----------------------------------------------------------------------

def alt(*termes):
    """Union de plusieurs expressions : aplatit les unions imbriquées,
    retire le langage vide et les doublons. Complexité : O(n²) pour n
    termes (test d'appartenance dans une liste)."""
    parts = []
    for terme in termes:
        for element in (terme.parts if isinstance(terme, Alt) else (terme,)):
            if isinstance(element, Empty):
                continue
            if element not in parts:
                parts.append(element)
    if not parts:
        return EMPTY
    if len(parts) == 1:
        return parts[0]
    return Alt(tuple(parts))


def cat(*facteurs):
    """Concaténation : aplatit les concaténations imbriquées, retire le
    mot vide, et renvoie le langage vide si un facteur est vide.
    Complexité : O(n)."""
    parts = []
    for facteur in facteurs:
        if isinstance(facteur, Empty):
            return EMPTY
        for element in (
            facteur.parts if isinstance(facteur, Cat) else (facteur,)
        ):
            if not isinstance(element, Eps):
                parts.append(element)
    if not parts:
        return EPS
    if len(parts) == 1:
        return parts[0]
    return Cat(tuple(parts))


def star(expression):
    """Étoile : le vide* et le mot vide* valent le mot vide, et (x*)*
    vaut x*. Complexité : O(1)."""
    if isinstance(expression, (Empty, Eps)):
        return EPS
    if isinstance(expression, Star):
        return expression
    return Star(expression)


# ----------------------------------------------------------------------
# Propriétés et simplification
# ----------------------------------------------------------------------

def is_nullable(expression):
    """Vrai si le mot vide appartient au langage de l'expression.
    Complexité : O(taille de l'expression)."""
    if isinstance(expression, (Eps, Star)):
        return True
    if isinstance(expression, (Empty, Sym)):
        return False
    if isinstance(expression, Alt):
        return any(is_nullable(p) for p in expression.parts)
    return all(is_nullable(p) for p in expression.parts)


def simplify(expression):
    """Simplifie une expression en conservant son langage.

    Règles appliquées, de bas en haut, en plus de celles des
    constructeurs `alt`, `cat` et `star` :
    - x | x*      ->  x*          (x est inclus dans x*)
    - x | ()      ->  x           si x contient déjà le mot vide
    - (x | ())*   ->  x*
    - x* x*       ->  x*          (deux étoiles identiques consécutives)

    Ce n'est pas une forme normale : deux expressions de même langage
    peuvent rester différentes après `simplify`. Complexité : O(n²) dans
    le pire cas pour une expression de taille n.
    """
    if isinstance(expression, (Empty, Eps, Sym)):
        return expression

    if isinstance(expression, Star):
        interieur = simplify(expression.inner)
        if isinstance(interieur, Alt):
            sans_eps = [p for p in interieur.parts if not isinstance(p, Eps)]
            if len(sans_eps) != len(interieur.parts):
                interieur = alt(*sans_eps)
        return star(interieur)

    if isinstance(expression, Cat):
        facteurs = [simplify(p) for p in expression.parts]
        resultat = []
        for facteur in facteurs:
            if (
                resultat
                and isinstance(facteur, Star)
                and resultat[-1] == facteur
            ):
                continue
            resultat.append(facteur)
        return cat(*resultat)

    termes = []
    for partie in expression.parts:
        simplifie = simplify(partie)
        termes.extend(
            simplifie.parts if isinstance(simplifie, Alt) else (simplifie,)
        )
    termes = [t for t in dict.fromkeys(termes) if not isinstance(t, Empty)]
    interieurs_des_etoiles = {t.inner for t in termes if isinstance(t, Star)}
    termes = [t for t in termes if t not in interieurs_des_etoiles]
    if any(isinstance(t, Eps) for t in termes) and any(
        is_nullable(t) for t in termes if not isinstance(t, Eps)
    ):
        termes = [t for t in termes if not isinstance(t, Eps)]
    return alt(*termes)


# ----------------------------------------------------------------------
# Affichage
# ----------------------------------------------------------------------

def verifier_lettre(lettre):
    """Lève `ValueError` si `lettre` ne peut pas être écrite dans une
    expression régulière (pas un caractère unique, ou caractère
    réservé comme `*`, `+`, `|`, `(`...)."""
    if len(lettre) != 1 or lettre in CARACTERES_RESERVES:
        raise ValueError(
            f"Le symbole {lettre!r} ne peut pas apparaître dans une "
            "expression régulière : il faut un caractère unique qui n'est "
            f"pas l'un de {''.join(sorted(CARACTERES_RESERVES))}."
        )


def _avec_parentheses(expression):
    return "(" + to_string(expression) + ")"


def to_string(expression):
    """Écrit l'expression avec la syntaxe d'automata-lib (`|`, `*`, `()`
    pour le mot vide), en ne mettant de parenthèses que quand elles sont
    nécessaires. Le langage vide s'écrit `∅`. Complexité : O(taille)."""
    if isinstance(expression, Empty):
        return "∅"
    if isinstance(expression, Eps):
        return "()"
    if isinstance(expression, Sym):
        verifier_lettre(expression.char)
        return expression.char
    if isinstance(expression, Alt):
        return "|".join(
            _avec_parentheses(p) if isinstance(p, Alt) else to_string(p)
            for p in expression.parts
        )
    if isinstance(expression, Cat):
        return "".join(
            _avec_parentheses(p) if isinstance(p, Alt) else to_string(p)
            for p in expression.parts
        )
    interieur = expression.inner
    texte = (
        to_string(interieur)
        if isinstance(interieur, Sym)
        else _avec_parentheses(interieur)
    )
    return texte + "*"
