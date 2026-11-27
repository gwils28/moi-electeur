"""Statistiques agrégées d'extraction et de découpage (fixture du notebook m2-01).

Lit `data/elections/<id>/sources/` (ignoré par git, absent en CI) et produit un petit JSON
versionnable : comptes par document et par candidat, tailles des extraits, cas limites. Aucun
texte de programme n'est recopié, sauf des exemples de cas limites tronqués à 60 caractères.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from statistics import median
from typing import Any

REQUIRED = (
    "candidate_id",
    "document_title",
    "source_url",
    "document_sha256",
    "page_number",
    "page_end",
)
# Mot de 6 lettres ou plus répété à l'identique (texte surimprimé, note M2b).
DOUBLED = re.compile(r"\b(\w{6,})\s+\1\b")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SHORT_TOKENS = 300
EXAMPLE_CHARS = 60


def read_chunks(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def read_extracted(directory: Path) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.json"))]


def _edge_cases(chunks: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    doubled: Counter[str] = Counter()
    examples: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    for c in chunks:
        text = c["text"]
        found = DOUBLED.findall(text)
        if found:
            counts["mots_doubles"] += 1
            doubled[c["candidate_id"]] += len(found)
            if len(examples) < 5:
                m = DOUBLED.search(text)
                assert m is not None
                examples.append({"chunk_id": c["id"], "extrait": m.group(0)[:EXAMPLE_CHARS]})
        if CONTROL.search(text):
            counts["caracteres_de_controle"] += 1
        if "­" in text:
            counts["traits_d_union_conditionnels"] += 1
        if not c.get("section_title"):
            counts["sans_titre_de_section"] += 1
        if c["page_end"] - c["page_number"] >= 2:
            counts["sur_3_pages_ou_plus"] += 1
        if c["token_count"] < SHORT_TOKENS:
            counts[f"moins_de_{SHORT_TOKENS}_tokens"] += 1
        if any(c.get(f) in (None, "") for f in REQUIRED):
            counts["metadonnee_manquante"] += 1
    return {
        "compte_extraits": dict(sorted(counts.items())),
        "mots_doubles_par_candidat": dict(sorted(doubled.items())),
        "exemples_mots_doubles": examples,
    }


def corpus_stats(chunks: list[dict[str, Any]], extracted: list[dict[str, Any]]) -> dict[str, Any]:
    by_doc: dict[str, list[dict[str, Any]]] = {}
    for c in chunks:
        by_doc.setdefault(c["document_sha256"][:12], []).append(c)
    documents = []
    for doc in sorted(extracted, key=lambda d: (d["candidate_id"], d["document_title"])):
        sha12 = doc["sha256"][:12]
        doc_chunks = by_doc.get(sha12, [])
        tokens = [c["token_count"] for c in doc_chunks]
        blocks = [b for p in doc["pages"] for b in p["blocks"]]
        covered = {n for c in doc_chunks for n in range(c["page_number"], c["page_end"] + 1)}
        documents.append(
            {
                "document": sha12,
                "candidate_id": doc["candidate_id"],
                "document_title": doc["document_title"],
                "profession_de_foi": doc["document_title"].startswith("Profession de foi"),
                "excluded": doc["excluded"],
                "pages": len(doc["pages"]),
                "pages_sans_texte": [p["page_number"] for p in doc["pages"] if not p["blocks"]],
                "pages_sans_extrait": [
                    p["page_number"]
                    for p in doc["pages"]
                    if p["blocks"] and p["page_number"] not in covered
                ],
                "titres": sum(1 for b in blocks if b["kind"] == "heading"),
                "blocs_texte": sum(1 for b in blocks if b["kind"] == "text"),
                "caracteres": sum(len(b["text"]) for b in blocks),
                "extraits": len(doc_chunks),
                "tokens_total": sum(tokens),
                "tokens_median": median(tokens) if tokens else None,
                "tokens_max": max(tokens) if tokens else None,
            }
        )
    candidates: dict[str, dict[str, int]] = {}
    for d in documents:
        agg = candidates.setdefault(
            d["candidate_id"], {"documents": 0, "pages": 0, "extraits": 0, "tokens_total": 0}
        )
        agg["documents"] += 1
        agg["pages"] += d["pages"]
        agg["extraits"] += d["extraits"]
        agg["tokens_total"] += d["tokens_total"]
    versions = sorted({c["corpus_version"] for c in chunks})
    return {
        "election_id": chunks[0]["election_id"] if chunks else None,
        "corpus_version": versions[0] if len(versions) == 1 else versions,
        "n_documents": len(documents),
        "n_extraits": len(chunks),
        "documents": documents,
        "candidats": dict(sorted(candidates.items())),
        "tokens_par_extrait": {
            cand: sorted(c["token_count"] for c in chunks if c["candidate_id"] == cand)
            for cand in sorted({c["candidate_id"] for c in chunks})
        },
        "cas_limites": _edge_cases(chunks),
    }


def corpus_stats_from_dir(election_dir: Path) -> dict[str, Any]:
    sources = election_dir / "sources"
    return corpus_stats(
        read_chunks(sources / "chunks.jsonl"), read_extracted(sources / "extracted")
    )
