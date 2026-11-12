# -*- coding: utf-8 -*-
"""
Le guide d'utilisation (GUIDE.md) est exécuté : chaque extrait Python est
joué dans l'ordre, et sa sortie doit être exactement celle qui est écrite
dans le guide. Ainsi le guide ne peut pas devenir faux sans qu'un test
échoue.
"""
import contextlib
import io
import re
from pathlib import Path

GUIDE = Path(__file__).resolve().parent.parent / "GUIDE.md"

BLOC = re.compile(
    r"```python\n(.*?)\n```(?:\n\nRésultat :\n\n```text\n(.*?)\n```)?", re.S
)


def test_les_extraits_du_guide_donnent_les_resultats_ecrits():
    texte = GUIDE.read_text(encoding="utf-8")
    espace = {}
    executes = 0
    for code, attendu in BLOC.findall(texte):
        if "IPython" in code:         # extrait de notebook : non exécuté ici
            continue
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            exec(compile(code, "<guide>", "exec"), espace)
        executes += 1
        if attendu:
            assert sortie.getvalue().rstrip("\n") == attendu, code
    assert executes >= 12              # le guide contient bien des extraits
