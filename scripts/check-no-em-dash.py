#!/usr/bin/env python3
"""CI : échoue si un fichier suivi par git contient le tiret cadratin (U+2014).

Complète le hook .claude/hooks/no-em-dash.py, qui ne protège que les sessions Claude Code.
Le caractère est désigné par son code pour que ce fichier respecte lui-même la règle.
"""

import subprocess
import sys

EM = chr(0x2014)


def main() -> int:
    files = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    fautes = []
    for name in files:
        try:
            with open(name, encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if EM in line:
                        fautes.append(f"{name}:{i}: {line.strip()[:80]}")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
    if fautes:
        print("Tiret cadratin (U+2014) interdit :", *fautes, sep="\n  ")
        return 1
    print(f"Aucun tiret cadratin ({len(files)} fichiers).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
