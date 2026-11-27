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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def cmd_judge_submit(args: argparse.Namespace) -> int:
    """Envoie le lot du juge (Batch API) après estimation ; état conservé pour la collecte."""
    from moi_electeur_pipeline.llm import AnthropicClient, cost_usd, load_api_key

    from .judge import judge_requests

    if args.state.exists():
        print(f"Lot déjà envoyé ({args.state}) : lancer judge-collect.")
        return 1
    requests = judge_requests(_read_jsonl(args.run))
    chars = sum(
        len(r["params"]["system"][0]["text"]) + len(r["params"]["messages"][0]["content"])
        for r in requests
    )
    usage = {"input_tokens": int(chars / 3), "output_tokens": 2500 * len(requests)}
    estimate = cost_usd(requests[0]["params"]["model"], usage, batch=True) if requests else 0.0
    print(f"{len(requests)} requêtes, coût estimé {estimate:.2f} $ (Batch API).")
    if args.dry_run:
        return 0
    if estimate > args.max_usd:
        print(f"Refusé : au-delà du plafond de {args.max_usd:.2f} $.")
        return 1
    if not args.yes:
        print("Aucune requête envoyée : relancer avec --yes.")
        return 1
    if not load_api_key():
        print("ANTHROPIC_API_KEY absente.")
        return 1
    batch_id = AnthropicClient().submit_batch(requests)
    _write_json(args.state, {"batch_id": batch_id, "run": str(args.run), "requests": len(requests)})
    print(f"Lot {batch_id} envoyé.")
    return 0


def cmd_judge_collect(args: argparse.Namespace) -> int:
    from moi_electeur_pipeline.llm import AnthropicClient, cost_usd, load_api_key

    from .judge import JUDGE_MODEL, parse_judgement

    state = json.loads(args.state.read_text(encoding="utf-8"))
    if not load_api_key():
        print("ANTHROPIC_API_KEY absente.")
        return 1
    client = AnthropicClient()
    status = client.batch_status(state["batch_id"])["status"]
    if status != "ended":
        print(f"Lot {state['batch_id']} : {status}.")
        return 2
    lines, total = [], 0.0
    for r in client.batch_results(state["batch_id"]):
        message = r["message"]
        usage = (message or {}).get("usage") or {}
        cost = cost_usd(
            JUDGE_MODEL,
            {k: int(v or 0) for k, v in usage.items() if isinstance(v, int)},
            batch=True,
        )
        total += cost
        lines.append(
            json.dumps(
                {
                    "custom_id": r["custom_id"],
                    "verdict": parse_judgement(message),
                    "cost_usd": cost,
                },
                ensure_ascii=False,
            )
        )
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} verdicts écrits dans {args.out}, coût réel {total:.3f} $.")
    return 0


def cmd_backtest_report(args: argparse.Namespace) -> int:
    from .backtest import build_report
    from .smoke import full_questions_path

    election = _election_dir(args.election)
    config = json.loads((election / "election_config.json").read_text(encoding="utf-8"))
    names = {c["id"]: c["name"] for c in config["candidates"]}
    date = args.run_dir.name
    text = build_report(
        date=date,
        questions=load_questions(full_questions_path()),
        names=names,
        retrieval_fixture=FIXTURES / "m4-retrieval-60.json",
        run_dir=args.run_dir,
        election=election,
        sheet=ROOT / "eval" / "reference" / "codage-2022.csv",
    )
    out = args.out or ROOT / "eval" / "reports" / f"{date}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"Rapport écrit : {out}")
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
    p = sub.add_parser("judge-submit", help="juge LLM des réponses du chat (Batch API, M4b)")
    p.add_argument("--run", type=Path, required=True, help="JSONL du banc d'essai")
    p.add_argument("--state", type=Path, required=True, help="fichier d'état du lot")
    p.add_argument("--max-usd", type=float, default=5.0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_judge_submit)

    p = sub.add_parser("backtest-report", help="rapport du backtest M4 (fichiers versionnés)")
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--election", default=ELECTION)
    p.add_argument("--out", type=Path, default=None)
    p.set_defaults(func=cmd_backtest_report)

    p = sub.add_parser("judge-collect", help="collecte les verdicts du juge")
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=cmd_judge_collect)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    code: int = args.func(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
