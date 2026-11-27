from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from moi_electeur_rag.testing import DatabaseUnavailable, temporary_database


@pytest.fixture(scope="session")
def db_dsn() -> Iterator[str]:
    try:
        with temporary_database() as dsn:
            yield dsn
    except DatabaseUnavailable as exc:
        if os.environ.get("CI"):
            raise
        pytest.skip(f"PostgreSQL injoignable ({exc}) : `docker compose up -d db`")
