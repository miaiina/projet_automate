"""
GrammaireMixin
==============

Passage entre automates et grammaires régulières (linéaires à droite).

Statut : squelette (phase 5 du projet, pas encore implémenté).

Méthodes prévues :
- to_grammar()      : grammaire régulière linéaire à droite équivalente
- from_grammar()    : construction d'un NFA à partir d'une grammaire
                      régulière linéaire à droite
- derivation_tree(word) : arbre de dérivation d'un mot accepté
"""


class GrammaireMixin:
    """Mixin grammaire, à utiliser avec `ExtendedFA`."""
