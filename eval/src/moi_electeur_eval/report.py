"""Tableaux de rappel@k à partir de la fixture de classements (sans base ni modèle)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .recall import MethodReport, evaluate
from .smoke import Question

METHOD_LABELS = {
    "semantique": "sémantique seul",
    "plein_texte": "plein texte seul",
    "rrf": "RRF (servi)",
    "plein_texte_brut": "plein texte brut (M2b)",
    "rrf_brut": "RRF brut (M2b)",
}


def encode_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Remplace chaque identifiant d'extrait par son indice dans `chunk_ids` (fixture compacte)."""
    ids = sorted(
        {
            chunk_id
            for model in fixture["models"].values()
            for per_q in model["rankings"].values()
            for per_c in per_q.values()
            for ranked in per_c.values()
            for chunk_id in ranked
        }
    )
    index = {chunk_id: i for i, chunk_id in enumerate(ids)}
    out = {**fixture, "chunk_ids": ids, "models": {}}
    for name, model in fixture["models"].items():
        rankings = {
            method: {
                qid: {cand: [index[c] for c in ranked] for cand, ranked in per_c.items()}
                for qid, per_c in per_q.items()
            }
            for method, per_q in model["rankings"].items()
        }
        out["models"][name] = {**model, "rankings": rankings}
    return out


def decode_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    if "chunk_ids" not in fixture:
        return fixture
    ids = fixture["chunk_ids"]
    out = {k: v for k, v in fixture.items() if k != "chunk_ids"}
    out["models"] = {}
    for name, model in fixture["models"].items():
        rankings = {
            method: {
                qid: {cand: [ids[i] for i in ranked] for cand, ranked in per_c.items()}
                for qid, per_c in per_q.items()
            }
            for method, per_q in model["rankings"].items()
        }
        out["models"][name] = {**model, "rankings": rankings}
    return out


def write_fixture(path: Path, fixture: dict[str, Any]) -> None:
    """Fixture compacte : une ligne par clé de premier niveau, listes d'indices sans espaces."""
    encoded = encode_fixture(fixture)
    lines = [
        f"{json.dumps(key)}:{json.dumps(value, ensure_ascii=False, separators=(',', ':'))}"
        for key, value in encoded.items()
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")


def load_fixture(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return decode_fixture(data)


def reports(
    fixture: Mapping[str, Any], questions: Sequence[Question], k: int = 4
) -> dict[tuple[str, str], MethodReport]:
    out = {}
    for model, data in fixture["models"].items():
        if k > data["keep"]:
            raise ValueError(f"k = {k} dépasse les {data['keep']} extraits conservés par candidat")
        for method in METHOD_LABELS:
            if method not in data["rankings"]:
                continue
            out[(model, method)] = evaluate(
                questions, data["rankings"][method], data["candidates"], k=k
            )
    return out


def format_table(results: Mapping[tuple[str, str], MethodReport]) -> str:
    """Tableau Markdown : une ligne par (modèle, méthode)."""
    k = next(iter(results.values())).k
    lines = [
        f"| Modèle | Méthode | Rappel@{k} (macro) | Rappel@{k} (micro) | Succès@{k} | Couverture 12/12 |",
        "|---|---|---|---|---|---|",
    ]
    for (model, method), r in results.items():
        lines.append(
            f"| {model} | {METHOD_LABELS[method]} | {r.recall:.3f} | {r.recall_micro:.3f} "
            f"| {r.hit_rate:.3f} | {'oui' if r.full_coverage else 'non'} |"
        )
    return "\n".join(lines)


def format_per_question(results: Mapping[tuple[str, str], MethodReport]) -> str:
    keys = list(results)
    first = results[keys[0]]
    head = "| Question | " + " | ".join(f"{m} / {METHOD_LABELS[x]}" for m, x in keys) + " |"
    lines = [head, "|---|" + "---|" * len(keys)]
    for i, q in enumerate(first.questions):
        cells = []
        for key in keys:
            s = results[key].questions[i]
            cells.append("-" if s.recall is None else f"{s.recall:.2f}")
        lines.append(f"| {q.question_id} | " + " | ".join(cells) + " |")
    return "\n".join(lines)
