"""`extract` : texte des documents du corpus, page par page, en blocs « titre » ou « texte ».

- PDF (PyMuPDF) : numéro de page = rang de la page dans le PDF, celui qu'affiche un lecteur PDF
  (sources P7). Un bloc dont la police est nettement plus grande que le corps du texte est un
  titre. Les en-têtes et pieds de page répétés et les numéros de page seuls sont retirés.
- HTML (trafilatura, converti en Markdown) et Markdown : une seule page.
- Pas d'OCR (sources P6, D20) : une page sans couche texte reste vide, un document sans aucun
  texte est exclu et signalé.

Sortie : `sources/extracted/<sha256[:12]>.json` par document (format interne au pipeline,
relu par `chunk`).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import pymupdf

from .validate import local_path_issue

HEADING_RATIO = 1.2  # taille de police minimale d'un titre, relativement au corps du texte
HEADING_MAX_CHARS = 150
HEADING_MAX_LINES = 3
REPEATED_MAX_CHARS = 80  # un en-tête ou pied de page répété est court
REPEATED_MIN_PAGES = 6  # pas sur les professions de foi (2 à 4 pages)
REPEATED_SHARE = 0.5

BlockKind = Literal["heading", "text"]


@dataclass(frozen=True)
class Block:
    kind: BlockKind
    text: str


@dataclass(frozen=True)
class Page:
    page_number: int
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class ExtractedDocument:
    candidate_id: str
    document_title: str
    source_url: str
    sha256: str
    type: str
    pages: tuple[Page, ...]
    excluded: bool


@dataclass
class ExtractReport:
    excluded: list[str] = field(default_factory=list)
    empty_pages: dict[str, list[int]] = field(default_factory=dict)
    written: list[Path] = field(default_factory=list)


# Polices de puces : « Symbol » en est exclue (elle porte aussi €, ≥, %…).
BULLET_FONTS = re.compile(r"dingbat|wingding", re.IGNORECASE)
LEADER_DOTS = re.compile(r"(?:\.\s*){4,}|…(?:\s*…)+")  # points de conduite d'un sommaire


# Caractères de contrôle (glyphes mal décodés : \x00, \x07…) ; PostgreSQL refuse \x00.
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _clean(text: str) -> str:
    # U+00AD (trait d'union conditionnel) est invisible : retiré, titres compris.
    text = CONTROL_CHARS.sub(" ", text).replace("\xad", "")
    return re.sub(r"\s+", " ", text).strip()


def _clean_pdf(text: str) -> str:
    return _clean(LEADER_DOTS.sub(" ", text))


def join_lines(lines: list[str]) -> str:
    """Joint les lignes d'un bloc. Une ligne finissant par « lettre- » suivie d'une ligne en
    minuscule est recollée sans espace mais en gardant le tiret : on ne sait pas distinguer une
    césure (« renonce-ment ») d'un mot composé (« porte-parole »), et garder le tiret ne perd
    aucune information du texte officiel."""
    text = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if text.endswith("\xad"):
            # Trait d'union conditionnel (U+00AD) : césure typographique, on recolle sans lui.
            text = text[:-1] + stripped
            continue
        glued = re.search(r"[a-zà-ÿ]-$", text) and stripped[0].islower()
        text = f"{text}{stripped}" if glued or not text else f"{text} {stripped}"
    # Les traits d'union conditionnels restants sont invisibles : retirés.
    return text.replace("\xad", "")


def _span_text(span: dict[str, Any]) -> str:
    """Une puce d'une police de puces (ZapfDingbats…) est lue comme une lettre : « • »."""
    text: str = span["text"]
    if BULLET_FONTS.search(span.get("font", "")) and len(text.strip()) == 1:
        return " • "
    return text


# --- PDF ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class _RawBlock:
    text: str
    size: float  # plus grande taille de police du bloc
    n_lines: int


def _raw_blocks(page: pymupdf.Page) -> list[_RawBlock]:
    flags = pymupdf.TEXTFLAGS_TEXT | pymupdf.TEXT_DEHYPHENATE
    data = page.get_text("dict", sort=True, flags=flags)
    blocks = []
    for block in data["blocks"]:
        lines = [
            "".join(_span_text(span) for span in line["spans"]) for line in block.get("lines", [])
        ]
        text = _clean_pdf(join_lines(lines))
        sizes = [span["size"] for line in block.get("lines", []) for span in line["spans"]]
        if text and sizes:
            blocks.append(_RawBlock(text, max(sizes), len(lines)))
    return blocks


def _body_size(pages: list[list[_RawBlock]]) -> float:
    """Taille de police la plus fréquente, pondérée par le nombre de caractères."""
    weights: Counter[float] = Counter()
    for blocks in pages:
        for b in blocks:
            weights[round(b.size * 2) / 2] += len(b.text)
    return weights.most_common(1)[0][0] if weights else 0.0


def _repeat_key(text: str) -> str:
    return re.sub(r"\d+", "#", text.casefold())


def _repeated(pages: list[list[_RawBlock]]) -> set[str]:
    """Blocs courts présents sur plus de la moitié des pages : en-têtes, pieds de page, slogans."""
    if len(pages) < REPEATED_MIN_PAGES:
        return set()
    seen: Counter[str] = Counter()
    for blocks in pages:
        seen.update({_repeat_key(b.text) for b in blocks if len(b.text) <= REPEATED_MAX_CHARS})
    return {key for key, n in seen.items() if n > REPEATED_SHARE * len(pages)}


