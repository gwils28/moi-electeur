"""CLI `moi-electeur-eval` (PLAN § 4.7) : jeu de fumée, rappel@k, fixtures des notebooks M2.

    uv run --project eval moi-electeur-eval check-smoke
    uv run --project eval moi-electeur-eval retrieval   # base indexée + poids dans models/
    uv run --project eval moi-electeur-eval report --k 4
    uv run --project eval moi-electeur-eval corpus-stats

Aucun appel à un modèle de langue ; les questions ne sont jamais journalisées.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .smoke import corpus_issues, default_questions_path, load_questions

ROOT = Path(__file__).resolve().parents[3]
ELECTION = "fr-presidentielle-2022"
FIXTURES = ROOT / "notebooks" / "fixtures"
RETRIEVAL_FIXTURE = FIXTURES / "m2-retrieval-smoke.json"
CORPUS_FIXTURE = FIXTURES / "m2-corpus-stats.json"
MODELS = ("bge-m3", "multilingual-e5-large")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _election_dir(election: str) -> Path:
    return ROOT / "data" / "elections" / election


def cmd_check_smoke(args: argparse.Namespace) -> int:
    questions = load_questions(args.questions)
    print(f"{len(questions)} questions, format valide.")
    chunks_path = _election_dir(args.election) / "sources" / "chunks.jsonl"
    if not chunks_path.exists():
        print(f"{chunks_path} absent : contrôle contre le corpus ignoré.")
        return 0
    from .corpus_stats import read_chunks

    issues = corpus_issues(questions, read_chunks(chunks_path))
    for issue in issues:
        print("  " + issue)
    if issues:
        return 1
    print("Attendus cohérents avec le corpus (extraits, candidats, pages, titres).")
    return 0


def cmd_retrieval(args: argparse.Namespace) -> int:
    from moi_electeur_rag.db import connect
    from moi_electeur_rag.embedding import get_embedder

    from .collect import collect
    from .report import format_per_question, format_table, reports, write_fixture

    questions = load_questions(args.questions)
    models: dict[str, Any] = {}
    with connect() as conn:
        for name in args.models:
            models[name] = collect(
                conn,
                get_embedder(name),
                election_id=args.election,
                questions=questions,
                keep=args.keep,
            )
    versions = {m["corpus_version"] for m in models.values()}
    if len(versions) != 1:
        print(f"Versions de corpus différentes selon le modèle : {sorted(versions)}")
        return 1
    fixture = {
        "description": (
            "Classements du jeu de fumée (eval/smoke) par modèle et par méthode : les "
            "premiers extraits par candidat, donnés par leur indice dans `chunk_ids` "
            "(décodage : moi_electeur_eval.report.load_fixture). Produit par "
            "`uv run --project eval moi-electeur-eval retrieval` (base indexée et poids requis)."
        ),
        "election_id": args.election,
        "corpus_version": versions.pop(),
        "questions_file": Path(args.questions).resolve().relative_to(ROOT).as_posix(),
        "models": models,
    }
    write_fixture(args.out, fixture)
    results = reports(fixture, questions, k=args.k)
    print(format_table(results))
    print()
    print(format_per_question(results))
    print(f"\nFixture écrite : {args.out}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from .report import format_per_question, format_table, load_fixture, reports

    questions = load_questions(args.questions)
    results = reports(load_fixture(args.fixture), questions, k=args.k)
    print(format_table(results))
    print()
    print(format_per_question(results))
    for (model, method), r in results.items():
        for q in r.questions:
            if q.missed or q.uncovered:
                print(
                    f"{model} / {method} / {q.question_id} : sans extrait pertinent "
                    f"{q.missed or '-'} ; sans aucun extrait {q.uncovered or '-'}"
                )
    return 0


def cmd_corpus_stats(args: argparse.Namespace) -> int:
    from .corpus_stats import corpus_stats_from_dir

    stats = corpus_stats_from_dir(_election_dir(args.election))
    _write_json(args.out, stats)
    print(f"{stats['n_documents']} documents, {stats['n_extraits']} extraits ; écrit : {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="moi-electeur-eval", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--questions", type=Path, default=default_questions_path())
        p.add_argument("--election", default=ELECTION)

    p = sub.add_parser(
        "check-smoke", help="valide le jeu de fumée (format, puis corpus si présent)"
    )
    common(p)
    p.set_defaults(func=cmd_check_smoke)

    p = sub.add_parser("retrieval", help="classements réels (base) -> fixture + rappel@k")
    common(p)
    p.add_argument("--models", nargs="+", default=list(MODELS))
    p.add_argument("--keep", type=int, default=6, help="extraits conservés par candidat")
    p.add_argument("--k", type=int, default=4)
    p.add_argument("--out", type=Path, default=RETRIEVAL_FIXTURE)
    p.set_defaults(func=cmd_retrieval)

    p = sub.add_parser("report", help="rappel@k depuis la fixture (sans base)")
    common(p)
    p.add_argument("--k", type=int, default=4)
    p.add_argument("--fixture", type=Path, default=RETRIEVAL_FIXTURE)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser(
        "corpus-stats", help="statistiques d'extraction -> fixture du notebook m2-01"
    )
    common(p)
    p.add_argument("--out", type=Path, default=CORPUS_FIXTURE)
    p.set_defaults(func=cmd_corpus_stats)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    code: int = args.func(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
