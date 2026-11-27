"""Propositions de positions et de mesures par Claude (PLAN § 5.2, D24 à D29, D32).

Chaîne : extraits du candidat (recherche hybride du service RAG) -> requête « aveugle » (ni nom
du candidat, ni titre du document) avec sortie structurée -> vérification des citations dans les
extraits fournis -> `proposals/*.jsonl` (versionnés) -> `positions.json` / `measures.json` au
statut `pending`, que la revue humaine (M3c) valide, corrige ou rejette.

Les citations natives de l'API sont incompatibles avec la sortie structurée : chaque citation
est donc recherchée après coup dans son extrait (espaces et apostrophes normalisés).
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .llm import LlmClient, cost_usd
from .paths import repo_root
from .validate import load_registry, schema_issues

MAX_MEASURES = 5
POSITION_K = 6
MEASURE_K = 10
MIN_THEMED = 4  # en deçà, la recherche des mesures se fait sans filtre de thème
MIN_QUOTE_CHARS = 10
MAX_CONSECUTIVE_ERRORS = 3
# Estimation avant envoi (D32) : environ 3 caractères par token en français, sortie forfaitaire
# (réflexion comprise ; pilote 2022 : 172 et 1 141 en moyenne). Coût réel relevé dans `usage`.
CHARS_PER_TOKEN = 3.0
ESTIMATED_OUTPUT = {"position": 500, "measure": 2000}


@dataclass(frozen=True)
class Settings:
    model: str
    effort: str
    max_tokens: int


POSITION_SETTINGS = Settings("claude-sonnet-5-5", "medium", 8192)
MEASURE_SETTINGS = Settings("claude-sonnet-5-5", "medium", 16000)
SETTINGS = {"position": POSITION_SETTINGS, "measure": MEASURE_SETTINGS}
PROMPTS = {"position": "positions_system", "measure": "measures_system"}
SCHEMAS = {
    "position": "position_extraction.schema.json",
    "measure": "measure_extraction.schema.json",
}
RECORD_FILES = {"position": "positions.jsonl", "measure": "measures.jsonl"}
BATCHES_FILE = "batches.json"

# (candidat, requête, thème ou None, k) -> extraits (dictionnaires `chunk`, texte compris).
Retriever = Callable[[str, str, str | None, int], list[dict[str, Any]]]


@dataclass(frozen=True)
class Prompt:
    name: str
    version: int
    text: str


@dataclass(frozen=True)
class Item:
    """Une requête à envoyer : couple (candidat, affirmation) ou (candidat, thème)."""

    kind: str
    custom_id: str
    candidate_id: str
    target: str
    chunks: tuple[dict[str, Any], ...]
    params: dict[str, Any] = field(default_factory=dict)


# Le tiret cadratin est interdit dans les fichiers du dépôt (CLAUDE.md), mais les citations
# exactes des programmes peuvent en contenir : il est écrit échappé (`\\u2014`) dans les JSON,
# ce qui laisse la donnée lue intacte.
EM_DASH = chr(0x2014)


def dumps(doc: Any, indent: int | None = None) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=indent).replace(EM_DASH, "\\u2014")


FRONT_MATTER = re.compile(r"\A---\nversion: (\d+)\n---\n")


def load_prompt(name: str) -> Prompt:
    raw = (repo_root() / "prompts" / f"{name}.md").read_text(encoding="utf-8")
    match = FRONT_MATTER.match(raw)
    if not match:
        raise ValueError(f"prompts/{name}.md : en-tête `version` manquant")
    return Prompt(name, int(match.group(1)), raw[match.end() :].strip())


def output_schema(kind: str) -> dict[str, Any]:
    """Schéma envoyé dans `output_config.format`, tiré de `schemas/` (source unique)."""
    _, schemas = load_registry()
    schema = dict(schemas[SCHEMAS[kind]])
    for key in ("$schema", "$id"):
        schema.pop(key, None)
    return schema


def position_custom_id(candidate_id: str, statement_id: str) -> str:
    return f"p-{candidate_id}-{statement_id}"


def measure_custom_id(candidate_id: str, theme_id: str) -> str:
    return f"m-{candidate_id}-{theme_id}"


def _params(kind: str, settings: Settings, prompt: Prompt, content: str) -> dict[str, Any]:
    return {
        "model": settings.model,
        "max_tokens": settings.max_tokens,
        "system": [{"type": "text", "text": prompt.text, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": content}],
        "thinking": {"type": "adaptive"},
        "output_config": {
            "effort": settings.effort,
            "format": {"type": "json_schema", "schema": output_schema(kind)},
        },
    }


def _extracts_block(chunks: Sequence[dict[str, Any]]) -> str:
    # Texte seul : le titre du document et l'URL révèlent souvent le candidat (extraction aveugle).
    parts = [f'<extrait numero="{n}">\n{c["text"]}\n</extrait>' for n, c in enumerate(chunks, 1)]
    return "<extraits>\n" + "\n".join(parts) + "\n</extraits>"


def _candidates(config: dict[str, Any], wanted: Iterable[str] | None) -> list[str]:
    ids = [c["id"] for c in config["candidates"]]
    if wanted is None:
        return ids
    wanted = set(wanted)
    unknown = sorted(wanted - set(ids))
    if unknown:
        raise ValueError(f"candidat inconnu : {', '.join(unknown)}")
    return [c for c in ids if c in wanted]


def _retrieved(chunks: list[dict[str, Any]], candidate_id: str, target: str) -> tuple[Any, ...]:
    if not chunks:
        raise ValueError(f"{candidate_id}/{target} : aucun extrait (corpus non indexé ?)")
    return tuple(chunks)


def position_items(
    config: dict[str, Any],
    statements: Sequence[dict[str, Any]],
    retriever: Retriever,
    *,
    prompt: Prompt,
    settings: Settings = POSITION_SETTINGS,
    candidates: Iterable[str] | None = None,
    statement_ids: Iterable[str] | None = None,
    done: Iterable[str] = (),
    k: int = POSITION_K,
) -> list[Item]:
    """Une requête par couple (candidat, affirmation) absent de `done` (D24)."""
    skip = set(done)
    keep = set(statement_ids) if statement_ids is not None else None
    items = []
    for cand in _candidates(config, candidates):
        for s in statements:
            custom_id = position_custom_id(cand, s["id"])
            if custom_id in skip or (keep is not None and s["id"] not in keep):
                continue
            chunks = _retrieved(retriever(cand, s["text"], None, k), cand, s["id"])
            content = (
                f"<affirmation>\n{s['text']}\n</affirmation>\n\n{_extracts_block(chunks)}\n\n"
                "Indique l'accord de ces extraits avec l'affirmation, selon les consignes."
            )
            params = _params("position", settings, prompt, content)
            items.append(Item("position", custom_id, cand, s["id"], chunks, params))
    return items


def measure_items(
    config: dict[str, Any],
    retriever: Retriever,
    *,
    prompt: Prompt,
    settings: Settings = MEASURE_SETTINGS,
    candidates: Iterable[str] | None = None,
    done: Iterable[str] = (),
    k: int = MEASURE_K,
) -> list[Item]:
    """Une requête par couple (candidat, thème) absent de `done` (D26)."""
    skip = set(done)
    items = []
    for cand in _candidates(config, candidates):
        for theme in config["themes"]:
            custom_id = measure_custom_id(cand, theme["id"])
            if custom_id in skip:
                continue
            query = f"{theme['label']} : {theme.get('description') or theme['label']}"
            found = retriever(cand, query, theme["id"], k)
            if len(found) < MIN_THEMED:
                found = retriever(cand, query, None, k)
            chunks = _retrieved(found, cand, theme["id"])
            content = (
                f"<theme>\n{query}\n</theme>\n\n{_extracts_block(chunks)}\n\n"
                "Relève les mesures phares de ce thème dans ces extraits, selon les consignes."
            )
            params = _params("measure", settings, prompt, content)
            items.append(Item("measure", custom_id, cand, theme["id"], chunks, params))
    return items


def estimate_cost(items: Sequence[Item], *, batch: bool) -> float:
    total = 0.0
    for item in items:
        chars = len(item.params["system"][0]["text"]) + len(item.params["messages"][0]["content"])
        usage = {
            "input_tokens": int(chars / CHARS_PER_TOKEN) + 200,
            "output_tokens": ESTIMATED_OUTPUT[item.kind],
        }
        total += cost_usd(item.params["model"], usage, batch=batch)
    return total


# Vérifications (D25, D26).

QUOTE_CHARS: dict[int, int | None] = {
    ord("\u2019"): ord("'"),
    ord("\u2018"): ord("'"),
    ord("\u02bc"): ord("'"),
    ord("\u201c"): ord('"'),
    ord("\u201d"): ord('"'),
    ord("\u00ad"): None,
}
SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Forme de comparaison : NFC, apostrophes et guillemets droits, espaces repliées."""
    return SPACES.sub(" ", unicodedata.normalize("NFC", text).translate(QUOTE_CHARS)).strip()


