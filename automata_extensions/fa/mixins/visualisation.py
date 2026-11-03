"""
VisualisationMixin
===================

Export visuel d'un automate : code DOT, rendu via Graphviz (pygraphviz,
cohérent avec `setup_avec_conda_automata.py` / `setup_sans_conda_automata.py`),
export TikZ en Python pur (sans dépendance externe).

Statut : squelette (phase 6 du projet, pas encore implémenté).

Méthodes prévues :
- dot()          : code source DOT (texte pur, toujours testable)
- svg()          : rendu SVG (nécessite le binaire `dot` installé)
- png() / pdf()  : autres formats de rendu Graphviz
- tikz()         : code source TikZ/LaTeX (texte pur, sans Graphviz)
- to_table()     : table de transitions, en texte ou LaTeX
- highlight_run(word) : variante de dot()/svg() avec le chemin suivi par
                        un mot mis en évidence (pour l'exécution pas à pas)

Remarque : les tests de rendu (`svg`, `png`, `pdf`) seront marqués
`@pytest.mark.skipif` si le binaire `dot` est absent de l'environnement,
pour ne pas faire échouer toute la suite sur une machine sans Graphviz.
"""


class VisualisationMixin:
    """Mixin de visualisation, à utiliser avec `ExtendedFA`."""
