"""Interface d'embedding (PLAN D15) : faux embedder des tests, préfixes e5, normalisation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from moi_electeur_rag.embedding import (
    MODELS,
    FakeEmbedder,
    SentenceTransformerEmbedder,
    get_embedder,
)


def test_fake_embedder_deterministe_et_normalise() -> None:
    e = FakeEmbedder()
    a = e.embed_documents(["la retraite à 60 ans", "la retraite à 60 ans"])
    assert a.shape == (2, e.dim)
    assert np.allclose(a[0], a[1])
    assert np.allclose(np.linalg.norm(a, axis=1), 1.0)


def test_fake_embedder_rapproche_les_textes_qui_partagent_des_mots() -> None:
    e = FakeEmbedder()
    q = e.embed_query("retraite")
    docs = e.embed_documents(["la retraite à 60 ans", "le nucléaire et le climat"])
    assert float(docs[0] @ q) > float(docs[1] @ q)


class StubModel:
    def __init__(self) -> None:
        self.inputs: list[list[str]] = []

    def encode(self, texts: list[str], **kwargs: Any) -> np.ndarray:
        self.inputs.append(list(texts))
        assert kwargs["normalize_embeddings"] is True
        return np.ones((len(texts), 1024), dtype=np.float32) / np.sqrt(1024)


@pytest.mark.parametrize(
    ("name", "query", "passage"),
    [("multilingual-e5-large", "query: ", "passage: "), ("bge-m3", "", "")],
)
def test_prefixes_par_modele(name: str, query: str, passage: str) -> None:
    stub = StubModel()
    e = SentenceTransformerEmbedder(MODELS[name], model=stub)
    e.embed_documents(["texte"])
    e.embed_query("question")
    assert stub.inputs == [[f"{passage}texte"], [f"{query}question"]]
    assert e.name == name
    assert e.dim == 1024


def test_modele_inconnu_refuse() -> None:
    with pytest.raises(ValueError, match="inconnu"):
        get_embedder("gpt")


def test_get_embedder_fake() -> None:
    assert get_embedder("fake").name == "fake"