# Césure du PDF (« der-nier », « sociaux-démo- crates ») : le trait d'union entre deux lettres
# est ignoré des deux côtés, pour la comparaison seulement.
HYPHEN = re.compile(r"(?<=\w)- ?(?=\w)")


def _match_form(text: str) -> str:
    return HYPHEN.sub("", normalize(text))


def _found(quote: str, text: str) -> bool:
    q = _match_form(quote)
    return len(q) >= MIN_QUOTE_CHARS and q in _match_form(text)


NUMBER = re.compile(r"(\d{1,3}(?:[ .]\d{3})+|\d+)(?:,(\d+))?")


def parse_amounts(text: str) -> list[float]:
    """Montants lus dans une citation, unités françaises comprises (milliard, Md€, M€…)."""
    t = normalize(text)
    out = []
    for m in NUMBER.finditer(t):
        value = float(re.sub(r"[ .]", "", m.group(1)) + (f".{m.group(2)}" if m.group(2) else ""))
        rest = t[m.end() :].lstrip().lower()
        if rest.startswith(("milliard", "md")):
            value *= 1e9
        elif rest.startswith(("million", "m€", "m d'euros")):
            value *= 1e6
        elif rest.startswith("k€"):
            value *= 1e3
        out.append(value)
    return out


def _amount_quoted(amount: float, quote: str) -> bool:
    return any(abs(a - amount) <= 0.005 * abs(amount) for a in parse_amounts(quote))


