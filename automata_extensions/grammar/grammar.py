"""
Grammaires régulières (linéaires à droite) et dérivations.

Une grammaire régulière a des règles de la forme  A -> w B  (un mot de
terminaux suivi d'un unique non-terminal) ou  A -> w  (terminaux
seulement, éventuellement le mot vide). Elles engendrent exactement les
langages reconnus par les automates finis.

Ce module est indépendant de tout automate : les conversions
automate <-> grammaire sont dans `ConversionsMixin`/`GrammaireMixin`
(`to_grammar`, `derivation_tree`) et dans `ExtendedNFA.from_grammar`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

EPSILON_TEXTE = "ε"


@dataclass(frozen=True)
class Rule:
    """Règle  left -> word right  (right vaut None s'il n'y a pas de
    non-terminal en fin de règle). `word` est une chaîne de terminaux,
    éventuellement vide."""
    left: str
    word: str
    right: Optional[str] = None

    def __str__(self):
        droite = self.word + (self.right or "")
        return f"{self.left} -> {droite or EPSILON_TEXTE}"


@dataclass(frozen=True)
class Grammar:
    """Grammaire régulière linéaire à droite : un axiome `start` et des
    règles. Les non-terminaux sont l'axiome et tous les noms qui
    apparaissent dans les règles ; les terminaux sont les lettres des
    mots de terminaux."""
    start: str
    rules: Tuple[Rule, ...]

    # -- Propriétés --------------------------------------------------

    @property
    def non_terminals(self):
        """Ensemble des non-terminaux."""
        noms = {self.start}
        for regle in self.rules:
            noms.add(regle.left)
            if regle.right is not None:
                noms.add(regle.right)
        return noms

    @property
    def terminals(self):
        """Ensemble des terminaux (les lettres des mots des règles)."""
        return {lettre for regle in self.rules for lettre in regle.word}

    def rules_of(self, non_terminal):
        """Règles dont le membre gauche est `non_terminal`."""
        return [r for r in self.rules if r.left == non_terminal]

    # -- Affichage ---------------------------------------------------

    def __str__(self):
        """Format classique : une ligne par non-terminal, les
        alternatives séparées par `|`, le mot vide écrit `ε`. L'axiome
        est écrit en premier."""
        ordre = [self.start]
        for regle in self.rules:
            if regle.left not in ordre:
                ordre.append(regle.left)
        lignes = []
        for non_terminal in ordre:
            alternatives = [
                (r.word + (r.right or "")) or EPSILON_TEXTE
                for r in self.rules_of(non_terminal)
            ]
            lignes.append(
                f"{non_terminal} -> {' | '.join(alternatives) or '∅'}"
            )
        return "\n".join(lignes)

    # -- Analyse d'un texte ------------------------------------------

    @classmethod
    def from_string(cls, texte):
        """Grammaire décrite par un texte au format classique :

            S -> aS | bT | ε
            T -> bT | a

        - une règle par ligne (ou séparées par `;`), `->` ou `→` entre
          les deux membres, `|` entre les alternatives ;
        - le premier membre gauche est l'axiome ;
        - sont des non-terminaux les noms qui apparaissent à gauche
          d'une flèche (de n'importe quelle longueur) ; tout le reste
          est terminal ;
        - le mot vide s'écrit `ε` (ou une alternative vide) ;
        - une alternative est un mot de terminaux, suivi éventuellement
          d'un non-terminal (à la fin) ; les espaces sont ignorés.

        Lève `ValueError` si le texte n'est pas une grammaire linéaire
        à droite. Complexité : O(n · |N|) pour un texte de n caractères
        et |N| non-terminaux.
        """
        productions = []
        for ligne in re.split(r"[\n;]", texte):
            if not ligne.strip():
                continue
            morceaux = re.split(r"->|→", ligne, maxsplit=1)
            if len(morceaux) != 2:
                raise ValueError(
                    f"Règle sans flèche '->' : {ligne.strip()!r}"
                )
            gauche = morceaux[0].strip()
            if not gauche or any(c.isspace() for c in gauche):
                raise ValueError(
                    f"Membre gauche invalide : {morceaux[0]!r} (un seul "
                    "nom de non-terminal, sans espace)"
                )
            productions.append((gauche, morceaux[1].split("|")))
        if not productions:
            raise ValueError("Grammaire vide : aucune règle.")

        non_terminaux = {gauche for gauche, _ in productions}
        par_longueur = sorted(non_terminaux, key=len, reverse=True)
        regles = []
        for gauche, alternatives in productions:
            for alternative in alternatives:
                texte_alt = "".join(alternative.split())
                if texte_alt in ("", EPSILON_TEXTE):
                    regles.append(Rule(gauche, "", None))
                    continue
                if texte_alt == "∅":
                    continue
                droite, mot = None, texte_alt
                for nom in par_longueur:
                    if texte_alt.endswith(nom):
                        droite, mot = nom, texte_alt[: -len(nom)]
                        break
                for nom in non_terminaux:
                    if nom in mot:
                        raise ValueError(
                            f"Règle non linéaire à droite : {gauche} -> "
                            f"{texte_alt} (le non-terminal {nom!r} doit "
                            "être à la fin de la règle)"
                        )
                regles.append(Rule(gauche, mot, droite))
        return cls(start=productions[0][0], rules=tuple(regles))

    # -- Langage engendré --------------------------------------------

    def generates(self, mot):
        """Vrai si la grammaire engendre `mot`. Recherche des couples
        (non-terminal, position) atteignables en lisant `mot`, sans
        jamais repasser deux fois par le même couple (ce qui évite de
        boucler sur des règles comme A -> B et B -> A). Complexité :
        O(|N| · |mot| · |règles|)."""
        vus = set()
        a_traiter = [(self.start, 0)]
        while a_traiter:
            non_terminal, i = a_traiter.pop()
            if (non_terminal, i) in vus:
                continue
            vus.add((non_terminal, i))
            for regle in self.rules_of(non_terminal):
                if not mot.startswith(regle.word, i):
                    continue
                j = i + len(regle.word)
                if regle.right is None:
                    if j == len(mot):
                        return True
                else:
                    a_traiter.append((regle.right, j))
        return False


@dataclass(frozen=True)
class DerivationStep:
    """Une étape d'une dérivation, suivie de toutes les suivantes
    (chaîne). L'étape représente la forme `prefix + non_terminal` : les
    terminaux déjà produits suivis du non-terminal restant (`None` à la
    dernière étape, où il ne reste que des terminaux). `rule` est la
    règle appliquée pour passer à l'étape `next` (`None` à la dernière
    étape)."""
    prefix: str
    non_terminal: Optional[str]
    rule: Optional[Rule]
    next: Optional["DerivationStep"]

    def form(self):
        """Forme de cette étape : terminaux produits + non-terminal."""
        return self.prefix + (self.non_terminal or "")

    def steps(self):
        """Liste des étapes à partir de celle-ci, dans l'ordre."""
        etapes, courante = [], self
        while courante is not None:
            etapes.append(courante)
            courante = courante.next
        return etapes

    def word(self):
        """Mot dérivé : les terminaux de la dernière étape."""
        return self.steps()[-1].prefix

    def sequence(self):
        """Suite classique des formes, séparées par ` => ` ; une forme
        vide s'écrit `ε`. Exemple : `0 => a1 => aa2 => aaa0 => aaa`."""
        return " => ".join(
            etape.form() or EPSILON_TEXTE for etape in self.steps()
        )
