"""Localisation des dossiers du dépôt."""

from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """Remonte jusqu'à la racine du dépôt (dossier contenant schemas/ et pnpm-workspace.yaml)."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "schemas").is_dir() and (candidate / "pnpm-workspace.yaml").is_file():
            return candidate
    raise FileNotFoundError("Racine du dépôt introuvable (schemas/ + pnpm-workspace.yaml).")


def schemas_dir() -> Path:
    return repo_root() / "schemas"


def elections_dir() -> Path:
    return repo_root() / "data" / "elections"
