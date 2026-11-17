"""Chaque notebook R&D s'exécute de bout en bout (PLAN § 1 bis)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

NOTEBOOKS = sorted(p for p in Path(__file__).resolve().parent.parent.glob("m*-*.py") if p.is_file())


def test_au_moins_un_notebook() -> None:
    assert NOTEBOOKS


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_s_execute(notebook: Path) -> None:
    env = {**os.environ, "MPLBACKEND": "Agg"}
    result = subprocess.run(
        [sys.executable, str(notebook)], capture_output=True, text=True, env=env, timeout=300
    )
    assert result.returncode == 0, result.stderr[-3000:]


def test_gabarit_s_execute() -> None:
    template = Path(__file__).resolve().parent.parent / "_template.py"
    result = subprocess.run([sys.executable, str(template)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-3000:]
