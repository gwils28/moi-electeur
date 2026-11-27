from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from moi_electeur_pipeline.demo import ELECTION_ID, build_demo


@pytest.fixture
def demo_docs() -> dict[str, Any]:
    return build_demo()


@pytest.fixture
def write_election(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Écrit des documents dans un dossier d'élection temporaire et renvoie son chemin."""

    def _write(docs: dict[str, Any], name: str = ELECTION_ID) -> Path:
        target = tmp_path / name
        target.mkdir(parents=True, exist_ok=True)
        for file, doc in docs.items():
            (target / file).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return target

    return _write


@pytest.fixture(scope="session")
def db_dsn():  # type: ignore[no-untyped-def]
    """Base éphémère (PLAN D19) : ignorée en local sans PostgreSQL, obligatoire en CI."""
    import os

    from moi_electeur_rag.testing import DatabaseUnavailable, temporary_database

    try:
        with temporary_database() as dsn:
            yield dsn
    except DatabaseUnavailable as exc:
        if os.environ.get("CI"):
            raise
        pytest.skip(f"PostgreSQL injoignable ({exc}) : `docker compose up -d db`")
