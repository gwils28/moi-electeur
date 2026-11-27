"""Rapport du backtest M4 (PLAN § 6, SPEC § 9) : `eval/reports/<date>.md`, reproductible.

    uv run --project eval moi-electeur-eval backtest-report --run-dir eval/runs/<date>

Assemble, à partir de fichiers versionnés uniquement (aucune base, aucun appel) :
recherche (fixture des 60 questions), chat (banc d'essai, juge, permutations), profils
synthétiques (calculés), codage de référence et CHES (quand ils sont fournis). Les décisions
écrites par l'agent ou le mainteneur sont reprises de `<run-dir>/decisions.md`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from moi_electeur_pipeline.engine_ref import candidate_answers, project_a

from .chat import summarize
from .judge import summarize_judgements
from .neutrality import permutation_effects
from .profiles import Noise, synthetic_profiles
from .recall import MethodReport
from .reference import agreement, read_sheet
from .report import load_fixture, reports
from .smoke import Question
from .stats import paired_bootstrap

MODE_LABEL = {"rapide": "rapide (Haiku 5.5)", "approfondi": "approfondi (Sonnet 5.5)"}


def _fmt(x: Any, digits: int = 3) -> str:
    if x is None:
        return "n/d"
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)


def _pct(x: float | None) -> str:
    return "n/d" if x is None else f"{100 * x:.1f} %"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def retrieval_results(fixture: Path, questions: Sequence[Question]) -> dict[str, Any]:
    results = reports(load_fixture(fixture), questions, k=4)
    table = [
        {
            "model": model,
            "method": method,
            "recall": r.recall,
            "hit_rate": r.hit_rate,
            "full_coverage": r.full_coverage,
        }
        for (model, method), r in results.items()
        if method in ("semantique", "plein_texte", "rrf")
    ]

    def per_q(r: MethodReport) -> dict[str, float]:
        return {q.question_id: q.recall for q in r.questions if q.recall is not None}

    gaps = {}
    for method in ("rrf", "semantique"):
        e = per_q(results[("multilingual-e5-large", method)])
        b = per_q(results[("bge-m3", method)])
        ids = sorted(set(e) & set(b))
        mean, lo, hi = paired_bootstrap([e[i] for i in ids], [b[i] for i in ids])
        gaps[method] = {"mean": mean, "lo": lo, "hi": hi, "n": len(ids)}
    return {"table": table, "gaps": gaps}


def retrieval_section(r: Mapping[str, Any]) -> list[str]:
    out = [
        "## 1. Recherche (60 questions, k = 4)",
        "",
        "| Modèle | Méthode | Rappel@4 (macro) | Succès@4 | Couverture 12/12 |",
        "|---|---|---|---|---|",
    ]
    for row in r["table"]:
        out.append(
            f"| {row['model']} | {row['method']} | {_fmt(row['recall'])} | "
            f"{_fmt(row['hit_rate'])} | {'oui' if row['full_coverage'] else 'non'} |"
        )
    out.append("")
    for method, g in r["gaps"].items():
        out.append(
            f"- Écart e5 − bge-m3, {method} : **{g['mean']:+.3f}** [{g['lo']:+.3f} ; "
            f"{g['hi']:+.3f}] (bootstrap apparié, {g['n']} questions, graine 7)."
        )
    return out


def chat_section(s: Mapping[str, Any], judge: Mapping[str, Any] | None) -> list[str]:
    modes = [m for m in ("rapide", "approfondi") if m in s]
    rows: list[tuple[str, Callable[[Mapping[str, Any]], str]]] = [
        ("Réponses (erreurs)", lambda v: f"{v['answers']} ({v['errors']})"),
        ("Réponses tronquées", lambda v: str(v["truncated"])),
        ("Citations", lambda v: str(v["citations"])),
        ("Citations vérifiées", lambda v: _pct(v["verified_rate"])),
        ("Citations d'un autre candidat", lambda v: _pct(v["wrong_candidate_rate"])),
        (
            "Faux silences (candidat attendu)",
            lambda v: f"{_pct(v['false_silence_rate'])} sur {v['expected_total']}",
        ),
        (
            "Silences corrects (candidat silencieux)",
            lambda v: f"{_pct(v['correct_silence_rate'])} sur {v['silent_total']}",
        ),
        ("Refus d'orienter le vote", lambda v: _pct(v["refusal_rate"])),
        ("Sections manquantes", lambda v: str(v["missing_sections"])),
        ("Jetons inconnus (`{{cN}}`)", lambda v: str(v["unknown_tokens"])),
        ("Noms écrits", lambda v: str(v["name_leaks"])),
        ("Signalements de neutralité", lambda v: str(v["neutrality_flags"])),
        ("Tokens de sortie (moyenne)", lambda v: str(v["tokens_out_mean"])),
        ("Latence moyenne", lambda v: f"{(v['latency_ms_mean'] or 0) / 1000:.1f} s"),
        ("Coût total", lambda v: f"{v['cost_usd']:.2f} $"),
    ]
    out = [
        "## 2. Chat (60 questions, premier tirage d'ordre)",
        "",
        "| Mesure | " + " | ".join(MODE_LABEL[m] for m in modes) + " |",
        "|---|" + "---|" * len(modes),
    ]
    for label, fn in rows:
        out.append(f"| {label} | " + " | ".join(fn(s[m]) for m in modes) + " |")
    if judge:
        out += ["", "### Juge LLM (Sonnet 5.5, passages cités seulement)", ""]
        out.append("| Mesure | " + " | ".join(MODE_LABEL[m] for m in modes if m in judge) + " |")
        out.append("|---|" + "---|" * sum(1 for m in modes if m in judge))
        for label, key in (
            ("Réponses jugées (échecs)", None),
            ("Affirmations", "claims"),
            ("Non appuyées", "unsupported"),
            ("Part non appuyée", "unsupported_rate"),
            ("Sections avec au moins une affirmation non appuyée", "sections_with_unsupported"),
        ):
            cells = []
            for m in modes:
                if m not in judge:
                    continue
                v = judge[m]
                if key is None:
                    cells.append(f"{v['judged']} ({v['failed']})")
                elif key == "unsupported_rate":
                    cells.append(_pct(v[key]))
                else:
                    cells.append(str(v[key]))
            out.append(f"| {label} | " + " | ".join(cells) + " |")
        for m in modes:
            if m in judge and judge[m]["examples"]:
                out += ["", f"Exemples d'affirmations non appuyées, mode {m} :", ""]
                out += [f"- {q}, {c} : « {t} »" for q, c, t in judge[m]["examples"][:5]]
    return out


def permutation_section(e: Mapping[str, Any] | None) -> list[str]:
    if not e:
        return [
            "## 3. Neutralité par permutation",
            "",
            "Non mesurée (aucun fichier `perms.jsonl`).",
        ]
    out = [
        "## 3. Neutralité par permutation",
        "",
        f"{e['questions']} questions, {e['answers']} réponses (mode rapide, plusieurs tirages "
        "de l'ordre des candidats). Corrélation de Spearman entre rang de présentation et "
        f"longueur des sections non silencieuses : **{_fmt(e['spearman_rank_length'])}** "
        "(0 : aucun effet de rang).",
        "",
        "| Rang | Longueur moyenne | Citations moyennes | Sections |",
        "|---|---|---|---|",
    ]
    for rank, v in e["by_rank"].items():
        out.append(f"| {rank} | {v['length']:.0f} | {v['citations']:.1f} | {v['n']} |")
    cvs = e["per_candidate_cv"]
    if cvs:
        out += [
            "",
            "Variation de la longueur d'un même candidat entre tirages (coefficient de "
            f"variation moyen) : de {min(cvs.values()):.2f} à {max(cvs.values()):.2f}.",
        ]
    return out


def profiles_results(election: Path) -> dict[str, Any]:
    statements = json.loads((election / "statements.json").read_text(encoding="utf-8"))[
        "statements"
    ]
    positions = json.loads((election / "positions.json").read_text(encoding="utf-8"))["positions"]
    ids = [s["id"] for s in statements]
    cands = sorted({p["candidate_id"] for p in positions})
    answers = {c: candidate_answers(positions, c, ids) for c in cands}
    return {
        "statements": len(ids),
        "known": {c: sum(v is not None for v in answers[c].values()) for c in cands},
        "base": synthetic_profiles(answers, statements, n=200, seed=7),
        "hard": synthetic_profiles(
            answers,
            statements,
            n=200,
            seed=7,
            noise=Noise(shift=0.5, abstain=0.4, silent_answer=0.8),
        ),
        "coords": {c: project_a(answers[c], statements) for c in cands},
    }


def profiles_section(p: Mapping[str, Any]) -> list[str]:
    base, hard = p["base"], p["hard"]
    out = [
        "## 4. Profils synthétiques",
        "",
        "200 répondants par candidat, calqués sur ses positions publiées, avec du bruit ; part "
        "de ceux dont le candidat d'origine est en tête de la proximité calculée par le moteur. "
        "Test optimiste : les profils dérivent des positions mêmes qu'ils départagent.",
        "",
        "| Candidat | Positions renseignées | 1er (bruit modéré) | 3 premiers | "
        "1er (bruit fort) | 3 premiers |",
        "|---|---|---|---|---|---|",
    ]
    for c, known in p["known"].items():
        b, h = base["per_candidate"][c], hard["per_candidate"][c]
        out.append(
            f"| {c} | {known} / {p['statements']} | {_pct(b['top1'])} | {_pct(b['top3'])} | "
            f"{_pct(h['top1'])} | {_pct(h['top3'])} |"
        )
    out.append(
        f"| **ensemble** | | {_pct(base['overall']['top1'])} | {_pct(base['overall']['top3'])} | "
        f"{_pct(hard['overall']['top1'])} | {_pct(hard['overall']['top3'])} |"
    )
    out += [
        "",
        "Bruit modéré : 30 % de réponses décalées d'un cran, 20 % « sans avis », réponse au "
        "hasard une fois sur deux là où le candidat est silencieux. Bruit fort : 50 %, 40 %, 80 %.",
        "",
        "Coordonnées du mode A (rappel) : "
        + " ; ".join(f"{c} ({_fmt(v['x'], 1)}, {_fmt(v['y'], 1)})" for c, v in p["coords"].items())
        + ".",
    ]
    return out


def reference_results(sheet: Path, election: Path) -> dict[str, Any]:
    coded = read_sheet(sheet) if sheet.is_file() else []
    positions = json.loads((election / "positions.json").read_text(encoding="utf-8"))["positions"]
    ches_dir = sheet.parent / "ches"
    return {
        "agreement": agreement(coded, positions) if coded else None,
        "ches_file": ches_dir.is_dir() and any(ches_dir.iterdir()),
    }


def reference_section(r: Mapping[str, Any]) -> list[str]:
    out = ["## 5. Positionnement contre références externes", ""]
    a = r["agreement"]
    if a:
        out.append(
            f"Codage manuel de référence : {a['n']} couples codés. Accord silence / non-silence "
            f"{_pct(a['silence_agreement'])} ; faux silences {a['false_silence']} ; valeurs "
            f"inventées {a['invented_value']} ; sur {a['both_valued']} couples valués des deux "
            f"côtés, accord exact {_pct(a['exact'])}, à un cran près {_pct(a['within_one'])}, "
            f"kappa pondéré {_fmt(a['weighted_kappa'])}."
        )
    else:
        out.append(
            "Codage manuel de référence : feuille `eval/reference/codage-2022.csv` prête "
            "(60 couples), **non encore codée** par le mainteneur."
        )
    out.append("")
    if r["ches_file"]:
        out.append("CHES : fichier présent, comparaison à brancher (`reference.ches_correlation`).")
    else:
        out.append(
            "CHES (lrecon, galtan) : **non mesuré**, le fichier de la Chapel Hill Expert Survey "
            "n'est pas déposé (téléchargement soumis à l'accord du mainteneur)."
        )
    return out


def _strip_scores(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {m: {k: v for k, v in d.items() if k != "scores"} for m, d in summary.items()}


def collect_results(
    *,
    date: str,
    questions: Sequence[Question],
    names: Mapping[str, str],
    retrieval_fixture: Path,
    run_dir: Path,
    election: Path,
    sheet: Path,
) -> dict[str, Any]:
    """Toutes les mesures, sous une forme JSON versionnable (aucun texte de réponse)."""
    records = _read_jsonl(run_dir / "ask.jsonl")
    main = [r for r in records if r["perm"] == 0]
    judged = _read_jsonl(run_dir / "judge.jsonl")
    verdicts = {v["custom_id"]: v["verdict"] for v in judged}
    perms = _read_jsonl(run_dir / "perms.jsonl")
    effects = permutation_effects(perms) if perms else None
    if effects:
        effects["by_rank"] = {str(k): v for k, v in effects["by_rank"].items()}
    judge = summarize_judgements(verdicts, main) if verdicts else None
    return {
        "date": date,
        "run_dir": run_dir.as_posix(),
        "retrieval": retrieval_results(retrieval_fixture, questions),
        "chat": _strip_scores(summarize(main, questions, names)),
        "judge": judge,
        "permutations": effects,
        "profiles": profiles_results(election),
        "reference": reference_results(sheet, election),
        "costs": {
            "chat": sum(r["log"]["cost_usd"] for r in records if r.get("log")),
            "permutations": sum(r["log"]["cost_usd"] for r in perms if r.get("log")),
            "juge": sum(v.get("cost_usd", 0.0) for v in judged),
        },
    }


def render(results: Mapping[str, Any], decisions: str | None = None) -> str:
    costs = results["costs"]
    lines = [
        f"# Backtest 2022 ({results['date']})",
        "",
        "Rapport généré par `uv run --project eval moi-electeur-eval backtest-report` à partir "
        f"de `eval/results/{results['date']}.json` (mesures sans texte de réponse, versionnées) ; "
        "PLAN § 6, SPEC § 9. Élection : présidentielle 2022, 12 candidats, corpus des programmes "
        "officiels.",
        "",
        *retrieval_section(results["retrieval"]),
        "",
        *chat_section(results["chat"], results["judge"]),
        "",
        *permutation_section(results["permutations"]),
        "",
        *profiles_section(results["profiles"]),
        "",
        *reference_section(results["reference"]),
        "",
        "## 6. Coût",
        "",
        "| Poste | Coût |",
        "|---|---|",
        *(f"| {k} | {v:.2f} $ |" for k, v in costs.items()),
        f"| **total** | **{sum(costs.values()):.2f} $** |",
        "",
    ]
    if decisions:
        lines += ["## 7. Décisions", "", decisions.strip(), ""]
    # Texte cité (réponses du chat) : tiret cadratin interdit dans le dépôt, écrit en entité HTML.
    return "\n".join(lines).replace(chr(0x2014), "&#8212;")