def _dedupe(flags: list[str]) -> list[str]:
    return list(dict.fromkeys(flags))


def _check_quotes(
    item: Item, quotes: Sequence[dict[str, Any]], measure: int | None
) -> tuple[list[dict[str, Any]], list[str]]:
    checked, flags = [], []
    for q in quotes:
        n = q["extrait"]
        chunk = item.chunks[n - 1] if 1 <= n <= len(item.chunks) else None
        if chunk is None:
            flags.append("extrait_inconnu")
        verified = chunk is not None and _found(q["text"], chunk["text"])
        checked.append(
            {
                "measure": measure,
                "role": "evidence",
                "chunk_id": chunk["id"] if chunk else None,
                "text": q["text"],
                "verified": verified,
            }
        )
    checked = _merge_adjacent(checked, item)
    if any(not c["verified"] for c in checked):
        flags.append("citation_non_retrouvee")
    return checked, flags


def _merge_adjacent(quotes: list[dict[str, Any]], item: Item) -> list[dict[str, Any]]:
    """Recolle deux citations vérifiées consécutives du même extrait si elles se suivent dans
    le texte (passage coupé par un retour à la ligne du PDF)."""
    texts = {c["id"]: c["text"] for c in item.chunks}
    out: list[dict[str, Any]] = []
    for q in quotes:
        prev = out[-1] if out else None
        if (
            prev is not None
            and prev["verified"]
            and q["verified"]
            and prev["chunk_id"] == q["chunk_id"]
            and _found(f"{prev['text']} {q['text']}", texts[q["chunk_id"]])
        ):
            out[-1] = {**prev, "text": f"{prev['text']} {q['text']}"}
        else:
            out.append(q)
    return out


def _check_position(item: Item, out: dict[str, Any]) -> tuple[str, list[Any], list[str]]:
    quotes, flags = _check_quotes(item, out["quotes"], None)
    status = "ok"
    if out["value"] is not None and not any(q["verified"] for q in quotes):
        flags.append("valeur_sans_citation")
        status = "invalid"
    if out["confidence"] == "low":
        flags.append("confiance_faible")
    return status, quotes, flags


