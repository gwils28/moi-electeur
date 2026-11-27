"""Codage manuel de référence et comparaison CHES (PLAN D42)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from moi_electeur_eval.reference import (
    SHEET_FIELDS,
    agreement,
    ches_correlation,
    read_sheet,
    sample_positions,
    write_sheet,
)

STATEMENTS = [{"id": f"s{i:02d}", "text": f"Affirmation {i}."} for i in range(1, 11)]


def positions() -> list[dict[str, object]]:
    out = []
    for c in ("a", "b", "c"):
        for i, s in enumerate(STATEMENTS):
            out.append(
                {
                    "candidate_id": c,
                    "statement_id": s["id"],
                    "value": None if i % 3 == 0 else (i % 5) - 2,
                    "review": {"status": "validated"},
                }
            )
    return out


def test_echantillon_stratifie_et_deterministe() -> None:
    sample = sample_positions(positions(), per_candidate=4, seed=7)
    assert sample == sample_positions(positions(), per_candidate=4, seed=7)
    assert len(sample) == 12
    assert {p["candidate_id"] for p in sample} == {"a", "b", "c"}
    # Silences et valeurs mêlés dans chaque strate.
    for c in ("a", "b", "c"):
        mine = [p for p in sample if p["candidate_id"] == c]
        assert any(p["value"] is None for p in mine) and any(p["value"] is not None for p in mine)


def test_feuille_sans_la_valeur_proposee(tmp_path: Path) -> None:
    sample = sample_positions(positions(), per_candidate=2, seed=7)
    path = tmp_path / "codage.csv"
    names = {"a": "Alice", "b": "Bruno", "c": "Chloé"}
    write_sheet(path, sample, STATEMENTS, names, sources={"a": ["https://a.fr/p.pdf"]})
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert list(rows[0]) == SHEET_FIELDS
    assert all(r["code"] == "" for r in rows)
    assert "value" not in rows[0] and "proposed" not in "".join(rows[0])
    assert read_sheet(path) == []  # rien de codé


def test_accord_avec_la_reference(tmp_path: Path) -> None:
    path = tmp_path / "codage.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_FIELDS)
        w.writeheader()
        for cand, sid, code in [
            ("a", "s02", "-1"),
            ("a", "s03", "1"),
            ("b", "s01", "silence"),
            ("b", "s02", "0"),
            ("c", "s05", "2"),
        ]:
            w.writerow(
                {
                    **dict.fromkeys(SHEET_FIELDS, ""),
                    "candidate_id": cand,
                    "statement_id": sid,
                    "code": code,
                }
            )
    coded = read_sheet(path)
    assert len(coded) == 5
    out = agreement(coded, positions())
    # Valeurs proposées : a/s02 = -1, a/s03 = 0, b/s01 = silence, b/s02 = -1, c/s05 = 2.
    assert out["n"] == 5
    assert out["silence_agreement"] == pytest.approx(1.0)
    assert out["both_valued"] == 4
    assert out["exact"] == pytest.approx(2 / 4)
    assert out["within_one"] == pytest.approx(1.0)
    assert -1 <= out["weighted_kappa"] <= 1


def test_code_invalide_refuse(tmp_path: Path) -> None:
    path = tmp_path / "codage.csv"
    path.write_text(
        ",".join(SHEET_FIELDS) + "\n" + ",".join(["a", "", "s01", "", "", "3", ""]) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="code"):
        read_sheet(path)


def test_correlation_ches() -> None:
    coords = {"a": (-8.0, -5.0), "b": (6.0, 7.0), "c": (2.0, 1.0), "d": (0.0, 0.0)}
    ches = {"A": (2.0, 3.0), "B": (8.0, 8.5), "C": (6.0, 5.0)}
    mapping = {"a": "A", "b": "B", "c": "C"}  # d : parti absent du CHES
    out = ches_correlation(coords, ches, mapping)
    assert out["n"] == 3 and out["missing"] == ["d"]
    assert out["spearman_x"] == pytest.approx(1.0)
    assert out["spearman_y"] == pytest.approx(1.0)
