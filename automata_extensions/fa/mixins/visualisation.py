"""
VisualisationMixin
==================

Représentations visuelles d'un automate (DFA ou NFA, epsilon-transitions
comprises) :

- `dot()` : source DOT de Graphviz, en texte pur (rien à installer) ;
- `svg()`, `png()`, `pdf()`, `save()` : rendu par le binaire Graphviz
  `dot`, appelé directement en sous-processus (aucun paquet Python à
  installer, et aucun conflit possible entre `pygraphviz` et `manim`) ;
- `tikz()` et `latex()` : code TikZ / document LaTeX, en texte pur ;
- `transition_table()` : table de transitions en texte ;
- `execution_trace(mot)` : suite des transitions suivies en lisant un mot
  (DFA) ; `dot(highlight=mot)` et les rendus colorient ce parcours ;
- `animate(mot)` : animation HTML autonome de la lecture d'un mot (DFA) ;
- `_repr_svg_()` : un automate affiché dans une cellule de notebook est
  dessiné automatiquement.

Le diagramme `show_diagram()` d'automata-lib reste disponible tel quel.

Convention des noms : les états sont numérotés `s0`, `s1`... dans l'ordre
alphabétique de leur nom (reproductible). Une epsilon-transition est
étiquetée `ε`. Plusieurs symboles entre les deux mêmes états donnent une
seule arête, étiquetée `a,b`.
"""
import html
import itertools
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ..fa import _cle_tri

EPSILON = ""
EPSILON_AFFICHE = "ε"

_compteur_animations = itertools.count(1)

_IDENTIFIANT_DOT = re.compile(
    r"([a-zA-Z_][a-zA-Z0-9_]*|-?(\.[0-9]+|[0-9]+(\.[0-9]*)?))$"
)


# ----------------------------------------------------------------------
# Fonctions utilitaires
# ----------------------------------------------------------------------

def _nom(etat):
    """Nom affiché d'un état : lui-même pour une chaîne, sinon son
    écriture reproductible (voir `_cle_tri`)."""
    return etat if isinstance(etat, str) else _cle_tri(etat)


def _id_dot(texte):
    """Écrit `texte` comme identifiant DOT : tel quel s'il est simple,
    entre guillemets (avec échappement) sinon."""
    if _IDENTIFIANT_DOT.match(texte):
        return texte
    echappe = texte.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{echappe}"'


def _etiquette(symboles):
    """Étiquette d'une arête : les symboles triés (epsilon en dernier),
    séparés par des virgules."""
    ordre = sorted(symboles, key=lambda s: (s == EPSILON, s))
    return ",".join(EPSILON_AFFICHE if s == EPSILON else s for s in ordre)


def _echapper_latex(texte):
    """Échappe les caractères spéciaux de LaTeX (pour du texte placé en
    mode mathématique)."""
    remplacements = {
        "\\": r"\backslash ", "{": r"\{", "}": r"\}", "_": r"\_",
        "#": r"\#", "%": r"\%", "&": r"\&", "$": r"\$", "^": r"\^{}",
        "~": r"\~{}",
    }
    return "".join(remplacements.get(c, c) for c in texte)


def _formater_table(etiquettes, en_tetes, lignes_de_cellules):
    """Met en forme une table de texte : `etiquettes` (une par ligne,
    alignées à droite), `en_tetes` (une par colonne) et
    `lignes_de_cellules` (une liste de cellules par ligne). Les colonnes
    sont séparées par ` | ` et l'en-tête est souligné."""
    largeur0 = max(len(e) for e in etiquettes)
    largeurs = [
        max([len(en_tetes[j])] + [len(l[j]) for l in lignes_de_cellules])
        for j in range(len(en_tetes))
    ]
    lignes = [
        " | ".join(["".ljust(largeur0)]
                   + [en_tetes[j].ljust(largeurs[j])
                      for j in range(len(en_tetes))]),
        "-+-".join(["-" * largeur0] + ["-" * w for w in largeurs]),
    ]
    for etiquette, cellules in zip(etiquettes, lignes_de_cellules):
        lignes.append(
            " | ".join([etiquette.rjust(largeur0)]
                       + [cellules[j].ljust(largeurs[j])
                          for j in range(len(en_tetes))])
        )
    return "\n".join(ligne.rstrip() for ligne in lignes)


