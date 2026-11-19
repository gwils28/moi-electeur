"""`extract` (PLAN § 4.2, D20, sources P6-P7) : texte par page, titres, en-têtes répétés."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from helpers import blank_pdf, make_pdf, write_corpus_election

from moi_electeur_pipeline.extract import (
    Block,
    ExtractError,
    _span_text,
    extract_corpus,
    extract_markdown,
    extract_pdf,
    join_lines,
    load_extracted,
)
from moi_electeur_pipeline.sources import add_source

BODY = "Nous proposons de rénover les écoles et de recruter des enseignants dans chaque région."


def _texts(blocks: tuple[Block, ...], kind: str) -> list[str]:
    return [b.text for b in blocks if b.kind == kind]


def test_pdf_numerote_les_pages_comme_un_lecteur_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(make_pdf([[(BODY, 11)], [("Deuxième page de texte.", 11)]]))
    pages = extract_pdf(pdf)
    assert [p.page_number for p in pages] == [1, 2]
    assert _texts(pages[1].blocks, "text") == ["Deuxième page de texte."]


def test_pdf_repere_les_titres_par_la_taille_de_police(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(make_pdf([[("Éducation", 22), (BODY, 11), (BODY, 11), (BODY, 11)]]))
    blocks = extract_pdf(pdf)[0].blocks
    assert _texts(blocks, "heading") == ["Éducation"]
    assert blocks[0] == Block("heading", "Éducation")
    assert len(_texts(blocks, "text")) == 3


def test_pdf_joint_les_lignes_dun_paragraphe(tmp_path: Path) -> None:
    long_text = " ".join([BODY] * 4)
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(make_pdf([[(long_text, 11)]]))
    (text,) = _texts(extract_pdf(pdf)[0].blocks, "text")
    assert "\n" not in text
    assert text == long_text


def test_pdf_retire_les_en_tetes_repetes_et_les_numeros_de_page(tmp_path: Path) -> None:
    pages = [[("Slogan de campagne", 9), (f"{BODY} Page {i}.", 11), (str(i), 9)] for i in range(8)]
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(make_pdf(pages))
    for page in extract_pdf(pdf):
        texts = [b.text for b in page.blocks]
        assert "Slogan de campagne" not in texts
        assert not any(t.isdigit() for t in texts)
        assert len(texts) == 1


def test_pdf_page_sans_texte_conservee_vide(tmp_path: Path) -> None:
    """Couverture en image (P6) : la page existe mais n'a aucun bloc ; pas d'OCR."""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(make_pdf([[], [(BODY, 11)]]))
    pages = extract_pdf(pdf)
    assert [len(p.blocks) for p in pages] == [0, 1]


def test_markdown_titres_et_paragraphes(tmp_path: Path) -> None:
    md = tmp_path / "doc.md"
    md.write_text("# Titre\n\nPremier paragraphe\nsur deux lignes.\n\n## Sous-titre\n\nSuite.\n")
    (page,) = extract_markdown(md)
    assert page.page_number == 1
    assert page.blocks == (
        Block("heading", "Titre"),
        Block("text", "Premier paragraphe sur deux lignes."),
        Block("heading", "Sous-titre"),
        Block("text", "Suite."),
    )


def _add_pdf(election: Path, url: str, data: bytes, title: str) -> None:
    add_source(election, "c1", url, title, "pdf", fetcher=lambda _u: data)


def test_extract_corpus_ecrit_un_fichier_par_document(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    _add_pdf(election, "https://a.fr/p.pdf", make_pdf([[(BODY, 11)]]), "Programme")
    report = extract_corpus(election)
    assert report.excluded == []
    (doc,) = load_extracted(election)
    assert doc.document_title == "Programme"
    assert doc.candidate_id == "c1"
    assert doc.pages[0].blocks[0].text == BODY
    assert not doc.excluded


def test_extract_corpus_signale_et_exclut_un_pdf_sans_texte(tmp_path: Path) -> None:
    """D20 : un PDF sans aucune couche texte est exclu (signalé), les autres sont extraits."""
    election = write_corpus_election(tmp_path)
    _add_pdf(election, "https://a.fr/scan.pdf", blank_pdf(3), "Scan")
    _add_pdf(election, "https://a.fr/p.pdf", make_pdf([[(BODY, 11)]]), "Programme")
    report = extract_corpus(election)
    assert report.excluded == ["c1 : Scan"]
    docs = {d.document_title: d for d in load_extracted(election)}
    assert docs["Scan"].excluded
    assert not docs["Programme"].excluded


def test_extract_corpus_signale_les_pages_vides(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    _add_pdf(election, "https://a.fr/p.pdf", make_pdf([[], [(BODY, 11)]]), "Programme")
    report = extract_corpus(election)
    assert report.empty_pages == {"c1 : Programme": [1]}


def _single_text(tmp_path: Path, blocks: list[tuple[str, float]]) -> list[str]:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(make_pdf([blocks]))
    return [b.text for b in extract_pdf(pdf)[0].blocks]


def test_pdf_retire_les_points_de_conduite(tmp_path: Path) -> None:
    assert _single_text(tmp_path, [("........ Rendre la justice efficace", 11)]) == [
        "Rendre la justice efficace"
    ]


def test_lignes_coupees_sur_un_tiret_recollees_en_gardant_le_tiret() -> None:
    """Césure ou mot composé : indiscernables, le tiret est gardé (aucune perte de texte)."""
    lines = ["le renonce-", "ment et le porte-", "parole, peut-", "être", "Fin-", "Suite"]
    assert join_lines(lines) == "le renonce-ment et le porte-parole, peut-être Fin- Suite"


def test_police_symbol_conservee_puce_dingbat_remplacee() -> None:
    assert _span_text({"text": "€", "font": "Symbol"}) == "€"
    assert _span_text({"text": "n", "font": "ZapfDingbatsITC"}).strip() == "•"
    assert _span_text({"text": "nnn", "font": "ZapfDingbatsITC"}) == "nnn"


def test_pdf_ignore_les_ornements_et_les_titres_dupliques(tmp_path: Path) -> None:
    blocks = [("“", 40), ("Justice", 22), ("Justice", 22), (BODY, 11), (BODY, 11)]
    assert _single_text(tmp_path, blocks) == ["Justice", BODY, BODY]


def test_pdf_puces_dune_police_de_symboles(tmp_path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((60, 80), "n", fontname="zadb", fontsize=11)  # ZapfDingbats
    page.insert_text((75, 80), "Réserver les logements sociaux", fontsize=11)
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(doc.tobytes())
    (text,) = [b.text for b in extract_pdf(pdf)[0].blocks]
    assert text == "• Réserver les logements sociaux"


def test_extract_corpus_verifie_le_sha256_et_la_presence(tmp_path: Path) -> None:
    election = write_corpus_election(tmp_path)
    _add_pdf(election, "https://a.fr/p.pdf", make_pdf([[(BODY, 11)]]), "Programme")
    source = election / "sources" / "c1" / "p.pdf"
    source.write_bytes(make_pdf([[("Texte substitué.", 11)]]))
    with pytest.raises(ExtractError, match="sha256"):
        extract_corpus(election)
    source.unlink()
    with pytest.raises(ExtractError, match="fetch"):
        extract_corpus(election)


def test_extract_corpus_refuse_un_chemin_hors_sources(tmp_path: Path) -> None:
    entry = {
        "candidate_id": "c1",
        "document_title": "Programme",
        "type": "pdf",
        "source_url": "https://a.fr/p.pdf",
        "local_path": "sources/../../hors.pdf",
        "sha256": "0" * 64,
        "retrieved_at": "2026-11-19",
    }
    election = write_corpus_election(tmp_path, [entry])
    with pytest.raises(ExtractError, match="hors de sources"):
        extract_corpus(election)
