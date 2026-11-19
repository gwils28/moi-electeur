"""Modèles d'embedding derrière une interface commune (PLAN D15, § 4.3).

Une seule implémentation sert à l'indexation (pipeline) et aux requêtes (service). Les
vecteurs sont normalisés L2 : le produit scalaire est la similarité cosinus.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt

Vectors = npt.NDArray[np.float32]
DIM = 1024


class Embedder(Protocol):
    name: str
    dim: int

    def embed_documents(self, texts: Sequence[str]) -> Vectors: ...

    def embed_query(self, text: str) -> Vectors: ...


@dataclass(frozen=True)
class ModelSpec:
    name: str
    hf_id: str
    query_prefix: str
    passage_prefix: str
    max_seq_length: int  # tokens au-delà desquels le modèle tronque l'entrée
    dim: int = DIM


MODELS = {
    # bge-m3 accepte 8192 tokens ; 1024 couvre les extraits (600 au plus) avec marge.
    "bge-m3": ModelSpec("bge-m3", "BAAI/bge-m3", "", "", max_seq_length=1024),
    # e5 exige des préfixes « query: » / « passage: » et plafonne à 512 tokens : les extraits
    # les plus longs sont tronqués de leur fin (limite connue, mesurée en M4).
    "multilingual-e5-large": ModelSpec(
        "multilingual-e5-large",
        "intfloat/multilingual-e5-large",
        "query: ",
        "passage: ",
        max_seq_length=512,
    ),
}
DEFAULT_MODEL = "bge-m3"


def models_dir() -> Path:
    """Poids téléchargés dans `models/` (ignoré par git ; volume `/models` dans Docker)."""
    return Path(os.environ.get("MODELS_DIR", Path(__file__).resolve().parents[4] / "models"))


class SentenceTransformerEmbedder:
    def __init__(self, spec: ModelSpec, model: Any = None, batch_size: int = 16) -> None:
        self.spec = spec
        self.name = spec.name
        self.dim = spec.dim
        self.batch_size = batch_size
        self._model = model

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # import coûteux, à la demande

            self._model = SentenceTransformer(
                self.spec.hf_id, device="cpu", cache_folder=str(models_dir())
            )
            self._model.max_seq_length = self.spec.max_seq_length
        return self._model

    def _encode(self, texts: Sequence[str]) -> Vectors:
        vectors = self.model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    def embed_documents(self, texts: Sequence[str]) -> Vectors:
        return self._encode([self.spec.passage_prefix + t for t in texts])

    def embed_query(self, text: str) -> Vectors:
        vector: Vectors = self._encode([self.spec.query_prefix + text])[0]
        return vector


class FakeEmbedder:
    """Embedder déterministe des tests : sac de mots hachés, aucun modèle ni réseau.

    Deux textes qui partagent des mots ont une similarité positive, ce qui suffit à tester
    l'indexation et la récupération.
    """

    name = "fake"
    dim = DIM

    def _one(self, text: str) -> Vectors:
        v = np.zeros(self.dim, dtype=np.float32)
        for word in re.findall(r"\w+", text.casefold()):
            h = int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "big")
            v[h % self.dim] += 1.0
        norm = float(np.linalg.norm(v))
        if norm == 0:
            v[0] = 1.0
            return v
        return v / norm

    def embed_documents(self, texts: Sequence[str]) -> Vectors:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.stack([self._one(t) for t in texts]).astype(np.float32)

    def embed_query(self, text: str) -> Vectors:
        return self._one(text)


@cache
def get_embedder(name: str = DEFAULT_MODEL) -> Embedder:
    if name == "fake":
        return FakeEmbedder()
    if name not in MODELS:
        raise ValueError(f"modèle d'embedding inconnu : {name} (connus : {', '.join(MODELS)})")
    return SentenceTransformerEmbedder(MODELS[name])
