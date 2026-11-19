"""Écriture du corpus indexé (`pipeline index`, PLAN § 4.2) : extraits, vecteurs, thèmes."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import psycopg

from .embedding import Embedder
from .ranking import classify_themes

CHUNK_COLUMNS = (
    "election_id",
    "id",
    "candidate_id",
    "document_title",
    "source_url",
    "document_sha256",
    "page_number",
    "page_end",
    "section_title",
    "text",
    "token_count",
    "corpus_version",
)
DEFAULT_THEME_MARGIN = 0.02


@dataclass
class IndexReport:
    model: str
    corpus_version: str
    n_chunks: int
    themes: dict[str | None, int]
    replaced_version: (
        str | None
    )  # version précédemment indexée si différente (autres modèles à réindexer)


def index_election(
    conn: psycopg.Connection[Any],
    *,
    election_id: str,
    chunks: Sequence[dict[str, Any]],
    embedder: Embedder,
    themes: Sequence[tuple[str, str]],
    theme_margin: float = DEFAULT_THEME_MARGIN,
) -> IndexReport:
    """Remplace l'index de l'élection pour ce modèle, en une transaction.

    Les extraits d'une autre version du corpus sont supprimés (avec leurs vecteurs, tous
    modèles confondus : ils ne correspondent plus au corpus).
    """
    versions = {c["corpus_version"] for c in chunks}
    if len(versions) != 1:
        raise ValueError(f"une seule version de corpus attendue, trouvé : {sorted(versions)}")
    if any(c["election_id"] != election_id for c in chunks):
        raise ValueError(f"extraits d'une autre élection que {election_id}")
    (version,) = versions
    # Vérifié avant le calcul des vecteurs (plusieurs minutes) : PostgreSQL refuse \x00.
    with_nul = [c["id"] for c in chunks if "\x00" in c["text"]]
    if with_nul:
        raise ValueError(f"caractère NUL dans les extraits {with_nul[:5]} : relancer `extract`")

    # Calcul (lent) hors transaction.
    vectors = embedder.embed_documents([c["text"] for c in chunks])
    theme_vectors = (
        np.stack([embedder.embed_query(description) for _, description in themes])
        if themes
        else np.zeros((0, embedder.dim), dtype=np.float32)
    )
    chunk_themes = classify_themes(vectors, theme_vectors, [t for t, _ in themes], theme_margin)

    placeholders = ", ".join(["%s"] * len(CHUNK_COLUMNS))
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in CHUNK_COLUMNS[2:])
    with conn.transaction():
        previous = conn.execute(
            "SELECT corpus_version FROM corpus_versions WHERE election_id = %s FOR UPDATE",
            (election_id,),
        ).fetchone()
        conn.execute(
            "DELETE FROM chunks WHERE election_id = %s AND corpus_version <> %s",
            (election_id, version),
        )
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO chunks ({', '.join(CHUNK_COLUMNS)}) VALUES ({placeholders}) "
                f"ON CONFLICT (election_id, id) DO UPDATE SET {updates}",
                [tuple(c[col] for col in CHUNK_COLUMNS) for c in chunks],
            )
            cur.execute(
                "DELETE FROM chunk_embeddings WHERE election_id = %s AND model = %s",
                (election_id, embedder.name),
            )
            cur.executemany(
                "INSERT INTO chunk_embeddings (election_id, chunk_id, model, theme, embedding) "
                "VALUES (%s, %s, %s, %s, %s)",
                [
                    (election_id, c["id"], embedder.name, theme, vector)
                    for c, theme, vector in zip(chunks, chunk_themes, vectors, strict=True)
                ],
            )
        conn.execute(
            "INSERT INTO corpus_versions (election_id, corpus_version) VALUES (%s, %s) "
            "ON CONFLICT (election_id) DO UPDATE "
            "SET corpus_version = EXCLUDED.corpus_version, indexed_at = now()",
            (election_id, version),
        )
    return IndexReport(
        model=embedder.name,
        corpus_version=version,
        n_chunks=len(chunks),
        themes=dict(Counter(chunk_themes)),
        replaced_version=(
            previous["corpus_version"]
            if previous and previous["corpus_version"] != version
            else None
        ),
    )
