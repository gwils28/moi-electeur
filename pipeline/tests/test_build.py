"""Tests de l'ACP (fixture partagée avec le moteur TS) et de `pipeline build`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from moi_electeur_pipeline.build import BuildError, build_election
from moi_electeur_pipeline.paths import elections_dir, repo_root
from moi_electeur_pipeline.pca import fit_pca, project_b

TOY = json.loads(
    (repo_root() / "schemas" / "fixtures" / "pca_toy.json").read_text(encoding="utf-8")
)


def test_acp_retrouve_le_modele_de_la_fixture() -> None:
    model = fit_pca("fixture", TOY["statements"], TOY["candidates"])
    expected = TOY["model"]
    for key in ("mean", "components", "explained_variance_ratio", "scale"):
        np.testing.assert_allclose(model[key], expected[key], atol=1e-9)
    assert model["top_statements"][0][0] == "s1"


@pytest.mark.parametrize("case", TOY["expected"])
def test_projection_b_reference(case: dict[str, Any]) -> None:
    x, y, clamped = project_b(case["values"], TOY["model"])
    assert x == pytest.approx(case["x"]) and y == pytest.approx(case["y"])
    assert clamped is case["clamped"]


def test_signe_oriente_sur_le_mode_a() -> None:
    # Mêmes positions, sens de toutes les affirmations inversés : c1 passe à -10 en mode A,
    # la composante 1 doit donc le placer du côté négatif (D3), alors que la SVD seule
    # donnerait le même signe dans les deux cas.
    statements = [{**s, "direction": -s["direction"]} for s in TOY["statements"]]
    model = fit_pca("fixture", statements, TOY["candidates"])
    x_c1, _, _ = project_b(TOY["candidates"]["c1"], model)
    assert x_c1 == pytest.approx(-9)


def test_signe_oriente_sur_le_mode_a_axe_y() -> None:
    statements = [
        {**s, "direction": -s["direction"] if s["axis"] == "y" else s["direction"]}
        for s in TOY["statements"]
    ]
    model = fit_pca("fixture", statements, TOY["candidates"])
    _, y_c3, _ = project_b(TOY["candidates"]["c3"], model)
    x_c1, _, _ = project_b(TOY["candidates"]["c1"], model)
    assert y_c3 == pytest.approx(-9)  # c3 passe en bas en mode A
    assert x_c1 == pytest.approx(9)  # l'axe x n'est pas touché


def test_echelle_max_candidat_9_sur_chaque_composante() -> None:
    demo = json.loads((elections_dir() / "demo-fictive" / "positions.json").read_text())
    statements = json.loads((elections_dir() / "demo-fictive" / "statements.json").read_text())[
        "statements"
    ]
    ids = [s["id"] for s in statements]
    from moi_electeur_pipeline.engine_ref import candidate_answers

    cands = {
        c: candidate_answers(demo["positions"], c, ids)
        for c in {p["candidate_id"] for p in demo["positions"]}
    }
    model = fit_pca("demo-fictive", statements, cands)
    coords = np.array([project_b(a, model)[:2] for a in cands.values()])
    np.testing.assert_allclose(np.abs(coords).max(axis=0), [9, 9], atol=1e-9)


def test_moins_de_trois_candidats_refuse() -> None:
    with pytest.raises(ValueError, match="3 candidats"):
        fit_pca("x", TOY["statements"], {"a": {}, "b": {}})


def test_build_demo(tmp_path: Path) -> None:
    target = build_election(elections_dir() / "demo-fictive", tmp_path)
    names = sorted(p.name for p in target.iterdir())
    assert names == sorted(
        [
            "election_config.json",
            "statements.json",
            "positions.json",
            "measures.json",
            "pca_model.json",
            "manifest.json",
        ]
    )
    positions = json.loads((target / "positions.json").read_text())["positions"]
    assert {p["review"]["status"] for p in positions} <= {"validated", "corrected"}
    assert len(positions) == 6 * 30 - 2  # les 2 rejetées sont exclues
    model = json.loads((target / "pca_model.json").read_text())
    assert len(model["statement_ids"]) == 30
    manifest = json.loads((target / "manifest.json").read_text())
    assert len(manifest["files"]) == 5


def test_build_refuse_des_donnees_invalides(tmp_path: Path) -> None:
    bad = tmp_path / "demo-fictive"
    bad.mkdir()
    (bad / "election_config.json").write_text("{}")
    with pytest.raises(BuildError):
        build_election(bad, tmp_path / "out")
