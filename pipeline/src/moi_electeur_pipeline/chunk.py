"""`chunk` : découpe des documents extraits en extraits de 300 à 600 tokens (PLAN § 4.2, D17).

Algorithme (déterministe) :
1. Le document devient une suite d'unités : titres et phrases, chacune rattachée à sa page, à
   son paragraphe et au titre de section en cours. Une unité dépasse rarement `max/4` tokens :
   au-delà, elle est coupée en fenêtres de mots.
2. Remplissage glouton : on ferme l'extrait quand l'unité suivante ferait dépasser `max`
   (l'extrait fait alors plus de `3/4 max`, donc plus de `min`), ou à un nouveau titre si
   l'extrait atteint déjà `min`. Après une coupure par la taille, les dernières phrases
   (`overlap` tokens au plus) sont reprises au début de l'extrait suivant.
3. Le dernier extrait d'un document, s'il est sous `min`, est fusionné avec le précédent
   quand la somme tient dans `max`. C'est le seul extrait qui peut rester sous `min`.

Un extrait ne couvre jamais deux documents. Chaque extrait est validé par
`schemas/chunk.schema.json` avant écriture dans `sources/chunks.jsonl`.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path
from typing import Any

from .extract import ExtractedDocument, load_extracted_one
from .validate import schema_issues

TokenCounter = Callable[[str], int]
TOKENIZER_NAME = "FacebookAI/xlm-roberta-base"
SECTION_MAX_CHARS = 200  # au-delà, les titres consécutifs ne sont plus fusionnés
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


class ChunkError(Exception):
    pass


@dataclass(frozen=True)
class ChunkParams:
    min_tokens: int = 300
    max_tokens: int = 600
    overlap_tokens: int = 50

    def __post_init__(self) -> None:
        if not 0 <= self.overlap_tokens < self.min_tokens:
            raise ValueError("il faut 0 <= overlap_tokens < min_tokens")
        if self.min_tokens > self.max_tokens * 3 // 4:
            raise ValueError("il faut min_tokens <= 3/4 de max_tokens (garantie de taille)")

    @property
    def unit_max(self) -> int:
        return self.max_tokens // 4


@cache
def xlmr_counter() -> TokenCounter:
    """Compteur XLM-RoBERTa (tokenizer commun à bge-m3 et multilingual-e5, PLAN D17).

    Téléchargé une fois depuis le Hub Hugging Face (quelques Mo, mis en cache).
    """
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_pretrained(TOKENIZER_NAME)

    def count(text: str) -> int:
        return len(tokenizer.encode(text, add_special_tokens=False).ids)

    return count


@dataclass(frozen=True)
class _Unit:
    text: str
    tokens: int
    page: int
    section: str | None
    para_start: bool  # premier morceau d'un paragraphe (ou titre)
    heading: bool


def _split_long(text: str, count: TokenCounter, limit: int) -> list[str]:
    """Coupe une phrase trop longue en fenêtres de mots d'au plus `limit` tokens."""
    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for word in text.split():
        n = count(word)
        if current and size + n > limit:
            pieces.append(" ".join(current))
            current, size = [], 0
        current.append(word)
        size += n
    if current:
        pieces.append(" ".join(current))
    return pieces


def _units(doc: ExtractedDocument, count: TokenCounter, params: ChunkParams) -> list[_Unit]:
    units: list[_Unit] = []
    section: str | None = None
    previous_heading = False
    for page in doc.pages:
        for block in page.blocks:
            if block.kind == "heading":
                # Un titre sur plusieurs blocs consécutifs forme un seul titre de section.
                merged = f"{section} {block.text}"
                fits = previous_heading and len(merged) <= SECTION_MAX_CHARS
                section = merged if fits else block.text
                sentences = [block.text]
            else:
                sentences = [s for s in SENTENCE_END.split(block.text) if s]
            first = True
            for sentence in sentences:
                pieces = (
                    [sentence]
                    if count(sentence) <= params.unit_max
                    else _split_long(sentence, count, params.unit_max)
                )
                for piece in pieces:
                    units.append(
                        _Unit(
                            text=piece,
                            tokens=count(piece),
                            page=page.page_number,
                            section=section,
                            para_start=first,
                            heading=block.kind == "heading",
                        )
                    )
                    first = False
            previous_heading = block.kind == "heading"
    return units


@dataclass
class _Draft:
    units: list[_Unit]
    n_overlap: int  # nombre d'unités reprises de l'extrait précédent

    @property
    def tokens(self) -> int:
        return sum(u.tokens for u in self.units)

    @property
    def own(self) -> list[_Unit]:
        return self.units[self.n_overlap :]


def _pack(units: list[_Unit], params: ChunkParams) -> list[_Draft]:
    drafts: list[_Draft] = []
    current = _Draft([], 0)

    def close(carry: bool) -> None:
        nonlocal current
        drafts.append(current)
        tail: list[_Unit] = []
        if carry:
            size = 0
            for unit in reversed(current.units):
                if size + unit.tokens > params.overlap_tokens:
                    break
                tail.insert(0, unit)
                size += unit.tokens
        current = _Draft(tail, len(tail))

    for unit in units:
        has_own = bool(current.own)
        if unit.heading and unit.para_start and has_own and current.tokens >= params.min_tokens:
            close(carry=False)
        elif has_own and current.tokens + unit.tokens > params.max_tokens:
            close(carry=True)
        current.units.append(unit)
    if current.own:
        drafts.append(current)

    if len(drafts) >= 2 and drafts[-1].tokens < params.min_tokens:
        last, prev = drafts[-1], drafts[-2]
        if prev.tokens + sum(u.tokens for u in last.own) <= params.max_tokens:
            drafts[-2:] = [_Draft(prev.units + last.own, prev.n_overlap)]
    return drafts


