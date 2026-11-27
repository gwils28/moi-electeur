"""`db-migrate` et `index` de bout en bout (marqueur `db`), avec le faux embedder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from helpers import make_pdf, write_corpus_election
from typer.testing import CliRunner

from moi_electeur_pipeline.chunk import ChunkParams, chunk_corpus
from moi_electeur_pipeline.cli import app
from moi_electeur_pipeline.extract import extract_corpus
from moi_electeur_pipeline.index import IndexingError, load_chunks
from moi_electeur_pipeline.sources import add_source
from moi_electeur_rag.db import connect
from moi_electeur_rag.embedding import FakeEmbedder
from moi_electeur_rag.retrieve import retrieve

runner = CliRunner()
PARAMS = ChunkParams(min_tokens=30, max_tokens=60, overlap_tokens=5)
BODY = " ".join(["Nous ramènerons la retraite à soixante ans pour les carrières longues."] * 8)


def words(text: str) -> int:
    return len(text.split())


def _chunked(tmp_path: Path) -> Path:
    election = write_corpus_election(tmp_path)
    for candidate in ("c1", "c2"):
        pdf = make_pdf([[("Retraites", 22), (f"{BODY} {candidate}", 11)]])
        url = f"https://a.fr/{candidate}.pdf"
        add_source(election, candidate, url, "Programme", "pdf", fetcher=lambda _u, p=pdf: p)
    extract_corpus(election)
    chunk_corpus(election, count=words, params=PARAMS, tokenizer_name="mots")
    return election


@pytest.mark.db
def test_db_migrate_puis_index(
    tmp_path: Path, db_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    election = _chunked(tmp_path)
    monkeypatch.setenv("DATABASE_URL", db_dsn)

    result = runner.invoke(app, ["db-migrate"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["index", str(election), "--model", "fake"])
    assert result.exit_code == 0, result.output
    assert "fake" in result.output

    with connect(db_dsn) as conn:
        found = retrieve(conn, FakeEmbedder(), election_id="test-corpus", question="retraite")
    assert [c["candidate_id"] for c in found["candidates"]] == ["c1", "c2"]
    assert all(c["chunks"] for c in found["candidates"])


def test_load_chunks_valide_chaque_extrait(tmp_path: Path) -> None:
    election = _chunked(tmp_path)
    chunks = load_chunks(election)
    assert chunks and all(c["election_id"] == "test-corpus" for c in chunks)

    path = election / "sources" / "chunks.jsonl"
    broken = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    del broken["source_url"]
    path.write_text(json.dumps(broken) + "\n", encoding="utf-8")
    with pytest.raises(IndexingError, match="source_url"):
        load_chunks(election)


def test_load_chunks_exige_le_decoupage(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    with pytest.raises(IndexingError, match="chunk"):
        load_chunks(election)
