"""Rapport du backtest (PLAN D45) : reproductible depuis les mesures versionnées."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moi_electeur_eval.backtest import render

ROOT = Path(__file__).resolve().parents[2]
RESULTS = sorted((ROOT / "eval" / "results").glob("????-??-??.json"))


@pytest.mark.parametrize("results", RESULTS, ids=lambda p: p.stem)
def test_rapport_commite_regenere_a_l_identique(results: Path) -> None:
    data = json.loads(results.read_text(encoding="utf-8"))
    decisions = results.with_name(f"{results.stem}-decisions.md")
    text = render(data, decisions.read_text(encoding="utf-8") if decisions.is_file() else None)
    report = ROOT / "eval" / "reports" / f"{results.stem}.md"
    assert report.read_text(encoding="utf-8") == text + "\n"
    assert "## 1. Recherche" in text and "## 6. Coût" in text