def _section(draft: _Draft) -> str | None:
    """Section du premier passage de texte propre à l'extrait (titre complet s'il commence
    par un titre sur plusieurs blocs), à défaut celle de sa première unité."""
    for unit in draft.own:
        if not unit.heading:
            return unit.section
    return draft.own[0].section


def _join(units: Iterable[_Unit]) -> str:
    parts: list[str] = []
    for i, unit in enumerate(units):
        if i:
            parts.append("\n\n" if unit.para_start else " ")
        parts.append(unit.text)
    return "".join(parts)


def chunk_document(
    doc: ExtractedDocument,
    *,
    election_id: str,
    corpus_version: str,
    count: TokenCounter,
    params: ChunkParams,
) -> list[dict[str, Any]]:
    if doc.excluded:
        return []
    chunks = []
    for i, draft in enumerate(_pack(_units(doc, count, params), params)):
        text = _join(draft.units)
        chunk = {
            "id": f"{doc.sha256[:12]}-{i:04d}",
            "election_id": election_id,
            "candidate_id": doc.candidate_id,
            "document_title": doc.document_title,
            "source_url": doc.source_url,
            "document_sha256": doc.sha256,
            "page_number": draft.units[0].page,
            "page_end": draft.units[-1].page,
            "section_title": _section(draft),
            "theme": None,
            "text": text,
            "token_count": count(text),
            "corpus_version": corpus_version,
        }
        validate_chunk(chunk)
        chunks.append(chunk)
    return chunks


def validate_chunk(chunk: dict[str, Any]) -> None:
    """Rejette un extrait non conforme au schéma ou incohérent (métadonnées obligatoires)."""
    problems = [str(i) for i in schema_issues(chunk, "chunk.schema.json", "chunk")]
    if not problems and chunk["page_end"] < chunk["page_number"]:
        problems.append("page_end antérieur à page_number")
    if problems:
        raise ChunkError(f"extrait {chunk.get('id', '?')} invalide : " + "; ".join(problems))


def compute_corpus_version(
    sha256s: Iterable[str], params: ChunkParams, tokenizer: str, content: str = ""
) -> str:
    """Empreinte des documents, des paramètres et du contenu des extraits.

    Le contenu (`content`, empreinte des extraits : texte et toutes les métadonnées) fait changer la version quand le code
    d'extraction ou de découpage évolue à documents et paramètres constants.
    """
    payload = {
        "documents": sorted(sha256s),
        "params": [params.min_tokens, params.max_tokens, params.overlap_tokens],
        "tokenizer": tokenizer,
        "content": content,
    }
    raw = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


@dataclass
class ChunkReport:
    path: Path
    corpus_version: str
    chunks_per_candidate: dict[str, int]
    skipped: list[str]


def chunk_corpus(
    election_dir: Path,
    *,
    count: TokenCounter | None = None,
    params: ChunkParams | None = None,
    tokenizer_name: str = TOKENIZER_NAME,
) -> ChunkReport:
    params = params or ChunkParams()
    count = count or xlmr_counter()
    config = json.loads((election_dir / "election_config.json").read_text(encoding="utf-8"))
    docs: list[ExtractedDocument] = []
    for entry in config["corpus"]:
        extracted = load_extracted_one(election_dir, entry["sha256"])
        # Attribution et références prises dans la config courante, jamais dans l'extraction
        # (un titre corrigé ou une réaffectation ne doit pas exiger de relancer `extract`).
        doc = extracted and replace(
            extracted,
            candidate_id=entry["candidate_id"],
            document_title=entry["document_title"],
            source_url=entry["source_url"],
        )
        if doc is None:
            raise ChunkError(
                f"« {entry['document_title']} » n'est pas extrait : lancer `pipeline extract`"
            )
        docs.append(doc)
    kept = [d for d in docs if not d.excluded]
    pending = "0" * 16  # remplacée une fois l'empreinte du contenu connue
    chunks = [
        c
        for d in kept
        for c in chunk_document(
            d, election_id=config["id"], corpus_version=pending, count=count, params=params
        )
    ]
    digest = hashlib.sha256()
    for c in chunks:
        fields = {k: v for k, v in c.items() if k != "corpus_version"}
        digest.update(json.dumps(fields, ensure_ascii=False, sort_keys=True).encode())
    version = compute_corpus_version(
        (d.sha256 for d in kept), params, tokenizer_name, digest.hexdigest()
    )
    for c in chunks:
        c["corpus_version"] = version
    path = election_dir / "sources" / "chunks.jsonl"
    path.write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks), encoding="utf-8"
    )
    per_candidate = Counter(c["candidate_id"] for c in chunks)
    return ChunkReport(
        path=path,
        corpus_version=version,
        chunks_per_candidate=dict(per_candidate),
        skipped=[d.document_title for d in docs if d.excluded],
    )