def _distance_point_segment(point, debut, fin):
    """Distance du point au segment [debut, fin] (coordonnées (x, y))."""
    (px, py), (ax, ay), (bx, by) = point, debut, fin
    dx, dy = bx - ax, by - ay
    longueur2 = dx * dx + dy * dy
    if longueur2 == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / longueur2))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def _trouver_graphviz(programme="dot"):
    """Chemin du programme Graphviz demandé (par défaut `dot`) : d'abord
    dans le PATH, puis à côté de l'interpréteur Python courant (cas d'un
    environnement conda). Lève `RuntimeError` avec une explication si
    Graphviz est introuvable."""
    chemin = shutil.which(programme)
    if chemin:
        return chemin
    racine = Path(sys.executable).resolve().parent
    for candidat in (
        racine / programme, racine / f"{programme}.exe",
        racine.parent / "bin" / programme,
        racine.parent / "Library" / "bin" / f"{programme}.exe",
        racine / "Library" / "bin" / f"{programme}.exe",
    ):
        if candidat.exists():
            return str(candidat)
    raise RuntimeError(
        f"Programme Graphviz {programme!r} introuvable. Installez Graphviz "
        "(`conda install graphviz`, ou `sudo apt install graphviz` sous "
        "Ubuntu) et vérifiez que `dot -V` fonctionne dans ce terminal."
    )


