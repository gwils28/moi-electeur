"""Génération des modèles Pydantic depuis schemas/ (source unique des types)."""

from __future__ import annotations

import filecmp
import shutil
import subprocess
import tempfile
from pathlib import Path

from .paths import schemas_dir

GENERATED = Path(__file__).parent / "generated"
IGNORED = ["__pycache__", ".ruff_cache"]


def _generate(target: Path) -> None:
    subprocess.run(
        [
            "datamodel-codegen",
            "--input",
            str(schemas_dir()),
            "--input-file-type",
            "jsonschema",
            "--output",
            str(target),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.12",
            "--use-standard-collections",
            "--use-union-operator",
            "--use-title-as-name",
            "--extra-fields",
            "forbid",
            "--disable-timestamp",
            "--formatters",
            "ruff-format",
        ],
        check=True,
    )


def _same_tree(a: Path, b: Path) -> bool:
    cmp = filecmp.dircmp(a, b, ignore=IGNORED)
    if cmp.left_only or cmp.right_only:
        return False
    _, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    if mismatch or errors:
        return False
    return all(_same_tree(a / d, b / d) for d in cmp.common_dirs)


def generate_models(check: bool = False) -> bool:
    """Génère les modèles ; en mode check, renvoie False si le dossier commité a dérivé."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "generated"
        _generate(target)
        if check:
            return GENERATED.is_dir() and _same_tree(target, GENERATED)
        if GENERATED.exists():
            shutil.rmtree(GENERATED)
        shutil.copytree(target, GENERATED, ignore=shutil.ignore_patterns(*IGNORED))
        return True
