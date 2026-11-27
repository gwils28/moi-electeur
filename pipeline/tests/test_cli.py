from __future__ import annotations

import pytest
from typer.testing import CliRunner

from moi_electeur_pipeline.cli import app
from moi_electeur_pipeline.demo import build_demo

runner = CliRunner()


def test_validate_toutes_les_elections() -> None:
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0, result.output
    assert "OK demo-fictive" in result.output


def test_demo_commitee_a_jour() -> None:
    result = runner.invoke(app, ["make-demo", "--check"])
    assert result.exit_code == 0, result.output


def test_demo_deterministe() -> None:
    assert build_demo() == build_demo()


def test_demo_contient_les_cas_particuliers() -> None:
    positions = build_demo()["positions.json"]["positions"]
    assert sum(p["value"] is None for p in positions) == 1
    assert sum(p["review"]["status"] == "rejected" for p in positions) == 2


def test_modeles_pydantic_a_jour() -> None:
    result = runner.invoke(app, ["gen-models", "--check"])
    assert result.exit_code == 0, result.output


def test_modeles_generes_chargent_la_demo() -> None:
    from moi_electeur_pipeline.generated.positions_schema import PositionsFile
    from moi_electeur_pipeline.generated.statements_schema import StatementsFile

    demo = build_demo()
    assert len(StatementsFile.model_validate(demo["statements.json"]).statements) == 30
    assert PositionsFile.model_validate(demo["positions.json"]).positions


def test_fixture_moteur_a_jour() -> None:
    result = runner.invoke(app, ["engine-fixtures", "--check"])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    "command", ["add-source", "fetch", "extract", "chunk", "db-migrate", "index"]
)
def test_commandes_ingestion_disponibles(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])
    assert result.exit_code == 0, result.output
