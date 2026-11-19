"""Fabriques de données de test pour l'ingestion (PDF générés, élection « corpus seul »)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pymupdf

from moi_electeur_pipeline.demo import build_demo

ELECTION_ID = "test-corpus"


def make_pdf(pages: list[list[tuple[str, float]]]) -> bytes:
    """PDF dont chaque page est une liste de (texte, taille de police), un bloc par entrée."""
    doc = pymupdf.open()
    for blocks in pages:
        page = doc.new_page()
        y = 60.0
        for text, size in blocks:
            if not text:
                continue
            rect = pymupdf.Rect(60, y, 540, y + 400)
            # insert_textbox renvoie la hauteur restante : on en déduit la hauteur utilisée.
            left = page.insert_textbox(rect, text, fontsize=size)
            y += (400 - left) + size
    data: bytes = doc.tobytes()
    return data


def blank_pdf(n_pages: int = 2) -> bytes:
    doc = pymupdf.open()
    for _ in range(n_pages):
        doc.new_page()
    data: bytes = doc.tobytes()
    return data


def corpus_config(corpus: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Config d'une élection sans affirmations, reprise de la démo (2 candidats, thèmes décrits)."""
    config = build_demo()["election_config.json"]
    config = json.loads(json.dumps(config))
    config["id"] = ELECTION_ID
    config.pop("fictional", None)
    config["candidates"] = config["candidates"][:2]
    for theme in config["themes"]:
        theme["description"] = f"Périmètre du thème {theme['label']}."
    config["corpus"] = corpus or []
    return config


def write_corpus_election(root: Path, corpus: list[dict[str, Any]] | None = None) -> Path:
    target = root / ELECTION_ID
    target.mkdir(parents=True, exist_ok=True)
    (target / "election_config.json").write_text(
        json.dumps(corpus_config(corpus), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target


def read_config(election_dir: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (election_dir / "election_config.json").read_text(encoding="utf-8")
    )
    return data
