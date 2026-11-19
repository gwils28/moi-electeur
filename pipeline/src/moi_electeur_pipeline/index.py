"""`index` : écrit les extraits, leurs vecteurs et leurs thèmes dans PostgreSQL (PLAN § 4.2).

Le code d'embedding et d'écriture est celui du service RAG (`moi_electeur_rag`, D15) : une seule
implémentation pour l'indexation et les requêtes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from moi_electeur_rag.db import connect
from moi_electeur_rag.embedding import get_embedder
from moi_electeur_rag.store import DEFAULT_THEME_MARGIN, IndexReport, index_election

from .chunk import ChunkError, validate_chunk


class IndexingError(Exception):
    pass


def load_chunks(election_dir: Path) -> list[dict[str, Any]]:
    path = election_dir / "sources" / "chunks.jsonl"
    if not path.is_file():
        raise IndexingError(f"{path} absent : lancer `pipeline chunk`")
    chunks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    for chunk in chunks:
        try:
            validate_chunk(chunk)
        except ChunkError as exc:
            raise IndexingError(str(exc)) from exc
    if not chunks:
        raise IndexingError(f"{path} ne contient aucun extrait")
    return chunks


def index_corpus(
    election_dir: Path,
    *,
    model: str,
    dsn: str | None = None,
    theme_margin: float = DEFAULT_THEME_MARGIN,
) -> IndexReport:
    config = json.loads((election_dir / "election_config.json").read_text(encoding="utf-8"))
    chunks = load_chunks(election_dir)
    # Thèmes décrits seulement (D16) ; un thème sans description n'est jamais attribué.
    themes = [(t["id"], t["description"]) for t in config["themes"] if t.get("description")]
    with connect(dsn) as conn:
        return index_election(
            conn,
            election_id=config["id"],
            chunks=chunks,
            embedder=get_embedder(model),
            themes=themes,
            theme_margin=theme_margin,
        )