def _check_measures(item: Item, out: dict[str, Any]) -> tuple[str, list[Any], list[str]]:
    quotes: list[dict[str, Any]] = []
    flags: list[str] = []
    measures = out["measures"]
    if len(measures) > MAX_MEASURES:
        flags.append("trop_de_mesures")
    for i, m in enumerate(measures):
        checked, more = _check_quotes(item, m["quotes"], i)
        quotes += checked
        flags += more
        if not any(q["verified"] for q in checked):
            flags.append("mesure_sans_citation")
        c = m["costing"]
        amount, quote = c["amount_eur"], c["quote"]
        if (
            (c["status"] == "chiffre" and (amount is None or quote is None))
            or (c["status"] == "partiel" and (amount is not None or quote is None))
            or (c["status"] == "intention" and (amount is not None or quote is not None))
        ):
            flags.append("chiffrage_incoherent")
        if quote:
            chunk = next((ch for ch in item.chunks if _found(quote, ch["text"])), None)
            quotes.append(
                {
                    "measure": i,
                    "role": "costing",
                    "chunk_id": chunk["id"] if chunk else None,
                    "text": quote,
                    "verified": chunk is not None,
                }
            )
            if chunk is None:
                flags.append("citation_non_retrouvee")
            elif (
                c["status"] == "chiffre"
                and amount is not None
                and not _amount_quoted(amount, quote)
            ):
                flags.append("montant_non_retrouve")
    return "ok", quotes, flags


ZERO_USAGE = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
}


def make_record(
    item: Item,
    response: dict[str, Any] | None,
    *,
    error: str | None = None,
    mode: str,
    batch_id: str | None,
    election_id: str,
    prompt_version: int,
    model: str,
    now: datetime,
) -> dict[str, Any]:
    """Ligne de `proposals/*.jsonl` (schéma `proposal.schema.json`)."""
    usage = dict(ZERO_USAGE)
    output: dict[str, Any] | None = None
    status = "error"
    quotes: list[dict[str, Any]] = []
    flags: list[str] = []
    stop = None
    if response is None:
        error = error or "réponse absente"
    else:
        raw_usage = response.get("usage") or {}
        usage = {key: int(raw_usage.get(key) or 0) for key in ZERO_USAGE}
        stop = response.get("stop_reason")
        text = next((b["text"] for b in response.get("content", []) if b["type"] == "text"), None)
        if stop != "end_turn":
            error = f"arrêt : {stop}"
        elif text is None:
            error = "aucun bloc de texte"
        else:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                error = f"JSON invalide : {exc}"
            else:
                issues = schema_issues(parsed, SCHEMAS[item.kind], "sortie")
                if issues:
                    error = "sortie non conforme : " + "; ".join(map(str, issues))[:500]
                else:
                    output = parsed
                    check = _check_position if item.kind == "position" else _check_measures
                    status, quotes, flags = check(item, parsed)
                    error = None
    return {
        "kind": item.kind,
        "custom_id": item.custom_id,
        "election_id": election_id,
        "candidate_id": item.candidate_id,
        "target": item.target,
        "model": model,
        "prompt_version": prompt_version,
        "mode": mode,
        "batch_id": batch_id,
        "corpus_version": item.chunks[0].get("corpus_version") if item.chunks else None,
        "chunk_ids": [c["id"] for c in item.chunks],
        "status": status,
        "stop_reason": stop,
        "output": output,
        "error": error,
        "flags": _dedupe(flags),
        "quotes": quotes,
        "usage": usage,
        "cost_usd": round(cost_usd(model, usage, batch=mode == "batch"), 6),
        "created_at": now.isoformat(),
    }


# Stockage (D29).