class VisualisationMixin:
    """Mixin de visualisation, à utiliser avec `ExtendedFA`."""

    # ------------------------------------------------------------------
    # Données communes
    # ------------------------------------------------------------------

    def _etats_ordonnes(self):
        return sorted(self.states, key=_cle_tri)

    def _aretes_fusionnees(self):
        """Dictionnaire {(source, cible): ensemble de symboles}."""
        aretes = {}
        for source, symbole, cible in self._labeled_edges():
            aretes.setdefault((source, cible), set()).add(symbole)
        return aretes

    # ------------------------------------------------------------------
    # Parcours d'un mot
    # ------------------------------------------------------------------

    def execution_trace(self, word):
        """Trace de la lecture de `word` : liste des transitions suivies,
        sous la forme (état, symbole, état suivant). Si une transition
        manque (DFA partiel), la trace s'arrête là. La trace est
        renvoyée que le mot soit accepté ou non.

        Défini pour un DFA seulement (`NotImplementedError` pour un NFA :
        déterminisez d'abord avec `to_dfa()`).

        Exemple : `execution_trace("aab")` ->
        `[('0', 'a', '1'), ('1', 'a', '2'), ('2', 'b', '2')]`

        Complexité : O(|word|).
        """
        from automata.fa.dfa import DFA

        if not isinstance(self, DFA):
            raise NotImplementedError(
                "execution_trace() n'est défini que pour un DFA "
                "(déterminisez d'abord avec to_dfa())."
            )
        trace = []
        etat = self.initial_state
        for symbole in word:
            table = self.transitions.get(etat, {})
            if symbole not in table:
                break
            cible = table[symbole]
            trace.append((etat, symbole, cible))
            etat = cible
        return trace

    # ------------------------------------------------------------------
    # DOT (Graphviz)
    # ------------------------------------------------------------------

    def _construire_dot(self, etats_surlignes=(), aretes_surlignees=(),
                        etat_courant=None):
        """Source DOT. `etats_surlignes` : états entourés en rouge ;
        `aretes_surlignees` : couples (source, cible) tracés en rouge ;
        `etat_courant` : état rempli en jaune (animation)."""
        etats = self._etats_ordonnes()
        numero = {etat: i for i, etat in enumerate(etats)}
        rouges = set(etats_surlignes)
        lignes = [
            "digraph {",
            "\trankdir=LR",
            "\t__start__ [shape=point style=invis]",
            f"\t__start__ -> s{numero[self.initial_state]}",
        ]
        for etat in etats:
            forme = "doublecircle" if etat in self.final_states else "circle"
            attributs = f"label={_id_dot(_nom(etat))} shape={forme}"
            if etat == etat_courant:
                attributs += " style=filled fillcolor=gold"
            if etat in rouges:
                attributs += " color=red"
            lignes.append(f"\ts{numero[etat]} [{attributs}]")
        aretes = self._aretes_fusionnees()
        cles = sorted(aretes, key=lambda a: (numero[a[0]], numero[a[1]]))
        surlignees = set(aretes_surlignees)
        for source, cible in cles:
            attributs = f"label={_id_dot(_etiquette(aretes[(source, cible)]))}"
            if (source, cible) in surlignees:
                attributs += " color=red penwidth=2"
            lignes.append(
                f"\ts{numero[source]} -> s{numero[cible]} [{attributs}]"
            )
        lignes.append("}")
        return "\n".join(lignes) + "\n"

    def dot(self, *, highlight=None):
        """Source DOT (Graphviz) de l'automate, en texte pur : le binaire
        Graphviz n'est pas nécessaire pour l'obtenir.

        Si `highlight` est un mot (DFA), les états visités et les
        transitions suivies en le lisant sont coloriés en rouge.

        Complexité : O(|Q| + |E|).
        """
        if highlight is None:
            return self._construire_dot()
        trace = self.execution_trace(highlight)
        visites = {self.initial_state} | {cible for _, _, cible in trace}
        return self._construire_dot(
            etats_surlignes=visites,
            aretes_surlignees={(s, c) for s, _, c in trace},
        )

    # ------------------------------------------------------------------
    # Rendu par Graphviz (sous-processus)
    # ------------------------------------------------------------------

    @staticmethod
    def _rendre_source(source_dot, fmt, programme="dot"):
        """Rend une source DOT dans le format Graphviz `fmt` (svg, png,
        pdf...) en appelant le programme Graphviz ; renvoie les octets."""
        executable = _trouver_graphviz(programme)
        resultat = subprocess.run(
            [executable, f"-T{fmt}"],
            input=source_dot.encode("utf-8"),
            capture_output=True,
        )
        if resultat.returncode != 0:
            raise RuntimeError(
                "Échec du rendu Graphviz :\n"
                + resultat.stderr.decode("utf-8", errors="replace")
            )
        return resultat.stdout

    def svg(self, *, highlight=None, prog="dot"):
        """Rendu SVG de l'automate (chaîne de caractères). Nécessite le
        binaire Graphviz `dot`. `highlight` : voir `dot()`."""
        return self._rendre_source(
            self.dot(highlight=highlight), "svg", prog
        ).decode("utf-8")

    def png(self, *, highlight=None, prog="dot"):
        """Rendu PNG de l'automate (octets). Nécessite le binaire
        Graphviz `dot`."""
        return self._rendre_source(self.dot(highlight=highlight), "png", prog)

    def pdf(self, *, highlight=None, prog="dot"):
        """Rendu PDF de l'automate (octets). Nécessite le binaire
        Graphviz `dot`."""
        return self._rendre_source(self.dot(highlight=highlight), "pdf", prog)

    def save(self, filename, *, highlight=None, prog="dot", fmt=None):
        """Écrit l'automate dans un fichier ; le format est déduit de
        l'extension (ou de `fmt`) :

        - `.dot` : source DOT (sans Graphviz) ;
        - `.tex` : document LaTeX (sans Graphviz) ; `.tikz` : code TikZ ;
        - tout autre format géré par Graphviz (`.svg`, `.png`, `.pdf`...).

        Renvoie le chemin écrit.
        """
        chemin = Path(filename)
        format_ = (fmt or chemin.suffix.lstrip(".") or "png").lower()
        if format_ == "dot":
            chemin.write_text(self.dot(highlight=highlight), encoding="utf-8")
        elif format_ == "tex":
            chemin.write_text(self.latex(), encoding="utf-8")
        elif format_ == "tikz":
            chemin.write_text(self.tikz(), encoding="utf-8")
        else:
            chemin.write_bytes(
                self._rendre_source(
                    self.dot(highlight=highlight), format_, prog
                )
            )
        return chemin

    def _repr_svg_(self):
        """Affichage automatique dans un notebook Jupyter. Renvoie `None`
        (Jupyter affiche alors la représentation texte habituelle) si
        Graphviz n'est pas disponible."""
        try:
            return self.svg()
        except (RuntimeError, OSError):
            return None

    # ------------------------------------------------------------------
    # TikZ et LaTeX
    # ------------------------------------------------------------------

    def tikz(self, *, colonnes=4, ecart=3.0):
        """Code TikZ (bibliothèque `automata`) de l'automate. Les états
        sont placés sur une grille de `colonnes` colonnes, espacées de
        `ecart` cm ; les boucles sont dessinées au-dessus, les arêtes qui
        existent dans les deux sens sont courbées, et celles qui
        passeraient sur un autre état sont courbées par en dessous.

        Nécessite `\\usetikzlibrary{automata}` dans le document ; voir
        `latex()` pour un document complet.

        Complexité : O(|Q| + |E|).
        """
        etats = self._etats_ordonnes()
        numero = {etat: i for i, etat in enumerate(etats)}
        position = {
            etat: ((i % colonnes) * ecart, -(i // colonnes) * ecart)
            for i, etat in enumerate(etats)
        }
        lignes = [
            r"\begin{tikzpicture}[->, >=stealth, auto, semithick]"
        ]
        for i, etat in enumerate(etats):
            options = ["state"]
            if etat == self.initial_state:
                options += ["initial", "initial text="]
            if etat in self.final_states:
                options.append("accepting")
            x, y = position[etat]
            lignes.append(
                f"  \\node[{', '.join(options)}] (s{i}) at ({x:g},{y:g}) "
                f"{{${_echapper_latex(_nom(etat))}$}};"
            )
        aretes = self._aretes_fusionnees()
        cles = sorted(aretes, key=lambda a: (numero[a[0]], numero[a[1]]))

        def traverse_un_etat(source, cible):
            """Vrai si le segment source-cible passe près d'un autre
            état (par exemple deux états éloignés sur la même ligne)."""
            return any(
                _distance_point_segment(
                    position[autre], position[source], position[cible]
                ) < 0.6
                for autre in etats if autre != source and autre != cible
            )

        morceaux = []
        for source, cible in cles:
            if source == cible:
                option = " [loop above]"
            elif traverse_un_etat(source, cible):
                option = " [bend right=45]"
            elif (cible, source) in aretes:
                option = " [bend left]"
            else:
                option = ""
            texte = ",\\,".join(
                r"\varepsilon" if s == EPSILON else _echapper_latex(s)
                for s in sorted(aretes[(source, cible)],
                                key=lambda s: (s == EPSILON, s))
            )
            morceaux.append(
                f"(s{numero[source]}) edge{option} node {{${texte}$}} "
                f"(s{numero[cible]})"
            )
        if morceaux:
            lignes.append("  \\path " + "\n       ".join(morceaux) + ";")
        lignes.append(r"\end{tikzpicture}")
        return "\n".join(lignes) + "\n"

    def latex(self, **options):
        """Document LaTeX autonome (classe `standalone`) contenant le
        dessin TikZ de l'automate ; `options` : voir `tikz()`. Se compile
        avec `pdflatex`."""
        return (
            "\\documentclass[tikz,border=5pt]{standalone}\n"
            "\\usetikzlibrary{automata}\n"
            "\\begin{document}\n"
            + self.tikz(**options)
            + "\\end{document}\n"
        )

    # ------------------------------------------------------------------
    # Table de transitions
    # ------------------------------------------------------------------

    def transition_table(self):
        """Table de transitions en texte : une ligne par état (`->` pour
        l'état initial, `*` pour un état final), une colonne par symbole
        (et une pour epsilon s'il y en a). Une case contient l'état
        cible, `{p,q}` pour plusieurs cibles, ou `-` s'il n'y en a pas.
        Complexité : O(|Q| · |Σ|)."""
        symboles = sorted(s for s in self.input_symbols if s != EPSILON)
        cibles = {}
        for source, symbole, cible in self._labeled_edges():
            cibles.setdefault((source, symbole), set()).add(cible)
        if any(s == EPSILON for (_, s) in cibles):
            symboles.append(EPSILON)

        def cellule(etat, symbole):
            ensemble = cibles.get((etat, symbole), set())
            noms = sorted(_nom(c) for c in ensemble)
            if not noms:
                return "-"
            return noms[0] if len(noms) == 1 else "{" + ",".join(noms) + "}"

        etats = self._etats_ordonnes()
        etiquettes = [
            ("->" if e == self.initial_state else "")
            + ("*" if e in self.final_states else "")
            + _nom(e)
            for e in etats
        ]
        en_tetes = [EPSILON_AFFICHE if s == EPSILON else s for s in symboles]
        lignes_cellules = [
            [cellule(e, s) for s in symboles] for e in etats
        ]
        return _formater_table(etiquettes, en_tetes, lignes_cellules)

    # ------------------------------------------------------------------
    # Animation HTML
    # ------------------------------------------------------------------

    def animate(self, word, *, interval=900):
        """Animation HTML autonome (un seul fichier, sans bibliothèque
        externe) de la lecture de `word` : une image par lettre lue,
        avec les boutons Précédent / Suivant / Lecture. L'état courant
        est en jaune et la dernière transition suivie en rouge. Renvoie
        le code HTML (chaîne) ; dans un notebook :
        `IPython.display.HTML(automate.animate("aab"))`.

        Défini pour un DFA. Nécessite le binaire Graphviz `dot` (une
        image SVG par étape). `interval` : durée d'une étape en lecture
        automatique, en millisecondes.

        Complexité : |word| + 1 appels à Graphviz.
        """
        trace = self.execution_trace(word)
        etats = [self.initial_state] + [cible for _, _, cible in trace]
        lus = len(trace)
        accepte = lus == len(word) and etats[-1] in self.final_states

        images = []
        for i, etat in enumerate(etats):
            aretes = {(trace[i - 1][0], trace[i - 1][2])} if i else set()
            source = self._construire_dot(
                aretes_surlignees=aretes, etat_courant=etat
            )
            svg = self._rendre_source(source, "svg").decode("utf-8")
            images.append(svg[svg.index("<svg"):])

        legendes = []
        for i, etat in enumerate(etats):
            if i == 0:
                legendes.append(f"Départ : état {_nom(etat)}")
            else:
                _, symbole, _ = trace[i - 1]
                legendes.append(
                    f"Lecture de « {symbole} » : état {_nom(etat)}"
                )
        if lus < len(word):
            conclusion = (
                f"Mot rejeté : aucune transition pour « {word[lus]} » "
                f"depuis l'état {_nom(etats[-1])}"
            )
        elif accepte:
            conclusion = f"Mot accepté : l'état {_nom(etats[-1])} est final"
        else:
            conclusion = f"Mot rejeté : l'état {_nom(etats[-1])} n'est pas final"

        cadres = "\n".join(
            f'<div class="cadre" style="display:none">{svg}</div>'
            for svg in images
        )
        # JSON : valide en JavaScript ; "</" est protégé pour ne pas fermer
        # la balise <script> si un nom d'état contient "</script>".
        legendes_js = json.dumps(legendes, ensure_ascii=False).replace(
            "</", "<\\/"
        )
        mot_affiche = html.escape(word) if word else "ε"
        return _MODELE_ANIMATION.format(
            identifiant=f"animation-automate-{next(_compteur_animations)}",
            mot=mot_affiche,
            cadres=cadres,
            legendes=legendes_js,
            conclusion=html.escape(conclusion),
            statut="accepte" if accepte else "rejete",
            nombre=len(images),
            interval=int(interval),
        )


_MODELE_ANIMATION = """<div id="{identifiant}" class="animation-automate" style="font-family:sans-serif">
<p>Mot lu : <b>{mot}</b></p>
{cadres}
<p class="legende" style="min-height:1.5em"></p>
<p class="conclusion" style="display:none;font-weight:bold" data-statut="{statut}">{conclusion}</p>
<button class="precedent">&#9664; Précédent</button>
<button class="suivant">Suivant &#9654;</button>
<button class="lecture">&#9654; Lecture</button>
<span class="compteur"></span>
<script>
(function () {{
  var racine = document.getElementById("{identifiant}");
  var cadres = racine.querySelectorAll(".cadre");
  var legendes = {legendes};
  var nombre = {nombre};
  var interval = {interval};
  var courant = 0;
  var minuteur = null;
  function afficher(i) {{
    courant = Math.max(0, Math.min(nombre - 1, i));
    for (var k = 0; k < cadres.length; k++) {{
      cadres[k].style.display = (k === courant) ? "block" : "none";
    }}
    racine.querySelector(".legende").textContent = legendes[courant];
    racine.querySelector(".compteur").textContent =
      " étape " + (courant + 1) + " / " + nombre;
    racine.querySelector(".conclusion").style.display =
      (courant === nombre - 1) ? "block" : "none";
  }}
  function arreter() {{
    if (minuteur !== null) {{ clearInterval(minuteur); minuteur = null; }}
    racine.querySelector(".lecture").innerHTML = "&#9654; Lecture";
  }}
  racine.querySelector(".precedent").onclick = function () {{ arreter(); afficher(courant - 1); }};
  racine.querySelector(".suivant").onclick = function () {{ arreter(); afficher(courant + 1); }};
  racine.querySelector(".lecture").onclick = function () {{
    if (minuteur !== null) {{ arreter(); return; }}
    if (courant === nombre - 1) {{ afficher(0); }}
    racine.querySelector(".lecture").innerHTML = "&#9208; Pause";
    minuteur = setInterval(function () {{
      if (courant >= nombre - 1) {{ arreter(); }} else {{ afficher(courant + 1); }}
    }}, interval);
  }};
  afficher(0);
}})();
</script>
</div>
"""
