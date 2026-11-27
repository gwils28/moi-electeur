#!/usr/bin/env python3
"""CI : aucun texte produit par l'app ne classe un candidat (CLAUDE.md, SPEC § 1).

Analyse les chaînes UI (apps/web/src/i18n/), le code du chat (apps/web/src/lib/rag/) et les prompts (prompts/).
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    ROOT / "apps/web/src/i18n",
    ROOT / "apps/web/src/lib/rag",
    ROOT / "prompts",
    ROOT / "services/rag/src",
]
# Source unique, partagée avec le garde-fou de /api/ask (apps/web/src/lib/rag/neutrality.ts).
WORDS_FILE = ROOT / "prompts/forbidden_words.json"
FORBIDDEN: list[str] = json.loads(WORDS_FILE.read_text(encoding="utf-8"))["patterns"]
PATTERN = re.compile("|".join(FORBIDDEN), re.IGNORECASE)
# Une ligne peut assumer un mot interdit en le justifiant (ex. une consigne qui l'interdit).
ALLOW = "mots-interdits: autorise"


def scan(paths: list[Path], allowed: list[str] | None = None) -> list[str]:
    fautes = []
    for base in paths:
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            # Caches compilés (__pycache__/*.pyc) : binaires, hors périmètre.
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            # La liste elle-même.
            if path == WORDS_FILE:
                continue
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                m = PATTERN.search(line)
                if not m:
                    continue
                where = f"{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}:{i}"
                if ALLOW in line:
                    if allowed is not None:
                        allowed.append(where)
                else:
                    fautes.append(f"{where}: « {m.group(0)} »")
    return fautes


def main() -> int:
    allowed: list[str] = []
    fautes = scan(TARGETS, allowed)
    # Les exceptions sont toujours affichées en CI pour rester visibles en revue.
    for where in allowed:
        print(f"Exception assumée (mots-interdits: autorise) : {where}")
    if fautes:
        print("Formulation qui classe un candidat :", *fautes, sep="\n  ")
        return 1
    print("Aucune formulation de classement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
