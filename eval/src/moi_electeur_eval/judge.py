"""Juge LLM des réponses du chat (PLAN D40, M4b) : Sonnet 5.5 en Batch API vérifie, section par
section, que chaque affirmation est appuyée par les passages que la section cite.

Le juge ne voit que le texte des sections et les passages cités (`cited_text`), jamais les noms
des candidats : la question est la fidélité aux sources, pas le fond.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from moi_electeur_pipeline.propose import load_prompt
from moi_electeur_pipeline.validate import load_registry, schema_issues

from .chat import is_silence, parse_answer

JUDGE_MODEL = "claude-sonnet-5-5"
SCHEMA = "chat_judgement.schema.json"
MAX_TOKENS = 8000


def _schema() -> dict[str, Any]:
    _, schemas = load_registry()
    schema = dict(schemas[SCHEMA])
    for key in ("$schema", "$id"):
        schema.pop(key, None)
    return schema


def _content(record: Mapping[str, Any]) -> str:
    answer = parse_answer(record["events"])
    meta = next(e for e in record["events"] if e["type"] == "meta")
    parts = []
    for c in meta["candidates"]:
        section = answer.sections.get(c["candidate_id"])
        if section is None:
            continue
        passages = "\n".join(f"<passage>{x['cited_text']}</passage>" for x in section.citations)
        parts.append(
            f'<section jeton="{c["token"]}">\n<texte>\n{section.text}\n</texte>\n'
            f"<passages>\n{passages}\n</passages>\n</section>"
        )
    return (
        "<reponse>\n" + "\n".join(parts) + "\n</reponse>\n\n"
        "Rends un verdict par section, dans l'ordre, selon les consignes."
    )


def judge_requests(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Une requête par réponse réussie (premier tirage d'ordre seulement)."""
    prompt = load_prompt("judge_system")
    schema = _schema()
    out = []
    for r in records:
        if r["status"] != 200 or r["perm"] != 0:
            continue
        if not any(e["type"] == "done" for e in r["events"]):
            continue
        out.append(
            {
                "custom_id": f"j-{r['question_id']}-{r['mode']}",
                "params": {
                    "model": JUDGE_MODEL,
                    "max_tokens": MAX_TOKENS,
                    "system": [
                        {
                            "type": "text",
                            "text": prompt.text,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    "messages": [{"role": "user", "content": _content(r)}],
                    "thinking": {"type": "adaptive"},
                    "output_config": {
                        "effort": "medium",
                        "format": {"type": "json_schema", "schema": schema},
                    },
                },
            }
        )
    return out


def parse_judgement(message: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Verdict validé par le schéma, ou None (refus, troncature, sortie non conforme)."""
    if not message or message.get("stop_reason") != "end_turn":
        return None
    text = next((b["text"] for b in message.get("content", []) if b["type"] == "text"), None)
    if text is None:
        return None
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        return None
    if schema_issues(out, SCHEMA, "verdict"):
        return None
    verdict: dict[str, Any] = out
    return verdict


def summarize_judgements(
    verdicts: Mapping[str, dict[str, Any] | None], records: Sequence[Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Par mode : affirmations jugées, non appuyées, et exemples (question, candidat, texte)."""
    out: dict[str, dict[str, Any]] = {}
    for r in records:
        cid = f"j-{r['question_id']}-{r['mode']}"
        if cid not in verdicts:
            continue
        m = out.setdefault(
            r["mode"],
            {
                "judged": 0,
                "failed": 0,
                "claims": 0,
                "unsupported": 0,
                "unsupported_rate": None,
                "sections_with_unsupported": 0,
                "examples": [],
            },
        )
        verdict = verdicts[cid]
        if verdict is None:
            m["failed"] += 1
            continue
        m["judged"] += 1
        meta = next(e for e in r["events"] if e["type"] == "meta")
        token_of = {c["token"]: c["candidate_id"] for c in meta["candidates"]}
        answer = parse_answer(r["events"])
        for s in verdict["sections"]:
            cand = token_of.get(s["token"])
            section = answer.sections.get(cand) if cand else None
            if section is None or is_silence(section.text):
                continue
            m["claims"] += s["claims"]
            m["unsupported"] += s["unsupported"]
            if s["unsupported"]:
                m["sections_with_unsupported"] += 1
                m["examples"].extend((r["question_id"], cand, x) for x in s["examples"][:1])
    for m in out.values():
        m["unsupported_rate"] = m["unsupported"] / m["claims"] if m["claims"] else None
    return out
