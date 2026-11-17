"""CLI du pipeline : `uv run pipeline --help`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .codegen import generate_models
from .demo import ELECTION_ID, build_demo, write_demo
from .paths import elections_dir
from .validate import validate_election

app = typer.Typer(no_args_is_help=True, help="Pipeline hors ligne de Moi Électeur.")


@app.command()
def validate(
    dirs: Annotated[list[Path] | None, typer.Argument(help="Dossiers d'élection.")] = None,
) -> None:
    """Valide les données (schémas + contrôles croisés). Par défaut : toutes les élections."""
    targets = dirs or sorted(p for p in elections_dir().iterdir() if p.is_dir())
    failed = False
    for d in targets:
        issues = validate_election(d)
        if issues:
            failed = True
            typer.echo(f"ÉCHEC {d.name} ({len(issues)} problème(s))")
            for issue in issues:
                typer.echo(f"  - {issue}")
        else:
            typer.echo(f"OK {d.name}")
    raise typer.Exit(1 if failed else 0)


@app.command("gen-models")
def gen_models(
    check: Annotated[bool, typer.Option(help="Échoue si les modèles commités ont dérivé.")] = False,
) -> None:
    """Génère les modèles Pydantic depuis schemas/."""
    ok = generate_models(check=check)
    if check and not ok:
        typer.echo(
            "Modèles Pydantic désynchronisés des schémas : lancer `uv run pipeline gen-models`."
        )
        raise typer.Exit(1)
    typer.echo("Modèles Pydantic à jour." if check else "Modèles Pydantic générés.")


@app.command("make-demo")
def make_demo(
    check: Annotated[bool, typer.Option(help="Échoue si les fichiers commités diffèrent.")] = False,
) -> None:
    """(Re)génère les données fictives data/elections/demo-fictive (déterministe)."""
    target = elections_dir() / ELECTION_ID
    if check:
        stale = [
            name
            for name, doc in build_demo().items()
            if not (target / name).is_file()
            or json.loads((target / name).read_text(encoding="utf-8")) != doc
        ]
        if stale:
            typer.echo(f"Données de démo désynchronisées : {', '.join(stale)}")
            raise typer.Exit(1)
        typer.echo("Données de démo à jour.")
        return
    for path in write_demo(target):
        typer.echo(f"Écrit {path}")


def _not_implemented(name: str, milestone: str) -> None:
    def command() -> None:
        typer.echo(f"`{name}` : non implémenté (jalon {milestone}).", err=True)
        raise typer.Exit(2)

    command.__doc__ = f"Non implémenté (jalon {milestone})."
    app.command(name)(command)


for _name, _milestone in [
    ("fetch", "M2"),
    ("extract", "M2"),
    ("chunk", "M2"),
    ("index", "M2"),
    ("propose-positions", "M3"),
    ("propose-measures", "M3"),
    ("review", "M3"),
    ("build", "M1"),
]:
    _not_implemented(_name, _milestone)
