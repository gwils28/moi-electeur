"""CLI du pipeline : `uv run pipeline --help`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .build import BuildError, build_election
from .chunk import ChunkError, chunk_corpus
from .codegen import generate_models
from .demo import ELECTION_ID, build_demo, write_demo
from .engine_fixtures import build_engine_cases
from .extract import ExtractError, extract_corpus
from .index import IndexingError, index_corpus
from .paths import elections_dir, repo_root
from .sources import SourceError, add_source, fetch_corpus
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


@app.command()
def build(
    dirs: Annotated[list[Path] | None, typer.Argument(help="Dossiers d'élection.")] = None,
    out: Annotated[Path | None, typer.Option(help="Dossier de sortie.")] = None,
) -> None:
    """Génère les JSON statiques du front (positions/mesures validées uniquement, modèle ACP)."""
    out_root = out or repo_root() / "apps" / "web" / "public" / "data"
    targets = dirs or sorted(p for p in elections_dir().iterdir() if p.is_dir())
    for d in targets:
        try:
            written = build_election(d, out_root)
        except BuildError as exc:
            typer.echo(f"ÉCHEC {d.name} :\n{exc}", err=True)
            raise typer.Exit(1) from exc
        if (d / "statements.json").is_file():
            typer.echo(f"Écrit {written}")
        else:
            typer.echo(f"Écrit {written} (corpus seul : configuration seule, pas de boussole)")


ElectionDir = Annotated[Path, typer.Argument(help="Dossier d'élection (data/elections/<id>).")]


@app.command("add-source")
def add_source_cmd(
    election: ElectionDir,
    candidate: Annotated[str, typer.Argument(help="Identifiant du candidat.")],
    url: Annotated[str, typer.Argument(help="URL du document (instantané Wayback id_/).")],
    title: Annotated[str, typer.Option(help="Titre du document, tel que cité.")],
    doc_type: Annotated[str, typer.Option("--type", help="pdf, html ou markdown.")] = "pdf",
) -> None:
    """Télécharge un document, calcule son sha256 et l'ajoute au corpus (PLAN D12)."""
    try:
        entry = add_source(election, candidate, url, title, doc_type)
    except SourceError as exc:
        typer.echo(f"ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Ajouté {entry['local_path']} ({entry['sha256'][:12]})")


@app.command()
def fetch(election: ElectionDir) -> None:
    """Télécharge les documents manquants du corpus et vérifie leur sha256."""
    try:
        report = fetch_corpus(election)
    except SourceError as exc:
        typer.echo(f"ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"{len(report.present)} présent(s), {len(report.downloaded)} téléchargé(s), sha256 OK"
    )


@app.command()
def extract(election: ElectionDir) -> None:
    """Extrait le texte des documents, page par page (PDF, HTML, Markdown)."""
    try:
        report = extract_corpus(election)
    except ExtractError as exc:
        typer.echo(f"ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"{len(report.written)} document(s) extrait(s)")
    for title, pages in report.empty_pages.items():
        typer.echo(f"  pages sans texte (non indexées) dans « {title} » : {pages}")
    for title in report.excluded:
        typer.echo(f"  EXCLU (aucun texte, OCR non prévu) : « {title} »")


@app.command()
def chunk(election: ElectionDir) -> None:
    """Découpe les documents extraits en extraits de 300 à 600 tokens."""
    try:
        report = chunk_corpus(election)
    except ChunkError as exc:
        typer.echo(f"ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    total = sum(report.chunks_per_candidate.values())
    typer.echo(f"{total} extraits, version du corpus {report.corpus_version} -> {report.path}")
    for candidate, n in sorted(report.chunks_per_candidate.items()):
        typer.echo(f"  {candidate} : {n}")


@app.command("db-migrate")
def db_migrate() -> None:
    """Applique les migrations SQL du service RAG (base de DATABASE_URL)."""
    from moi_electeur_rag.db import migrate

    applied = migrate()
    typer.echo(f"Migrations appliquées : {', '.join(applied)}" if applied else "Base à jour.")


@app.command()
def index(
    election: ElectionDir,
    model: Annotated[
        str, typer.Option(help="bge-m3, multilingual-e5-large (ou fake pour les tests).")
    ] = "bge-m3",
    theme_margin: Annotated[
        float,
        typer.Option(help="Écart de similarité minimal entre les deux thèmes les plus proches."),
    ] = 0.02,
) -> None:
    """Calcule les vecteurs et les thèmes des extraits et les écrit dans PostgreSQL."""
    try:
        report = index_corpus(election, model=model, theme_margin=theme_margin)
    except IndexingError as exc:
        typer.echo(f"ÉCHEC : {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"{report.n_chunks} extraits indexés avec {report.model}, version {report.corpus_version}"
    )
    if report.replaced_version:
        typer.echo(
            f"  ATTENTION : remplace la version {report.replaced_version} ; "
            "les vecteurs des autres modèles ont été supprimés, à réindexer"
        )
    for theme, n in sorted(report.themes.items(), key=lambda kv: (kv[0] is None, kv[0] or "")):
        typer.echo(f"  {theme or 'sans thème (ambigu)'} : {n}")


@app.command("engine-fixtures")
def engine_fixtures(
    check: Annotated[bool, typer.Option(help="Échoue si la fixture commitée diffère.")] = False,
) -> None:
    """(Re)génère schemas/fixtures/engine_cases.json depuis la référence Python."""
    path = repo_root() / "schemas" / "fixtures" / "engine_cases.json"
    cases = build_engine_cases()
    if check:
        if not path.is_file() or json.loads(path.read_text(encoding="utf-8")) != cases:
            typer.echo("Fixture moteur désynchronisée : lancer `uv run pipeline engine-fixtures`.")
            raise typer.Exit(1)
        typer.echo("Fixture moteur à jour.")
        return
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    typer.echo(f"Écrit {path}")


def _not_implemented(name: str, milestone: str) -> None:
    def command() -> None:
        typer.echo(f"`{name}` : non implémenté (jalon {milestone}).", err=True)
        raise typer.Exit(2)

    command.__doc__ = f"Non implémenté (jalon {milestone})."
    app.command(name)(command)


for _name, _milestone in [
    ("propose-positions", "M3"),
    ("propose-measures", "M3"),
    ("review", "M3"),
]:
    _not_implemented(_name, _milestone)
