"""Codage manuel de référence et comparaison CHES (PLAN D42, SPEC § 9 « Positionnement »).

1. Un échantillon de positions est tiré au sort (stratifié par candidat, silences et valeurs
   mêlés) ; le mainteneur code chaque couple à partir des programmes, **sans voir la valeur
   proposée** (`eval/reference/codage-2022.csv`) ; l'accord se mesure ensuite.
2. Les coordonnées du mode A sont comparées aux scores des partis dans la Chapel Hill Expert
   Survey (lrecon pour l'axe économique, galtan pour l'axe société), par corrélation de rangs.
"""

from __future__ import annotations

import csv
import random
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .stats import spearman, weighted_kappa

SHEET_FIELDS = ["candidate_id", "candidate", "statement_id", "statement", "sources", "code", "note"]
CODES = {"-2": -2, "-1": -1, "0": 0, "1": 1, "2": 2, "silence": None}


def sample_positions(
    positions: Sequence[Mapping[str, Any]], *, per_candidate: int = 5, seed: int = 7
) -> list[dict[str, Any]]:
    """Tirage stratifié par candidat ; dans chaque strate, silences et valeurs alternés quand
    les deux existent (un échantillon sans silence ne mesurerait pas les faux silences)."""
    rng = random.Random(seed)
    out: list[dict[str, Any]] = []
    for cand in sorted({p["candidate_id"] for p in positions}):
        mine = sorted(
            (dict(p) for p in positions if p["candidate_id"] == cand),
            key=lambda p: p["statement_id"],
        )
        silent = [p for p in mine if p["value"] is None]
        valued = [p for p in mine if p["value"] is not None]
        rng.shuffle(silent)
        rng.shuffle(valued)
        picked: list[dict[str, Any]] = []
        while len(picked) < per_candidate and (silent or valued):
            source = valued if (len(picked) % 2 == 0 and valued) or not silent else silent
            picked.append(source.pop())
        out.extend(sorted(picked, key=lambda p: p["statement_id"]))
    return out


def write_sheet(
    path: Path,
    sample: Sequence[Mapping[str, Any]],
    statements: Sequence[Mapping[str, Any]],
    names: Mapping[str, str],
    *,
    sources: Mapping[str, Sequence[str]],
) -> None:
    """Feuille de codage : couple, affirmation et sources, sans la valeur proposée."""
    text = {s["id"]: s["text"] for s in statements}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_FIELDS)
        w.writeheader()
        for p in sample:
            w.writerow(
                {
                    "candidate_id": p["candidate_id"],
                    "candidate": names.get(p["candidate_id"], ""),
                    "statement_id": p["statement_id"],
                    "statement": text[p["statement_id"]],
                    "sources": " ".join(sources.get(p["candidate_id"], [])),
                    "code": "",
                    "note": "",
                }
            )


def read_sheet(path: Path) -> list[dict[str, Any]]:
    """Lignes codées (code renseigné) ; refuse un code hors de -2, -1, 0, 1, 2, silence."""
    out = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            code = (row.get("code") or "").strip().lower()
            if not code:
                continue
            if code not in CODES:
                raise ValueError(
                    f"code invalide {code!r} pour {row['candidate_id']}/{row['statement_id']}"
                )
            out.append({**row, "value": CODES[code]})
    return out


def agreement(
    coded: Sequence[Mapping[str, Any]], positions: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Accord entre la référence humaine et les positions publiées."""
    proposed = {(p["candidate_id"], p["statement_id"]): p["value"] for p in positions}
    pairs = [(r["value"], proposed[(r["candidate_id"], r["statement_id"])]) for r in coded]
    silence_same = sum(1 for h, m in pairs if (h is None) == (m is None))
    valued = [(h, m) for h, m in pairs if h is not None and m is not None]
    return {
        "n": len(pairs),
        "silence_agreement": silence_same / len(pairs) if pairs else None,
        "false_silence": sum(1 for h, m in pairs if h is not None and m is None),
        "invented_value": sum(1 for h, m in pairs if h is None and m is not None),
        "both_valued": len(valued),
        "exact": sum(1 for h, m in valued if h == m) / len(valued) if valued else None,
        "within_one": sum(1 for h, m in valued if abs(h - m) <= 1) / len(valued)
        if valued
        else None,
        "weighted_kappa": weighted_kappa([h for h, _ in valued], [m for _, m in valued])
        if len(valued) >= 2
        else None,
    }


def ches_correlation(
    coords: Mapping[str, tuple[float, float]],
    ches: Mapping[str, tuple[float, float]],
    mapping: Mapping[str, str],
) -> dict[str, Any]:
    """Spearman entre (x, y) du mode A et (lrecon, galtan) du parti de chaque candidat."""
    kept = [c for c in sorted(coords) if mapping.get(c) in ches]
    xs = [coords[c][0] for c in kept]
    ys = [coords[c][1] for c in kept]
    lrecon = [ches[mapping[c]][0] for c in kept]
    galtan = [ches[mapping[c]][1] for c in kept]
    return {
        "n": len(kept),
        "missing": [c for c in sorted(coords) if c not in kept],
        "spearman_x": spearman(xs, lrecon) if len(kept) >= 2 else None,
        "spearman_y": spearman(ys, galtan) if len(kept) >= 2 else None,
    }
