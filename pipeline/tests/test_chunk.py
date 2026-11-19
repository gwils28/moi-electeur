"""`chunk` (PLAN § 4.2, D17) : bornes de taille, métadonnées, reconstruction, déterminisme.

Les propriétés sont vérifiées sur des documents générés aléatoirement (graines fixées) avec un
compteur de tokens « un mot = un token », additif, ce qui rend les bornes exactes.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pytest
from helpers import make_pdf, write_corpus_election

from moi_electeur_pipeline.chunk import (
    ChunkError,
    ChunkParams,
    chunk_corpus,
    chunk_document,
    compute_corpus_version,
    validate_chunk,
)
from moi_electeur_pipeline.extract import Block, ExtractedDocument, Page, extract_corpus
from moi_electeur_pipeline.sources import add_source

SHA = "ab" * 32
PARAMS = ChunkParams(min_tokens=30, max_tokens=60, overlap_tokens=5)
VERSION = "0123456789abcdef"


def words(text: str) -> int:
    return len(text.split())


def make_doc(pages: list[list[Block]], sha: str = SHA) -> ExtractedDocument:
    return ExtractedDocument(
        candidate_id="c1",
        document_title="Programme",
        source_url="https://a.fr/p.pdf",
        sha256=sha,
        type="pdf",
        pages=tuple(Page(i + 1, tuple(blocks)) for i, blocks in enumerate(pages)),
        excluded=False,
    )


def random_doc(seed: int) -> ExtractedDocument:
    """Document aux mots tous distincts (w0, w1, ...), titres et phrases de longueurs variées."""
    rng = random.Random(seed)
    counter = iter(range(10**6))
    pages: list[list[Block]] = []
    for _ in range(rng.randint(1, 8)):
        blocks: list[Block] = []
        for _ in range(rng.randint(0, 6)):
            if rng.random() < 0.2:
                blocks.append(Block("heading", f"Titre{next(counter)}"))
                continue
            sentences = []
            for _ in range(rng.randint(1, 5)):
                # Quelques phrases très longues forcent le découpage sous la phrase.
                n = rng.choice([rng.randint(1, 25), rng.randint(40, 130)])
                sentences.append(" ".join(f"w{next(counter)}" for _ in range(n)) + ".")
            blocks.append(Block("text", " ".join(sentences)))
        pages.append(blocks)
    return make_doc(pages)


def doc_words(doc: ExtractedDocument) -> list[str]:
    return [w for p in doc.pages for b in p.blocks for w in b.text.split()]


def chunks_of(doc: ExtractedDocument, params: ChunkParams = PARAMS) -> list[dict[str, Any]]:
    return chunk_document(
        doc, election_id="test-corpus", corpus_version=VERSION, count=words, params=params
    )


def strip_overlap(prev: list[str], cur: list[str], max_overlap: int) -> list[str]:
    """Retire de `cur` le plus long préfixe (<= max_overlap mots) égal à un suffixe de `prev`."""
    for n in range(min(max_overlap, len(prev), len(cur)), 0, -1):
        if prev[-n:] == cur[:n]:
            return cur[n:]
    return cur


SEEDS = range(60)


@pytest.mark.parametrize("seed", SEEDS)
def test_bornes_de_taille(seed: int) -> None:
    chunks = chunks_of(random_doc(seed))
    for i, c in enumerate(chunks):
        assert c["token_count"] == words(c["text"])
        assert c["token_count"] <= PARAMS.max_tokens
        if i < len(chunks) - 1:
            assert c["token_count"] >= PARAMS.min_tokens


@pytest.mark.parametrize("seed", SEEDS)
def test_reconstruction_sans_perte(seed: int) -> None:
    doc = random_doc(seed)
    chunks = [c["text"].split() for c in chunks_of(doc)]
    rebuilt: list[str] = []
    for i, cur in enumerate(chunks):
        rebuilt += cur if i == 0 else strip_overlap(chunks[i - 1], cur, PARAMS.overlap_tokens)
    assert rebuilt == doc_words(doc)


@pytest.mark.parametrize("seed", SEEDS)
def test_metadonnees_conformes_au_schema(seed: int) -> None:
    chunks = chunks_of(random_doc(seed))
    for i, c in enumerate(chunks):
        validate_chunk(c)
        assert c["id"] == f"{SHA[:12]}-{i:04d}"
        assert c["page_end"] >= c["page_number"]
        assert c["theme"] is None


def test_deterministe() -> None:
    assert chunks_of(random_doc(7)) == chunks_of(random_doc(7))


def test_pages_et_titre_de_section() -> None:
    para = " ".join(f"m{i}" for i in range(20)) + "."
    doc = make_doc(
        [
            [Block("text", para)],
            [Block("heading", "Santé"), Block("text", para), Block("text", para)],
            [Block("text", para)],
        ]
    )
    chunks = chunks_of(doc)
    assert chunks[0]["section_title"] is None
    assert chunks[0]["page_number"] == 1
    assert any(c["section_title"] == "Santé" for c in chunks)
    assert chunks[-1]["page_end"] == 3


def test_nouveau_titre_coupe_quand_le_minimum_est_atteint() -> None:
    para = " ".join(f"m{i}" for i in range(35)) + "."
    doc = make_doc([[Block("text", para), Block("heading", "Logement"), Block("text", para)]])
    chunks = chunks_of(doc)
    assert len(chunks) == 2
    assert chunks[1]["text"].startswith("Logement")
    assert chunks[1]["section_title"] == "Logement"


def test_paragraphes_separes_par_une_ligne_vide() -> None:
    doc = make_doc([[Block("text", "Un deux."), Block("text", "Trois quatre.")]])
    (chunk,) = chunks_of(doc)
    assert chunk["text"] == "Un deux.\n\nTrois quatre."


def test_document_exclu_ne_produit_rien() -> None:
    doc = make_doc([[Block("text", "Texte.")]])
    excluded = ExtractedDocument(**{**doc.__dict__, "excluded": True})
    assert chunks_of(excluded) == []


def test_parametres_incoherents_refuses() -> None:
    with pytest.raises(ValueError):
        ChunkParams(min_tokens=500, max_tokens=600, overlap_tokens=50)
    with pytest.raises(ValueError):
        ChunkParams(min_tokens=30, max_tokens=60, overlap_tokens=30)


def test_chunk_sans_metadonnee_obligatoire_rejete() -> None:
    (chunk,) = chunks_of(make_doc([[Block("text", "Texte.")]]))
    for field in ("candidate_id", "document_title", "source_url", "page_number", "section_title"):
        broken = {k: v for k, v in chunk.items() if k != field}
        with pytest.raises(ChunkError, match=field):
            validate_chunk(broken)
    with pytest.raises(ChunkError, match="page_end"):
        validate_chunk({**chunk, "page_number": 3, "page_end": 2})


def test_version_du_corpus() -> None:
    v = compute_corpus_version([SHA, "cd" * 32], PARAMS, "tok")
    assert v == compute_corpus_version(["cd" * 32, SHA], PARAMS, "tok")
    assert v != compute_corpus_version([SHA], PARAMS, "tok")
    assert v != compute_corpus_version([SHA, "cd" * 32], PARAMS, "autre-tokenizer")
    assert v != compute_corpus_version([SHA, "cd" * 32], PARAMS, "tok", "autre contenu")
    assert len(v) == 16


def test_chunk_corpus_bout_en_bout(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    body = " ".join(["Nous rénoverons les écoles publiques de chaque région."] * 6)
    pdf = make_pdf([[("Éducation", 22), (body, 11)], [(body, 11)]])
    add_source(election, "c1", "https://a.fr/p.pdf", "Programme", "pdf", fetcher=lambda _u: pdf)
    extract_corpus(election)
    report = chunk_corpus(election, count=words, params=PARAMS, tokenizer_name="mots")

    lines = (election / "sources" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    chunks = [json.loads(line) for line in lines]
    assert report.chunks_per_candidate == {"c1": len(chunks)}
    assert {c["election_id"] for c in chunks} == {"test-corpus"}
    assert {c["corpus_version"] for c in chunks} == {report.corpus_version}
    assert chunks[0]["section_title"] == "Éducation"
    for c in chunks:
        validate_chunk(c)


def test_chunk_corpus_exige_lextraction(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    pdf = make_pdf([[("Texte.", 11)]])
    add_source(election, "c1", "https://a.fr/p.pdf", "Programme", "pdf", fetcher=lambda _u: pdf)
    with pytest.raises(ChunkError, match="extract"):
        chunk_corpus(election, count=words, params=PARAMS, tokenizer_name="mots")


def test_titres_consecutifs_forment_un_seul_titre_de_section() -> None:
    doc = make_doc(
        [
            [
                Block("heading", "Pour apaiser et"),
                Block("heading", "sécuriser"),
                Block("text", "Texte."),
            ]
        ]
    )
    (chunk,) = chunks_of(doc)
    assert chunk["section_title"] == "Pour apaiser et sécuriser"


def test_metadonnees_prises_dans_la_config_courante(tmp_path: Path) -> None:
    """Un titre corrigé ou une réaffectation après `extract` est pris en compte par `chunk`,
    et change la version du corpus."""
    election = write_corpus_election(tmp_path)
    pdf = make_pdf([[("Texte du programme.", 11)]])
    add_source(election, "c1", "https://a.fr/p.pdf", "Programme", "pdf", fetcher=lambda _u: pdf)
    extract_corpus(election)
    before = chunk_corpus(election, count=words, params=PARAMS, tokenizer_name="mots")

    config_path = election / "election_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["corpus"][0]["document_title"] = "Programme corrigé"
    config["corpus"][0]["candidate_id"] = "c2"
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    after = chunk_corpus(election, count=words, params=PARAMS, tokenizer_name="mots")

    (chunk,) = [json.loads(line) for line in after.path.read_text(encoding="utf-8").splitlines()]
    assert chunk["document_title"] == "Programme corrigé"
    assert chunk["candidate_id"] == "c2"
    assert after.corpus_version != before.corpus_version


def test_titres_consecutifs_trop_longs_non_fusionnes() -> None:
    long_title = "T" * 197
    doc = make_doc(
        [[Block("heading", long_title), Block("heading", "Suite"), Block("text", "Texte.")]]
    )
    (chunk,) = chunks_of(doc)
    assert chunk["section_title"] == "Suite"