def extract_pdf(path: Path) -> list[Page]:
    with pymupdf.open(path) as doc:
        raw = [_raw_blocks(page) for page in doc]
    body = _body_size(raw)
    repeated = _repeated(raw)
    pages = []
    for number, blocks in enumerate(raw, start=1):
        kept: list[Block] = []
        for b in blocks:
            # Numéros de page, ornements sans lettre ni chiffre, en-têtes répétés.
            decorative = re.fullmatch(r"[\d\s/.-]+", b.text) or not re.search(r"\w", b.text)
            if decorative or _repeat_key(b.text) in repeated:
                continue
            is_heading = (
                b.size >= HEADING_RATIO * body
                and len(b.text) <= HEADING_MAX_CHARS
                and b.n_lines <= HEADING_MAX_LINES
            )
            if is_heading and kept and kept[-1] == Block("heading", b.text):
                continue  # titre dupliqué (calque de texte en double)
            kept.append(Block("heading" if is_heading else "text", b.text))
        pages.append(Page(number, tuple(kept)))
    return pages


# --- Markdown et HTML ----------------------------------------------------------------------


def markdown_blocks(text: str) -> tuple[Block, ...]:
    blocks: list[Block] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        heading = re.fullmatch(r"#{1,6}\s+(.+)", para)
        if heading and "\n" not in para:
            blocks.append(Block("heading", _clean(heading.group(1))))
        else:
            blocks.append(Block("text", _clean(para)))
    return tuple(blocks)


def extract_markdown(path: Path) -> list[Page]:
    return [Page(1, markdown_blocks(path.read_text(encoding="utf-8")))]


def extract_html(path: Path) -> list[Page]:
    import trafilatura  # import local : coûteux, et seulement utile pour le HTML

    markdown = trafilatura.extract(
        path.read_text(encoding="utf-8", errors="replace"),
        output_format="markdown",
        include_formatting=True,
    )
    return [Page(1, markdown_blocks(markdown or ""))]


EXTRACTORS = {"pdf": extract_pdf, "html": extract_html, "markdown": extract_markdown}


# --- Corpus -------------------------------------------------------------------------------


def extracted_dir(election_dir: Path) -> Path:
    return election_dir / "sources" / "extracted"


def _to_json(doc: ExtractedDocument) -> dict[str, Any]:
    return asdict(doc)


def _from_json(data: dict[str, Any]) -> ExtractedDocument:
    pages = tuple(
        Page(p["page_number"], tuple(Block(b["kind"], b["text"]) for b in p["blocks"]))
        for p in data["pages"]
    )
    return ExtractedDocument(**{**data, "pages": pages})


class ExtractError(Exception):
    pass


def extract_corpus(election_dir: Path) -> ExtractReport:
    """Extrait chaque document après avoir vérifié son chemin et son sha256 : le texte indexé
    est bien celui du document référencé (URL, sha256) dans `election_config.json`."""
    config = json.loads((election_dir / "election_config.json").read_text(encoding="utf-8"))
    out = extracted_dir(election_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = ExtractReport()
    for entry in config["corpus"]:
        problem = local_path_issue(entry["local_path"])
        if problem:
            raise ExtractError(problem)
        source = election_dir / entry["local_path"]
        if not source.is_file():
            raise ExtractError(f"{entry['local_path']} absent : lancer `pipeline fetch`")
        if hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
            raise ExtractError(f"{entry['local_path']} : sha256 différent de la config")
        pages = EXTRACTORS[entry["type"]](source)
        excluded = not any(p.blocks for p in pages)
        title = entry["document_title"]
        label = f"{entry['candidate_id']} : {title}"  # un titre peut être commun à plusieurs
        if excluded:
            report.excluded.append(label)
        else:
            empty = [p.page_number for p in pages if not p.blocks]
            if empty:
                report.empty_pages[label] = empty
        doc = ExtractedDocument(
            candidate_id=entry["candidate_id"],
            document_title=title,
            source_url=entry["source_url"],
            sha256=entry["sha256"],
            type=entry["type"],
            pages=tuple(pages),
            excluded=excluded,
        )
        path = out / f"{entry['sha256'][:12]}.json"
        path.write_text(json.dumps(_to_json(doc), ensure_ascii=False), encoding="utf-8")
        report.written.append(path)
    return report


def load_extracted_one(election_dir: Path, sha256: str) -> ExtractedDocument | None:
    path = extracted_dir(election_dir) / f"{sha256[:12]}.json"
    if not path.is_file():
        return None
    doc = _from_json(json.loads(path.read_text(encoding="utf-8")))
    return doc if doc.sha256 == sha256 else None


def load_extracted(election_dir: Path) -> list[ExtractedDocument]:
    """Documents extraits, dans l'ordre du corpus (ceux qui manquent sont ignorés)."""
    config = json.loads((election_dir / "election_config.json").read_text(encoding="utf-8"))
    docs = [load_extracted_one(election_dir, e["sha256"]) for e in config["corpus"]]
    return [d for d in docs if d is not None]
