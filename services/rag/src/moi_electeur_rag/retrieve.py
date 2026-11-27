"""Récupération hybride par candidat (PLAN § 4.4, SPEC § 6.1).

Pour chaque candidat : les `POOL` extraits les plus proches sémantiquement et les `POOL`
mieux classés en plein texte, fusionnés par RRF, puis les `k` premiers. Aucun seuil de score : tout
candidat indexé a des extraits, donc aucun n'est absent de la réponse faute de score.

Choix conservateur : la recherche sémantique est **exacte** (fenêtre `row_number` par
candidat, sans index HNSW). Un index approximatif filtré par candidat peut renvoyer moins de
`POOL` résultats pour un candidat peu représenté ; au volume d'une élection (environ un
millier d'extraits par modèle), le parcours exact prend quelques millisecondes.

Plein texte : les lexèmes de la question sont combinés en OU et classés par `ts_rank_cd`. En ET,
une question en langage naturel ne correspondrait presque jamais à un extrait. Les lexèmes
présents dans plus de `MAX_DF` des extraits de l'élection sont ignorés : en configuration
`french`, « les » devient le lexème `le` (le mot vide est testé avant la racinisation), présent
dans 99 % des extraits de 2022, qui noyait la requête (M2d : rappel@4 du RRF 0,60, sous la
sémantique seule à 0,67 ; 0,79 avec ce filtre, jeu de fumée `eval/smoke/`). Une question dont
tous les lexèmes sont ignorés n'a pas de requête plein texte (seul le sémantique joue).

Règle : ne jamais journaliser la question (SPEC § 6.3).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import psycopg

from .embedding import Embedder
from .ranking import rrf
from .store import CHUNK_COLUMNS

POOL = 20
# Fréquence documentaire au-delà de laquelle un lexème de la question est ignoré en plein texte.
MAX_DF = 0.5

_COLUMNS = ", ".join(f"c.{col}" for col in CHUNK_COLUMNS) + ", e.theme"
_FILTERS = (
    "e.election_id = %(election)s AND e.model = %(model)s "
    "AND c.candidate_id = ANY(%(candidates)s) "
    "AND (%(theme)s::text IS NULL OR e.theme = %(theme)s)"
)
_JOIN = "chunk_embeddings e JOIN chunks c ON c.election_id = e.election_id AND c.id = e.chunk_id"

SEMANTIC_SQL = f"""
SELECT * FROM (
    SELECT {_COLUMNS},
           row_number() OVER (
               PARTITION BY c.candidate_id ORDER BY e.embedding <=> %(vector)s, c.id
           ) AS rank
    FROM {_JOIN}
    WHERE {_FILTERS}
) ranked WHERE rank <= %(pool)s
"""

LEXICAL_SQL = f"""
WITH lexemes AS (
    SELECT DISTINCT unnest(tsvector_to_array(to_tsvector('french', %(question)s))) AS word
),
total AS (SELECT count(*) AS n FROM chunks WHERE election_id = %(election)s),
kept AS (
    SELECT l.word FROM lexemes l, total t
    WHERE (
        SELECT count(*) FROM chunks c2
        WHERE c2.election_id = %(election)s AND c2.tsv @@ quote_literal(l.word)::tsquery
    ) <= %(max_df)s * t.n
),
q AS (SELECT string_agg(quote_literal(word), ' | ' ORDER BY word)::tsquery AS query FROM kept)
SELECT * FROM (
    SELECT {_COLUMNS},
           row_number() OVER (
               PARTITION BY c.candidate_id ORDER BY ts_rank_cd(c.tsv, q.query) DESC, c.id
           ) AS rank
    FROM {_JOIN}, q
    WHERE {_FILTERS} AND c.tsv @@ q.query
) ranked WHERE rank <= %(pool)s
"""


class NotIndexed(LookupError):
    """Élection inconnue, ou non indexée pour ce modèle."""


def _chunk(row: dict[str, Any]) -> dict[str, Any]:
    chunk = {col: row[col] for col in CHUNK_COLUMNS}
    chunk["theme"] = row["theme"]
    return chunk


def retrieve(
    conn: psycopg.Connection[Any],
    embedder: Embedder,
    *,
    election_id: str,
    question: str,
    candidate_ids: Sequence[str] | None = None,
    theme: str | None = None,
    k: int = 4,
) -> dict[str, Any]:
    """Renvoie un document conforme à `schemas/retrieve_response.schema.json`."""
    version_row = conn.execute(
        "SELECT corpus_version FROM corpus_versions WHERE election_id = %s", (election_id,)
    ).fetchone()
    indexed = conn.execute(
        "SELECT 1 FROM chunk_embeddings WHERE election_id = %s AND model = %s LIMIT 1",
        (election_id, embedder.name),
    ).fetchone()
    if version_row is None or indexed is None:
        raise NotIndexed(f"{election_id} non indexée pour le modèle {embedder.name}")

    if candidate_ids:
        candidates = list(dict.fromkeys(candidate_ids))  # sans doublon, ordre conservé
    else:
        rows = conn.execute(
            "SELECT DISTINCT candidate_id FROM chunks WHERE election_id = %s", (election_id,)
        ).fetchall()
        candidates = [r["candidate_id"] for r in rows]
    candidates.sort()

    params = {
        "election": election_id,
        "model": embedder.name,
        "candidates": candidates,
        "theme": theme,
        "pool": POOL,
        "vector": embedder.embed_query(question),
        "question": question,
        "max_df": MAX_DF,
    }
    semantic = conn.execute(SEMANTIC_SQL, params).fetchall()
    lexical = conn.execute(LEXICAL_SQL, params).fetchall()

    rows_by_id: dict[str, dict[str, Any]] = {}
    sem_rank: dict[str, int] = {}
    lex_rank: dict[str, int] = {}
    sem_lists: dict[str, list[str]] = {c: [] for c in candidates}
    lex_lists: dict[str, list[str]] = {c: [] for c in candidates}
    for rows, ranks, lists in ((semantic, sem_rank, sem_lists), (lexical, lex_rank, lex_lists)):
        for row in sorted(rows, key=lambda r: (r["candidate_id"], r["rank"])):
            rows_by_id[row["id"]] = row
            ranks[row["id"]] = row["rank"]
            lists[row["candidate_id"]].append(row["id"])

    results = []
    for candidate in candidates:
        fused = rrf([sem_lists[candidate], lex_lists[candidate]])[:k]
        results.append(
            {
                "candidate_id": candidate,
                "chunks": [
                    {
                        "chunk": _chunk(rows_by_id[chunk_id]),
                        "score": score,
                        "semantic_rank": sem_rank.get(chunk_id),
                        "lexical_rank": lex_rank.get(chunk_id),
                    }
                    for chunk_id, score in fused
                ],
            }
        )
    return {
        "election_id": election_id,
        "corpus_version": version_row["corpus_version"],
        "model": embedder.name,
        "candidates": results,
    }
