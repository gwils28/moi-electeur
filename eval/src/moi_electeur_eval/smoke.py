"""Jeu de fumée du retrieval (PLAN § 4.7) : lecture et contrôle de `eval/smoke/*.jsonl`.

Format documenté dans `eval/smoke/README.md`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KINDS = ("theme", "silence", "recommandation")


@dataclass(frozen=True)
class ExpectedChunk:
    chunk_id: str
    document_title: str
    pages: str


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    kind: str
    theme: str | None
    expected: dict[str, list[ExpectedChunk]] = field(default_factory=dict)
    silent: list[str] = field(default_factory=list)
    note: str = ""

    def relevant(self, candidate_id: str) -> set[str]:
        return {e.chunk_id for e in self.expected.get(candidate_id, [])}


def smoke_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "smoke"


def default_questions_path() -> Path:
    return smoke_dir() / "questions-2022.jsonl"


def parse_question(raw: Mapping[str, Any]) -> Question:
    expected = {
        cand: [ExpectedChunk(**e) for e in items] for cand, items in raw.get("expected", {}).items()
    }
    q = Question(
        id=raw["id"],
        question=raw["question"],
        kind=raw["kind"],
        theme=raw.get("theme"),
        expected=expected,
        silent=list(raw.get("silent", [])),
        note=raw.get("note", ""),
    )
    problems = structural_issues(q)
    if problems:
        raise ValueError(f"{q.id} : " + " ; ".join(problems))
    return q


def structural_issues(q: Question) -> list[str]:
    """Règles du format, sans le corpus."""
    out = []
    if q.kind not in KINDS:
        out.append(f"kind inconnu : {q.kind}")
    if q.kind == "recommandation" and (q.expected or q.silent):
        out.append("une demande de recommandation n'a ni attendu ni silence")
    if q.kind != "recommandation" and not q.expected:
        out.append("aucun candidat attendu")
    if q.kind == "silence" and not q.silent:
        out.append("piège sans candidat silencieux")
    if q.kind == "theme" and q.silent:
        out.append("candidats silencieux hors piège (kind = silence)")
    both = set(q.expected) & set(q.silent)
    if both:
        out.append(f"candidats à la fois attendus et silencieux : {sorted(both)}")
    for cand, items in q.expected.items():
        if not items:
            out.append(f"{cand} attendu sans extrait")
        for e in items:
            if not e.chunk_id:
                out.append(f"{cand} : chunk_id vide")
    return out


def load_questions(path: Path | None = None) -> list[Question]:
    path = path or default_questions_path()
    questions = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                questions.append(parse_question(json.loads(line)))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{path.name}:{n} : {exc}") from exc
    ids = [q.id for q in questions]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path.name} : identifiants de question en double")
    return questions


def corpus_issues(questions: Iterable[Question], chunks: Iterable[Mapping[str, Any]]) -> list[str]:
    """Écarts entre les attendus et le corpus : extrait inconnu, mauvais candidat, pages ou titre
    qui ne correspondent plus (le corpus a été redécoupé), candidat inconnu."""
    by_id = {c["id"]: c for c in chunks}
    candidates = {c["candidate_id"] for c in by_id.values()}
    out = []
    for q in questions:
        for cand in [*q.expected, *q.silent]:
            if cand not in candidates:
                out.append(f"{q.id} : candidat inconnu {cand}")
        for cand, items in q.expected.items():
            for e in items:
                c = by_id.get(e.chunk_id)
                if c is None:
                    out.append(f"{q.id} : extrait inconnu {e.chunk_id}")
                    continue
                if c["candidate_id"] != cand:
                    out.append(f"{q.id} : {e.chunk_id} appartient à {c['candidate_id']}")
                if e.pages != pages_label(c["page_number"], c["page_end"]):
                    out.append(
                        f"{q.id} : {e.chunk_id} pages {e.pages} au lieu de {pages_label(c['page_number'], c['page_end'])}"
                    )
                if e.document_title != c["document_title"]:
                    out.append(f"{q.id} : {e.chunk_id} titre de document différent")
    return out


def pages_label(start: int, end: int) -> str:
    return str(start) if start == end else f"{start}-{end}"
