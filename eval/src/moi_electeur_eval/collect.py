"""Classements réels du jeu de fumée, lus dans la base indexée (PLAN § 4.7).

Reprend les requêtes SQL et la fusion RRF du service (`moi_electeur_rag.retrieve`) pour
obtenir, pour chaque question et chaque candidat, trois classements : sémantique seul, plein
texte seul et RRF (celui que renvoie `/retrieve`). Aucun appel à un modèle de langue.

Règle : ne jamais journaliser les questions (ici publiques, mais le code est partagé en esprit
avec le service).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import psycopg

from moi_electeur_rag.embedding import Embedder
from moi_electeur_rag.ranking import RRF_K, rrf
from moi_electeur_rag.retrieve import LEXICAL_SQL, POOL, SEMANTIC_SQL, NotIndexed

from .smoke import Question, corpus_issues

METHODS = ("semantique", "plein_texte", "rrf")
# Variante expérimentale (non servie par /retrieve) : plein texte sans les lexèmes présents dans
# plus de `MAX_DF` des extraits. En configuration `french`, « les » devient le lexème `le`
# (non retiré comme mot vide) qui figure dans presque tous les extraits : en OU, il noie la
# requête. Mesurée pour éclairer la décision, sans modifier le service.
EXPERIMENTAL = ("plein_texte_filtre", "rrf_filtre")
ALL_METHODS = METHODS + EXPERIMENTAL
MAX_DF = 0.5

QUERY_LEXEMES_SQL = "SELECT unnest(tsvector_to_array(to_tsvector('french', %(question)s))) AS lex"

DOC_FREQ_SQL = """
SELECT word, ndoc::float / (SELECT count(*) FROM chunks WHERE election_id = %(election)s) AS df
FROM ts_stat(format('SELECT tsv FROM chunks WHERE election_id = %%L', %(election)s::text))
"""

# Même requête que LEXICAL_SQL, mais la tsquery (lexèmes en OU) est fournie toute faite.
LEXICAL_FILTERED_SQL = LEXICAL_SQL.replace(
    "replace(plainto_tsquery('french', %(question)s)::text, '&', '|')::tsquery",
    "%(tsquery)s::tsquery",
)

SIMILARITY_SQL = """
SELECT e.chunk_id, 1 - (e.embedding <=> %(vector)s) AS sim
FROM chunk_embeddings e
WHERE e.election_id = %(election)s AND e.model = %(model)s
"""


def fuse(semantic: Sequence[str], lexical: Sequence[str]) -> list[str]:
    """Fusion RRF identique à `/retrieve` (k = 60, égalités départagées par identifiant)."""
    return [chunk_id for chunk_id, _ in rrf([semantic, lexical])]


def filtered_tsquery(
    lexemes: Sequence[str], doc_freq: dict[str, float], max_df: float = MAX_DF
) -> str:
    """Lexèmes en OU, sans ceux dont la fréquence documentaire dépasse `max_df`."""
    kept = sorted({lex for lex in lexemes if doc_freq.get(lex, 0.0) <= max_df})
    return " | ".join("'" + lex.replace("'", "''") + "'" for lex in kept)


def query_lexemes(conn: psycopg.Connection[Any], question: str) -> list[str]:
    """Lexèmes de la question en configuration `french` (ceux de `plainto_tsquery`)."""
    return sorted({r["lex"] for r in conn.execute(QUERY_LEXEMES_SQL, {"question": question})})


def question_rankings(
    conn: psycopg.Connection[Any],
    embedder: Embedder,
    *,
    election_id: str,
    question: str,
    candidates: Sequence[str],
    pool: int = POOL,
    doc_freq: dict[str, float] | None = None,
) -> tuple[dict[str, dict[str, list[str]]], dict[str, float]]:
    """Classements par méthode et par candidat, et similarité cosinus de chaque extrait."""
    vector = embedder.embed_query(question)
    params = {
        "election": election_id,
        "model": embedder.name,
        "candidates": list(candidates),
        "theme": None,
        "pool": pool,
        "vector": vector,
        "question": question,
    }
    methods = ALL_METHODS if doc_freq is not None else METHODS
    out: dict[str, dict[str, list[str]]] = {m: {c: [] for c in candidates} for m in methods}
    queries = [("semantique", SEMANTIC_SQL), ("plein_texte", LEXICAL_SQL)]
    if doc_freq is not None:
        params["tsquery"] = filtered_tsquery(query_lexemes(conn, question), doc_freq)
        if params["tsquery"]:
            queries.append(("plein_texte_filtre", LEXICAL_FILTERED_SQL))
    for method, sql in queries:
        rows = conn.execute(sql, params).fetchall()
        for row in sorted(rows, key=lambda r: (r["candidate_id"], r["rank"])):
            out[method][row["candidate_id"]].append(row["id"])
    for cand in candidates:
        out["rrf"][cand] = fuse(out["semantique"][cand], out["plein_texte"][cand])
        if doc_freq is not None:
            out["rrf_filtre"][cand] = fuse(out["semantique"][cand], out["plein_texte_filtre"][cand])
    sims = {r["chunk_id"]: float(r["sim"]) for r in conn.execute(SIMILARITY_SQL, params)}
    return out, sims


def _similarity_summary(
    sims: dict[str, float], relevant: set[str], top: Sequence[str]
) -> dict[str, float | None]:
    values = np.array(list(sims.values()), dtype=np.float64)
    rel = [sims[c] for c in relevant if c in sims]
    irr = [s for c, s in sims.items() if c not in relevant]
    return {
        "min": round(float(values.min()), 4),
        "p50": round(float(np.median(values)), 4),
        "p90": round(float(np.quantile(values, 0.9)), 4),
        "max": round(float(values.max()), 4),
        "top4_mean": round(float(np.mean([sims[c] for c in top[:4]])), 4),
        "relevant_mean": round(float(np.mean(rel)), 4) if rel else None,
        "irrelevant_mean": round(float(np.mean(irr)), 4) if irr else None,
    }


def collect(
    conn: psycopg.Connection[Any],
    embedder: Embedder,
    *,
    election_id: str,
    questions: Sequence[Question],
    keep: int = 10,
) -> dict[str, Any]:
    """Classements (les `keep` premiers par candidat) et similarités pour un modèle."""
    indexed = conn.execute(
        "SELECT 1 FROM chunk_embeddings WHERE election_id = %s AND model = %s LIMIT 1",
        (election_id, embedder.name),
    ).fetchone()
    version = conn.execute(
        "SELECT corpus_version FROM corpus_versions WHERE election_id = %s", (election_id,)
    ).fetchone()
    if indexed is None or version is None:
        raise NotIndexed(f"{election_id} non indexée pour le modèle {embedder.name}")
    chunks = conn.execute(
        "SELECT id, candidate_id, document_title, page_number, page_end FROM chunks"
        " WHERE election_id = %s",
        (election_id,),
    ).fetchall()
    issues = corpus_issues(questions, chunks)
    if issues:
        raise ValueError("jeu de fumée incohérent avec l'index :\n  " + "\n  ".join(issues))
    candidates = sorted({c["candidate_id"] for c in chunks})

    doc_freq = {
        r["word"]: float(r["df"]) for r in conn.execute(DOC_FREQ_SQL, {"election": election_id})
    }
    rankings: dict[str, dict[str, dict[str, list[str]]]] = {m: {} for m in ALL_METHODS}
    similarity: dict[str, dict[str, float | None]] = {}
    lexemes: dict[str, dict[str, float]] = {}
    for q in questions:
        per_method, sims = question_rankings(
            conn,
            embedder,
            election_id=election_id,
            question=q.question,
            candidates=candidates,
            doc_freq=doc_freq,
        )
        lexemes[q.id] = {
            lex: round(doc_freq.get(lex, 0.0), 3) for lex in query_lexemes(conn, q.question)
        }
        for method in ALL_METHODS:
            rankings[method][q.id] = {c: ids[:keep] for c, ids in per_method[method].items()}
        relevant = set().union(*(q.relevant(c) for c in q.expected)) if q.expected else set()
        top = sorted(sims, key=lambda c: -sims[c])
        similarity[q.id] = _similarity_summary(sims, relevant, top)
    return {
        "corpus_version": version["corpus_version"],
        "candidates": candidates,
        "pool": POOL,
        "rrf_k": RRF_K,
        "keep": keep,
        "max_df": MAX_DF,
        "rankings": rankings,
        "similarity": similarity,
        "lexemes": lexemes,
    }
