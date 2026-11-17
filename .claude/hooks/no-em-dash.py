#!/usr/bin/env python3
"""Interdit le tiret cadratin (U+2014) partout : fichiers écrits, commandes shell, réponses.

Usage :
  no-em-dash.py pre   (PreToolUse)  : bloque l'appel d'outil si le contenu écrit en contient un.
  no-em-dash.py stop  (Stop)        : bloque la fin du tour si la dernière réponse en contient un.

Le caractère est désigné par son code (EM) pour que ce fichier respecte lui-même la règle.
"""
import json
import sys

EM = chr(0x2014)
CONSIGNE = (
    "Tiret cadratin (U+2014) interdit dans le code, les commentaires, la documentation "
    "et les réponses. Remplace-le par une virgule, deux-points, des parenthèses ou un tiret simple '-'."
)


def textes_ecrits(tool_name: str, tool_input: dict) -> list[str]:
    """Ne renvoie que le contenu NOUVEAU (pas old_string, pour pouvoir supprimer des tirets existants)."""
    textes: list[str] = []
    if tool_name == "Write":
        textes.append(tool_input.get("content", ""))
    elif tool_name == "Edit":
        textes.append(tool_input.get("new_string", ""))
    elif tool_name == "MultiEdit":
        textes += [e.get("new_string", "") for e in tool_input.get("edits", [])]
    elif tool_name == "NotebookEdit":
        textes.append(tool_input.get("new_source", ""))
    elif tool_name == "Bash":
        textes.append(tool_input.get("command", ""))
    return textes


def lignes_fautives(texte: str) -> list[str]:
    return [f"  l.{i}: {l.strip()[:100]}" for i, l in enumerate(texte.splitlines(), 1) if EM in l][:5]


def mode_pre(data: dict) -> int:
    fautes: list[str] = []
    for t in textes_ecrits(data.get("tool_name", ""), data.get("tool_input", {}) or {}):
        fautes += lignes_fautives(t)
    if fautes:
        print(CONSIGNE + "\nOccurrences :\n" + "\n".join(fautes), file=sys.stderr)
        return 2
    return 0


def derniere_reponse(transcript_path: str) -> str:
    """Concatène les blocs texte de l'assistant depuis le dernier vrai message utilisateur."""
    try:
        with open(transcript_path, encoding="utf-8") as f:
            entrees = [json.loads(l) for l in f if l.strip()]
    except (OSError, json.JSONDecodeError):
        return ""
    textes: list[str] = []
    for e in reversed(entrees):
        msg = e.get("message") or {}
        contenu = msg.get("content")
        if e.get("type") == "user":
            vrai_message = isinstance(contenu, str) or any(
                isinstance(b, dict) and b.get("type") == "text" for b in (contenu or [])
            )
            if vrai_message:
                break
        elif e.get("type") == "assistant" and isinstance(contenu, list):
            textes += [b.get("text", "") for b in contenu if isinstance(b, dict) and b.get("type") == "text"]
    return "\n".join(reversed(textes))


def mode_stop(data: dict) -> int:
    fautes = lignes_fautives(derniere_reponse(data.get("transcript_path", "")))
    if fautes:
        print(
            CONSIGNE + "\nTa dernière réponse en contient. Réécris-la intégralement sans ce caractère.\n"
            "Occurrences :\n" + "\n".join(fautes),
            file=sys.stderr,
        )
        return 2
    return 0


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    return mode_stop(data) if mode == "stop" else mode_pre(data)


if __name__ == "__main__":
    sys.exit(main())
