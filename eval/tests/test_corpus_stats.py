"""Statistiques d'extraction sur un corpus jouet."""

from __future__ import annotations

from typing import Any

from moi_electeur_eval.corpus_stats import corpus_stats


def chunk(n: int, text: str, pages: tuple[int, int], tokens: int, **over: Any) -> dict[str, Any]:
    return {
        "id": f"aaaaaaaaaaaa-{n:04d}",
        "election_id": "test",
        "candidate_id": "alice",
        "document_title": "Programme",
        "source_url": "https://example.org/p.pdf",
        "document_sha256": "a" * 64,
        "page_number": pages[0],
        "page_end": pages[1],
        "section_title": "Titre",
        "text": text,
        "token_count": tokens,
        "corpus_version": "v1",
        **over,
    }


EXTRACTED = [
    {
        "candidate_id": "alice",
        "document_title": "Programme",
        "sha256": "a" * 64,
        "type": "pdf",
        "excluded": False,
        "pages": [
            {"page_number": 1, "blocks": []},
            {
                "page_number": 2,
                "blocks": [{"kind": "heading", "text": "Titre"}, {"kind": "text", "text": "abc"}],
            },
            {"page_number": 3, "blocks": [{"kind": "text", "text": "de"}]},
            {"page_number": 4, "blocks": [{"kind": "text", "text": "orphelin"}]},
            {"page_number": 5, "blocks": [{"kind": "text", "text": "fin"}]},
        ],
    }
]


def test_statistiques_jouet() -> None:
    chunks = [
        chunk(0, "SIMPLIFIER SIMPLIFIER la vie", (2, 3), 500),
        chunk(1, "texte\x07 avec contrôle", (5, 5), 120, section_title=None),
    ]
    s = corpus_stats(chunks, EXTRACTED)
    doc = s["documents"][0]
    assert doc["pages"] == 5
    assert doc["pages_sans_texte"] == [1]
    assert doc["pages_sans_extrait"] == [4]
    assert (doc["titres"], doc["blocs_texte"], doc["caracteres"]) == (
        1,
        4,
        21,
    )  # Titre 5 + abc 3 + de 2 + orphelin 8 + fin 3
    assert (doc["extraits"], doc["tokens_total"], doc["tokens_max"]) == (2, 620, 500)
    assert s["candidats"]["alice"] == {
        "documents": 1,
        "pages": 5,
        "extraits": 2,
        "tokens_total": 620,
    }
    assert s["tokens_par_extrait"] == {"alice": [120, 500]}
    cas = s["cas_limites"]["compte_extraits"]
    assert cas["mots_doubles"] == 1
    assert cas["caracteres_de_controle"] == 1
    assert cas["sans_titre_de_section"] == 1
    assert cas["moins_de_300_tokens"] == 1
    assert "metadonnee_manquante" not in cas
    assert s["cas_limites"]["exemples_mots_doubles"][0]["extrait"] == "SIMPLIFIER SIMPLIFIER"


def test_metadonnee_manquante() -> None:
    s = corpus_stats([chunk(0, "x", (2, 2), 10, source_url="")], EXTRACTED)
    assert s["cas_limites"]["compte_extraits"]["metadonnee_manquante"] == 1
