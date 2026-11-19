"""Validation des données d'une élection : JSON Schema puis contrôles croisés.

Les contrôles croisés couvrent ce que JSON Schema n'exprime pas (PLAN § 2.3) : références,
couverture des affirmations, unicité, alias du mode aveugle.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .paths import schemas_dir

MIN_PER_THEME = 4
MIN_PER_AXIS = 10
LOADED_STATUSES = {"validated", "corrected"}

# Fichier de données -> (schéma, obligatoire pour la boussole).
FILES: dict[str, tuple[str, bool]] = {
    "election_config.json": ("election_config.schema.json", True),
    "statements.json": ("statements.schema.json", True),
    "positions.json": ("positions.schema.json", True),
    "measures.json": ("measures.schema.json", False),
}
# PLAN D13 : sans aucun de ces fichiers, l'élection est « corpus seul » (pas de boussole).
COMPASS_FILES = ("statements.json", "positions.json", "measures.json")


@dataclass(frozen=True)
class Issue:
    file: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}: {self.message}"


def load_registry(directory: Path | None = None) -> tuple[Registry[Any], dict[str, Any]]:
    """Charge tous les schémas, indexés par leur $id (les $ref relatifs se résolvent dessus)."""
    directory = directory or schemas_dir()
    schemas: dict[str, Any] = {}
    resources: list[tuple[str, Resource[Any]]] = []
    for path in sorted(directory.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schemas[path.name] = schema
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources), schemas


def schema_issues(data: Any, schema_name: str, file: str) -> list[Issue]:
    registry, schemas = load_registry()
    validator = Draft202012Validator(
        schemas[schema_name],
        registry=registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    return [
        Issue(file, f"{'/'.join(map(str, err.absolute_path)) or '<racine>'}: {err.message}")
        for err in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.path)))
    ]


def local_path_issue(local_path: str) -> str | None:
    """Un document du corpus doit rester sous `sources/` du dossier d'élection (ignoré par git)."""
    path = Path(local_path)
    if path.is_absolute() or path.parts[:1] != ("sources",) or ".." in path.parts:
        return f"chemin local hors de sources/ : {local_path}"
    return None


def _duplicates(values: list[str]) -> list[str]:
    return sorted(v for v, n in Counter(values).items() if n > 1)