def recheck_records(election_dir: Path, kind: str) -> int:
    """Refait les vérifications (citations, montants, signalements) des propositions déjà
    reçues, sans appel à l'API, après une évolution des règles. Réécrit le fichier ; renvoie le
    nombre de propositions dont le résultat a changé."""
    path = proposals_path(election_dir, kind)
    if not path.is_file():
        return 0
    lookup = load_chunk_lookup(election_dir)
    check = _check_position if kind == "position" else _check_measures
    lines, changed = [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec["output"] is not None:
            chunks = tuple(lookup[cid] for cid in rec["chunk_ids"])
            item = Item(kind, rec["custom_id"], rec["candidate_id"], rec["target"], chunks)
            status, quotes, flags = check(item, rec["output"])
            new = {**rec, "status": status, "quotes": quotes, "flags": _dedupe(flags)}
            if new != rec:
                changed += 1
                rec = new
        lines.append(dumps(rec))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


def proposals_path(election_dir: Path, kind: str) -> Path:
    return election_dir / "proposals" / RECORD_FILES[kind]


def load_records(path: Path) -> dict[str, dict[str, Any]]:
    """Dernière proposition par `custom_id` (le fichier ne fait que s'allonger)."""
    if not path.is_file():
        return {}
    records: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            records[rec["custom_id"]] = rec
    return records


def append_record(path: Path, record: dict[str, Any]) -> None:
    issues = schema_issues(record, "proposal.schema.json", path.name)
    if issues:
        raise ValueError("proposition non conforme : " + "; ".join(map(str, issues)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(dumps(record) + "\n")


def done_ids(records: dict[str, dict[str, Any]], prompt_version: int | None = None) -> set[str]:
    """Propositions acquises ; celles en erreur, ou faites avec une autre version du prompt que
    `prompt_version` (si elle est donnée), sont redemandées (même prompt pour tous)."""
    return {
        cid
        for cid, r in records.items()
        if r["status"] != "error"
        and (prompt_version is None or r["prompt_version"] == prompt_version)
    }


def _election_id(election_dir: Path) -> str:
    config = json.loads((election_dir / "election_config.json").read_text(encoding="utf-8"))
    return str(config["id"])


def run_direct(
    client: LlmClient,
    items: Sequence[Item],
    *,
    election_dir: Path,
    kind: str,
    prompt_version: int,
    now: datetime,
) -> list[dict[str, Any]]:
    """Appels directs (pilote, D28), chaque proposition écrite dès réception (reprise)."""
    path = proposals_path(election_dir, kind)
    election_id = _election_id(election_dir)
    records = []
    consecutive = 0
    for item in items:
        response, error = None, None
        try:
            response = client.create(item.params)
        except Exception as exc:  # erreur d'API : consignée, la requête sera redemandée
            error = f"{type(exc).__name__}: {exc}"[:500]
        rec = make_record(
            item,
            response,
            error=error,
            mode="direct",
            batch_id=None,
            election_id=election_id,
            prompt_version=prompt_version,
            model=item.params["model"],
            now=now,
        )
        append_record(path, rec)
        records.append(rec)
        consecutive = consecutive + 1 if response is None else 0
        if consecutive >= MAX_CONSECUTIVE_ERRORS:
            raise RuntimeError(f"{consecutive} erreurs d'API consécutives : arrêt ({error})")
    return records


def _batches_path(election_dir: Path) -> Path:
    return election_dir / "proposals" / BATCHES_FILE


def _load_batches(election_dir: Path) -> list[dict[str, Any]]:
    path = _batches_path(election_dir)
    if not path.is_file():
        return []
    batches: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["batches"]
    return batches


def _save_batches(election_dir: Path, batches: list[dict[str, Any]]) -> None:
    path = _batches_path(election_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = dumps({"batches": batches}, indent=2)
    path.write_text(doc + "\n", encoding="utf-8")


def pending_ids(election_dir: Path) -> set[str]:
    """Requêtes d'un lot envoyé mais pas encore collecté (jamais renvoyées en double)."""
    return {
        entry["custom_id"]
        for batch in _load_batches(election_dir)
        if not batch["collected"]
        for entry in batch["items"]
    }


def submit_batch(
    client: LlmClient,
    items: Sequence[Item],
    *,
    election_dir: Path,
    kind: str,
    prompt_version: int,
    now: datetime,
) -> str:
    """Envoie un lot (Batch API, -50 %) et consigne de quoi le collecter plus tard (D32)."""
    requests = [{"custom_id": i.custom_id, "params": i.params} for i in items]
    batch_id = client.submit_batch(requests)
    batches = _load_batches(election_dir)
    batches.append(
        {
            "batch_id": batch_id,
            "kind": kind,
            "model": items[0].params["model"],
            "prompt_version": prompt_version,
            "created_at": now.isoformat(),
            "collected": False,
            "items": [
                {
                    "custom_id": i.custom_id,
                    "candidate_id": i.candidate_id,
                    "target": i.target,
                    "chunk_ids": [c["id"] for c in i.chunks],
                }
                for i in items
            ],
        }
    )
    _save_batches(election_dir, batches)
    return batch_id


def load_chunk_lookup(election_dir: Path) -> dict[str, dict[str, Any]]:
    """Extraits du corpus local (`sources/chunks.jsonl`, ignoré par git), par identifiant."""
    path = election_dir / "sources" / "chunks.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"{path} absent : lancer `pipeline chunk`")
    lookup = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            chunk = json.loads(line)
            lookup[chunk["id"]] = chunk
    return lookup


def collect_batches(
    client: LlmClient, election_dir: Path, *, now: datetime
) -> list[tuple[str, str, int]]:
    """Collecte les lots terminés ; renvoie (lot, état, propositions écrites) par lot ouvert."""
    batches = _load_batches(election_dir)
    election_id = _election_id(election_dir)
    report = []
    lookup: dict[str, dict[str, Any]] | None = None
    for batch in batches:
        if batch["collected"]:
            continue
        status = client.batch_status(batch["batch_id"])["status"]
        if status != "ended":
            report.append((batch["batch_id"], status, 0))
            continue
        lookup = lookup if lookup is not None else load_chunk_lookup(election_dir)
        entries = {e["custom_id"]: e for e in batch["items"]}
        path = proposals_path(election_dir, batch["kind"])
        n = 0
        for result in client.batch_results(batch["batch_id"]):
            entry = entries.get(result["custom_id"])
            if entry is None:
                continue
            missing = [cid for cid in entry["chunk_ids"] if cid not in lookup]
            if missing:
                raise KeyError(f"extraits absents du corpus local : {', '.join(missing)}")
            item = Item(
                batch["kind"],
                entry["custom_id"],
                entry["candidate_id"],
                entry["target"],
                tuple(lookup[cid] for cid in entry["chunk_ids"]),
            )
            message = result["message"] if result["type"] == "succeeded" else None
            rec = make_record(
                item,
                message,
                error=result.get("error") or result["type"],
                mode="batch",
                batch_id=batch["batch_id"],
                election_id=election_id,
                prompt_version=batch["prompt_version"],
                model=batch["model"],
                now=now,
            )
            append_record(path, rec)
            n += 1
        batch["collected"] = True
        _save_batches(election_dir, batches)
        report.append((batch["batch_id"], status, n))
    return report


# Écriture des fichiers de la boussole (statut pending).


def _write_json(path: Path, doc: Any) -> None:
    path.write_text(dumps(doc, indent=2) + "\n", encoding="utf-8")


def _evidence(
    quotes: Sequence[dict[str, Any]], lookup: dict[str, dict[str, Any]], measure: int | None
) -> list[dict[str, Any]]:
    out = []
    for q in quotes:
        if q["verified"] and q["role"] == "evidence" and q["measure"] == measure:
            chunk = lookup[q["chunk_id"]]
            out.append(
                {
                    "quote": q["text"],
                    "document_title": chunk["document_title"],
                    "page": chunk["page_number"],
                    "chunk_id": chunk["id"],
                }
            )
    return out


def write_positions(
    election_dir: Path,
    config: dict[str, Any],
    statements: Sequence[dict[str, Any]],
    records: dict[str, dict[str, Any]],
) -> tuple[bool, int]:
    """Écrit `positions.json` si chaque couple a une proposition (sinon : (False, manquants)).

    Les positions déjà revues sont conservées telles quelles ; les autres reprennent la dernière
    proposition. Une proposition refusée par les vérifications devient un silence peu sûr, sans
    citation, que la revue tranchera."""
    path = election_dir / "positions.json"
    existing: dict[tuple[str, str], dict[str, Any]] = {}
    if path.is_file():
        for p in json.loads(path.read_text(encoding="utf-8"))["positions"]:
            existing[(p["candidate_id"], p["statement_id"])] = p
    lookup = load_chunk_lookup(election_dir)
    positions, missing = [], 0
    for cand in _candidates(config, None):
        for s in statements:
            old = existing.get((cand, s["id"]))
            if old is not None and old["review"]["status"] != "pending":
                positions.append(old)
                continue
            rec = records.get(position_custom_id(cand, s["id"]))
            if rec is None or rec["status"] == "error":
                missing += 1
                continue
            out = rec["output"]
            valid = rec["status"] == "ok"
            value = out["value"] if valid else None
            positions.append(
                {
                    "candidate_id": cand,
                    "statement_id": s["id"],
                    "value": value,
                    "confidence": out["confidence"] if valid else "low",
                    "evidence": _evidence(rec["quotes"], lookup, None) if value is not None else [],
                    "proposed_by": f"{rec['model']} positions v{rec['prompt_version']}",
                    "review": {"status": "pending"},
                }
            )
    if missing:
        return False, missing
    _write_json(path, {"election_id": config["id"], "positions": positions})
    return True, 0


def write_measures(
    election_dir: Path, config: dict[str, Any], records: dict[str, dict[str, Any]]
) -> tuple[bool, int]:
    """Écrit `measures.json` (au plus `MAX_MEASURES` mesures citées par couple, identifiants
    `mNNN` dans l'ordre candidat puis thème de la configuration). Exige `positions.json` (une
    élection avec mesures sans positions est refusée par `validate`)."""
    if not (election_dir / "positions.json").is_file():
        return False, 0
    path = election_dir / "measures.json"
    if path.is_file():
        current = json.loads(path.read_text(encoding="utf-8"))["measures"]
        if any(m["review"]["status"] != "pending" for m in current):
            raise ValueError("measures.json contient des mesures revues : réécriture refusée")
    lookup = load_chunk_lookup(election_dir)
    measures, missing = [], 0
    for cand in _candidates(config, None):
        for theme in config["themes"]:
            rec = records.get(measure_custom_id(cand, theme["id"]))
            if rec is None or rec["status"] == "error":
                missing += 1
                continue
            kept = 0
            for i, m in enumerate(rec["output"]["measures"]):
                evidence = _evidence(rec["quotes"], lookup, i)
                if not evidence or kept == MAX_MEASURES:
                    continue
                kept += 1
                measures.append(
                    {
                        "id": "",
                        "candidate_id": cand,
                        "theme": theme["id"],
                        "title": m["title"],
                        "summary": m["summary"],
                        "costing": dict(m["costing"]),
                        "evidence": evidence,
                        "review": {"status": "pending"},
                    }
                )
    if missing:
        return False, missing
    for n, m in enumerate(measures, 1):
        m["id"] = f"m{n:03d}"
    _write_json(path, {"election_id": config["id"], "measures": measures})
    return True, 0


@contextmanager
def open_retriever(election_id: str, model: str, dsn: str | None) -> Iterator[Retriever]:
    """Recherche hybride du service RAG (même code que `/retrieve`) sur la base indexée."""
    from moi_electeur_rag.db import connect
    from moi_electeur_rag.embedding import get_embedder
    from moi_electeur_rag.retrieve import retrieve

    embedder = get_embedder(model)
    with connect(dsn) as conn:

        def search(cand: str, query: str, theme: str | None, k: int) -> list[dict[str, Any]]:
            found = retrieve(
                conn,
                embedder,
                election_id=election_id,
                question=query,
                candidate_ids=[cand],
                theme=theme,
                k=k,
            )
            block = next((b for b in found["candidates"] if b["candidate_id"] == cand), None)
            chunks = [dict(r["chunk"]) for r in block["chunks"]] if block else []
            for c in chunks:
                c.setdefault("corpus_version", found["corpus_version"])
            return chunks

        yield search


# Rapport de relecture (pilote D28, puis revue M3c).


def _value_label(value: int | None) -> str:
    return "silence" if value is None else f"{value:+d}"


def _amount_label(costing: dict[str, Any]) -> str:
    amount = costing["amount_eur"]
    label = str(costing["status"])
    if amount is not None:
        label += f" : {amount:,.0f} €".replace(",", " ")
    if costing["period"]:
        label += f" {costing['period']}"
    return label


def _quote_lines(
    quotes: Iterable[dict[str, Any]], lookup: dict[str, dict[str, Any]], indent: str
) -> list[str]:
    lines = []
    for q in quotes:
        mark = "✅" if q["verified"] else "❌ non retrouvée"
        chunk = lookup.get(q["chunk_id"] or "")
        where = f" (p. {chunk['page_number']})" if chunk else ""
        role = "chiffrage : " if q["role"] == "costing" else ""
        lines.append(f"{indent}- {mark} {role}« {q['text']} »{where}")
    return lines


def render_report(election_dir: Path, kind: str, *, candidates: Iterable[str] | None = None) -> str:
    """Propositions en Markdown, groupées par affirmation (positions) ou par candidat et thème
    (mesures), signalements en clair. Pour relire un pilote ; aucun classement des candidats."""
    config = json.loads((election_dir / "election_config.json").read_text(encoding="utf-8"))
    cands = _candidates(config, candidates)
    names = {c["id"]: c["name"] for c in config["candidates"]}
    themes = {t["id"]: t["label"] for t in config["themes"]}
    records = load_records(proposals_path(election_dir, kind))
    try:
        lookup = load_chunk_lookup(election_dir)
    except FileNotFoundError:
        lookup = {}
    mine = [r for r in records.values() if r["candidate_id"] in cands]
    status = Counter(r["status"] for r in mine)
    flags = Counter(f for r in mine for f in r["flags"])
    title = "positions" if kind == "position" else "mesures"
    out: list[str] = [
        f"# Propositions : {title} ({config['id']})",
        "",
        f"Candidats : {', '.join(names[c] for c in cands)}. "
        f"{len(mine)} propositions ({', '.join(f'{n} {s}' for s, n in sorted(status.items()))}), "
        f"coût {sum(r['cost_usd'] for r in mine):.3f} $.",
    ]
    if flags:
        out.append("Signalements : " + ", ".join(f"{f} {n}" for f, n in sorted(flags.items())))
    if kind == "position":
        statements = json.loads((election_dir / "statements.json").read_text(encoding="utf-8"))
        current = None
        for s in statements["statements"]:
            if s["theme"] != current:
                current = s["theme"]
                out += ["", f"## {themes.get(current, current)}"]
            sens = "+1" if s["direction"] > 0 else "-1"
            out += ["", f"### {s['id']} · {s['text']}", "", f"Axe {s['axis']}, sens {sens}.", ""]
            for cand in cands:
                rec = records.get(position_custom_id(cand, s["id"]))
                if rec is None:
                    out.append(f"- **{names[cand]}** : pas de proposition")
                    continue
                note = f" ⚠️ {', '.join(rec['flags'])}" if rec["flags"] else ""
                if rec["status"] == "error":
                    out.append(f"- **{names[cand]}** : erreur ({rec['error']})")
                    continue
                o = rec["output"]
                head = f"**{_value_label(o['value'])}** (confiance {o['confidence']})"
                if rec["status"] == "invalid":
                    head = f"**refusée** (proposé {_value_label(o['value'])})"
                out.append(f"- **{names[cand]}** : {head}{note}")
                out += _quote_lines(rec["quotes"], lookup, "  ")
                out.append(f"  - _{o['rationale']}_")
    else:
        for cand in cands:
            for theme_id, label in themes.items():
                rec = records.get(measure_custom_id(cand, theme_id))
                if rec is None:
                    continue
                note = f" ⚠️ {', '.join(rec['flags'])}" if rec["flags"] else ""
                out += ["", f"## {names[cand]} · {label}{note}", ""]
                if rec["status"] == "error":
                    out.append(f"Erreur : {rec['error']}")
                    continue
                if not rec["output"]["measures"]:
                    out.append("Aucune mesure relevée.")
                for i, m in enumerate(rec["output"]["measures"]):
                    out.append(f"{i + 1}. **{m['title']}** ({_amount_label(m['costing'])})")
                    out.append(f"   {m['summary']}")
                    out += _quote_lines(
                        (q for q in rec["quotes"] if q["measure"] == i), lookup, "   "
                    )
    return "\n".join(out).replace(EM_DASH, "&#8212;") + "\n"
