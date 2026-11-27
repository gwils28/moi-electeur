"""CLI du pipeline : `uv run pipeline --help`."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from .build import BuildError, build_election
from .chunk import ChunkError, chunk_corpus
from .codegen import generate_models
from .demo import ELECTION_ID, build_demo, write_demo
from .engine_fixtures import build_engine_cases
from .extract import ExtractError, extract_corpus
from .index import IndexingError, index_corpus
from .llm import AnthropicClient, LlmClient, load_api_key
from .paths import elections_dir, repo_root
from .propose import (
    PROMPTS,
    collect_batches,
    done_ids,
    estimate_cost,
    load_prompt,
    load_records,
    measure_items,
    open_retriever,
    pending_ids,
    position_items,
    proposals_path,
    run_direct,
    submit_batch,
    write_measures,
    write_positions,
)
from .sources import SourceError, add_source, fetch_corpus
from .validate import validate_election


def make_client() -> LlmClient:
    return AnthropicClient()


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


for _name, _milestone in [("review", "M3")]:
    _not_implemented(_name, _milestone)


# Extraction (M3b, PLAN § 5.2 et D32). Aucune requête sans --yes ; plafond de coût ; reprise.

Candidates = Annotated[
    str | None, typer.Option(help="Candidats séparés par des virgules (défaut : tous).")
]
Pilot = Annotated[
    bool, typer.Option(help="Appels directs (pilote, D28) au lieu de la Batch API (-50 %).")
]
DryRun = Annotated[bool, typer.Option(help="Affiche le nombre de requêtes et le coût estimé.")]
Yes = Annotated[bool, typer.Option("--yes", help="Confirme l'envoi des requêtes payantes.")]
MaxUsd = Annotated[float, typer.Option(help="Refuse l'envoi si le coût estimé dépasse ce plafond.")]
Embedding = Annotated[str, typer.Option(help="Modèle d'embedding de la recherche.")]
Dsn = Annotated[str | None, typer.Option(help="Base PostgreSQL (défaut : DATABASE_URL).")]


def _split(value: str | None) -> list[str] | None:
    return [v.strip() for v in value.split(",") if v.strip()] if value else None


def _write_outputs(election: Path) -> None:
    """Écrit positions.json puis measures.json dès que toutes les propositions sont là."""
    config = json.loads((election / "election_config.json").read_text(encoding="utf-8"))
    statements = json.loads((election / "statements.json").read_text(encoding="utf-8"))
    positions = load_records(proposals_path(election, "position"))
    if positions:
        written, missing = write_positions(election, config, statements["statements"], positions)
        if written:
            typer.echo("positions.json écrit (statut pending, à revoir).")
        else:
            typer.echo(f"positions.json non écrit : {missing} proposition(s) manquent.")
    measures = load_records(proposals_path(election, "measure"))
    if measures:
        written, missing = write_measures(election, config, measures)
        if written:
            typer.echo("measures.json écrit (statut pending, à revoir).")
        elif missing:
            typer.echo(f"measures.json non écrit : {missing} proposition(s) manquent.")
        else:
            typer.echo("measures.json non écrit : positions.json d'abord.")


def _summary(records: list[dict[str, Any]]) -> str:
    counts = Counter(r["status"] for r in records)
    flags = Counter(f for r in records for f in r["flags"])
    cost = sum(r["cost_usd"] for r in records)
    parts = [f"{counts[s]} {s}" for s in ("ok", "invalid", "error") if counts[s]]
    detail = ", ".join(f"{f} {n}" for f, n in sorted(flags.items()))
    return f"{', '.join(parts)} ; coût réel {cost:.3f} $" + (
        f" ; signalements : {detail}" if detail else ""
    )


def _propose(
    kind: str,
    election: Path,
    *,
    candidates: str | None,
    pilot: bool,
    dry_run: bool,
    yes: bool,
    max_usd: float,
    embedding: str,
    dsn: str | None,
) -> None:
    config = json.loads((election / "election_config.json").read_text(encoding="utf-8"))
    prompt = load_prompt(PROMPTS[kind])
    skip = done_ids(load_records(proposals_path(election, kind))) | pending_ids(election)
    wanted = _split(candidates)
    with open_retriever(config["id"], embedding, dsn) as search:
        try:
            if kind == "position":
                statements = json.loads((election / "statements.json").read_text(encoding="utf-8"))
                items = position_items(
                    config,
                    statements["statements"],
                    search,
                    prompt=prompt,
                    candidates=wanted,
                    done=skip,
                )
            else:
                items = measure_items(config, search, prompt=prompt, candidates=wanted, done=skip)
        except ValueError as exc:
            typer.echo(f"Erreur : {exc}", err=True)
            raise typer.Exit(1) from exc
    if not items:
        typer.echo("Rien à demander : toutes les propositions sont acquises ou en cours de lot.")
        _write_outputs(election)
        return
    cost = estimate_cost(items, batch=not pilot)
    how = "appels directs" if pilot else "Batch API, -50 %"
    typer.echo(
        f"{len(items)} requêtes, coût estimé {cost:.2f} $ ({how}, prompt v{prompt.version})."
    )
    if dry_run:
        return
    if cost > max_usd:
        typer.echo(f"Refusé : coût estimé au-delà du plafond de {max_usd:.2f} $ (--max-usd).")
        raise typer.Exit(1)
    if not yes:
        typer.echo("Aucune requête envoyée : relancer avec --yes pour confirmer.")
        raise typer.Exit(1)
    if not load_api_key():
        typer.echo("ANTHROPIC_API_KEY absente (environnement ou .env à la racine).", err=True)
        raise typer.Exit(1)
    client = make_client()
    now = datetime.now(UTC)
    if pilot:
        records = run_direct(
            client, items, election_dir=election, kind=kind, prompt_version=prompt.version, now=now
        )
        typer.echo(_summary(records))
        _write_outputs(election)
    else:
        batch_id = submit_batch(
            client, items, election_dir=election, kind=kind, prompt_version=prompt.version, now=now
        )
        typer.echo(
            f"Lot {batch_id} envoyé ; suivre avec `uv run pipeline batch-status {election}`."
        )


@app.command("propose-positions")
def propose_positions_cmd(
    election: ElectionDir,
    candidates: Candidates = None,
    pilot: Pilot = False,
    dry_run: DryRun = False,
    yes: Yes = False,
    max_usd: MaxUsd = 10.0,
    embedding: Embedding = "bge-m3",
    dsn: Dsn = None,
) -> None:
    """Propose les positions (candidat x affirmation) par Claude, en extraction aveugle."""
    _propose(
        "position",
        election,
        candidates=candidates,
        pilot=pilot,
        dry_run=dry_run,
        yes=yes,
        max_usd=max_usd,
        embedding=embedding,
        dsn=dsn,
    )


@app.command("propose-measures")
def propose_measures_cmd(
    election: ElectionDir,
    candidates: Candidates = None,
    pilot: Pilot = False,
    dry_run: DryRun = False,
    yes: Yes = False,
    max_usd: MaxUsd = 10.0,
    embedding: Embedding = "bge-m3",
    dsn: Dsn = None,
) -> None:
    """Propose les mesures phares (candidat x thème) et leur chiffrage par Claude."""
    _propose(
        "measure",
        election,
        candidates=candidates,
        pilot=pilot,
        dry_run=dry_run,
        yes=yes,
        max_usd=max_usd,
        embedding=embedding,
        dsn=dsn,
    )


@app.command("batch-status")
def batch_status_cmd(election: ElectionDir) -> None:
    """État des lots envoyés ; collecte ceux qui sont terminés, puis écrit les fichiers."""
    if not pending_ids(election):
        typer.echo("Aucun lot en cours.")
        _write_outputs(election)
        return
    if not load_api_key():
        typer.echo("ANTHROPIC_API_KEY absente (environnement ou .env à la racine).", err=True)
        raise typer.Exit(1)
    for batch_id, status, n in collect_batches(make_client(), election, now=datetime.now(UTC)):
        typer.echo(f"{batch_id} : {status}" + (f", {n} propositions collectées" if n else ""))
    _write_outputs(election)