def cross_issues(election_dir: Path, docs: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    config = docs["election_config.json"]
    compass = "statements.json" in docs
    statements = docs["statements.json"]["statements"] if compass else []
    positions = docs["positions.json"]["positions"] if compass else []
    measures = docs.get("measures.json", {"measures": []})["measures"]

    def add(file: str, message: str) -> None:
        issues.append(Issue(file, message))

    if config["id"] != election_dir.name:
        add(
            "election_config.json",
            f"id '{config['id']}' différent du dossier '{election_dir.name}'",
        )
    for name, doc in docs.items():
        if name != "election_config.json" and doc.get("election_id") != config["id"]:
            add(name, f"election_id '{doc.get('election_id')}' différent de '{config['id']}'")

    theme_ids = [t["id"] for t in config["themes"]]
    cand_ids = [c["id"] for c in config["candidates"]]
    stmt_ids = [s["id"] for s in statements]
    for label, values, file in [
        ("thème", theme_ids, "election_config.json"),
        ("candidat", cand_ids, "election_config.json"),
        ("alias aveugle", [c["blind_alias"] for c in config["candidates"]], "election_config.json"),
        ("affirmation", stmt_ids, "statements.json"),
        ("mesure", [m["id"] for m in measures], "measures.json"),
    ]:
        for dup in _duplicates(values):
            add(file, f"{label} en double : {dup}")

    for c in config["candidates"]:
        alias = c["blind_alias"].casefold()
        name_words = [w for w in c["name"].replace("-", " ").split() if len(w) >= 3]
        for revealing in (c["name"], c["party"], *name_words):
            if revealing and revealing.casefold() in alias:
                add("election_config.json", f"l'alias de {c['id']} révèle '{revealing}'")

    for doc in config["corpus"]:
        if doc["candidate_id"] not in cand_ids:
            add("election_config.json", f"corpus : candidat inconnu {doc['candidate_id']}")
        problem = local_path_issue(doc["local_path"])
        if problem:
            add("election_config.json", f"corpus : {problem}")
    for label, key in [("URL", "source_url"), ("sha256", "sha256"), ("chemin local", "local_path")]:
        for dup in _duplicates([d[key] for d in config["corpus"]]):
            add("election_config.json", f"corpus : {label} en double : {dup}")

    if not compass:
        return issues

    # Couverture des affirmations (SPEC § 4.2).
    for s in statements:
        if s["theme"] not in theme_ids:
            add("statements.json", f"{s['id']} : thème inconnu {s['theme']}")
    per_theme = Counter(s["theme"] for s in statements)
    for theme in theme_ids:
        if per_theme[theme] < MIN_PER_THEME:
            add(
                "statements.json",
                f"thème {theme} : {per_theme[theme]} affirmations (< {MIN_PER_THEME})",
            )
    for axis in ("x", "y"):
        on_axis = [s for s in statements if s["axis"] == axis]
        if len(on_axis) < MIN_PER_AXIS:
            add("statements.json", f"axe {axis} : {len(on_axis)} affirmations (< {MIN_PER_AXIS})")
        if len({s["direction"] for s in on_axis}) < 2:
            add("statements.json", f"axe {axis} : sens non alternés (biais d'acquiescement)")

    corpus_titles: dict[str, set[str]] = {}
    for doc in config["corpus"]:
        corpus_titles.setdefault(doc["candidate_id"], set()).add(doc["document_title"])

    # Positions : références, unicité et complétude des couples, justification.
    pairs = Counter((p["candidate_id"], p["statement_id"]) for p in positions)
    for p in positions:
        ref = f"{p['candidate_id']}/{p['statement_id']}"
        if p["candidate_id"] not in cand_ids:
            add("positions.json", f"{ref} : candidat inconnu")
        if p["statement_id"] not in stmt_ids:
            add("positions.json", f"{ref} : affirmation inconnue")
        if (
            p["review"]["status"] in LOADED_STATUSES
            and p["value"] is not None
            and not p["evidence"]
        ):
            add("positions.json", f"{ref} : position retenue sans citation")
        # Hors démo fictive, une citation doit renvoyer à un document du corpus du candidat.
        if not config.get("fictional") and p["review"]["status"] in LOADED_STATUSES:
            for ev in p["evidence"]:
                if ev["document_title"] not in corpus_titles.get(p["candidate_id"], set()):
                    add(
                        "positions.json",
                        f"{ref} : document cité hors corpus ({ev['document_title']})",
                    )
    for (cand, stmt), n in pairs.items():
        if n > 1:
            add("positions.json", f"{cand}/{stmt} : {n} positions pour le même couple")
    for cand in cand_ids:
        for stmt in stmt_ids:
            if (cand, stmt) not in pairs:
                add("positions.json", f"{cand}/{stmt} : position manquante")

    for m in measures:
        if m["candidate_id"] not in cand_ids:
            add("measures.json", f"{m['id']} : candidat inconnu {m['candidate_id']}")
        if m["theme"] not in theme_ids:
            add("measures.json", f"{m['id']} : thème inconnu {m['theme']}")
        if m["review"]["status"] in LOADED_STATUSES and not m["evidence"]:
            add("measures.json", f"{m['id']} : mesure retenue sans citation")
    return issues


def validate_election(election_dir: Path) -> list[Issue]:
    """Renvoie la liste des problèmes (vide si les données sont valides)."""
    issues: list[Issue] = []
    docs: dict[str, Any] = {}
    corpus_only = not any((election_dir / f).is_file() for f in COMPASS_FILES)
    for file, (schema_name, required) in FILES.items():
        path = election_dir / file
        if not path.is_file():
            if required and not (corpus_only and file in COMPASS_FILES):
                issues.append(Issue(file, "fichier manquant"))
            continue
        try:
            docs[file] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(Issue(file, f"JSON invalide : {exc}"))
            continue
        issues += schema_issues(docs[file], schema_name, file)
    # Les contrôles croisés supposent des documents conformes à leur schéma.
    if issues:
        return issues
    return cross_issues(election_dir, docs)
