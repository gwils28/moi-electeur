"""Revue humaine des propositions (PLAN § 5.3, D30, D31).

Logique des applications marimo `review/review_positions.py` et `review/review_measures.py` :
file de revue (signalements d'abord), décisions valider / corriger / rejeter, écriture de
`positions.json` / `measures.json` validée (schémas et contrôles croisés) avant d'être conservée.
Les propositions (`proposals/*.jsonl`) ne sont jamais modifiées : elles gardent la trace de ce
que le modèle a proposé, et `proposed_value` / `proposed` celle de ce que la revue a corrigé.
"""

from __future__ import annotations

import html
import json
import os
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from .propose import (
    _evidence,
    dumps,
    exact_span,
    load_chunk_lookup,
    load_records,
    measure_custom_id,
    position_custom_id,
    proposals_path,
)
from .validate import validate_election

DECISIONS = ("validated", "corrected", "rejected")
REVIEWER_ENV = "MOI_ELECTEUR_REVIEWER"
DEFAULT_REVIEWER = "mainteneur"
UNSET: Any = object()

# Priorité dans la file (plus petit = plus tôt).
POSITION_PRIORITY = {
    "valeur_sans_citation": 0,
    "citation_non_retrouvee": 1,
    "extrait_inconnu": 1,
    "confiance_faible": 2,
}


class ReviewError(Exception):
    pass


def default_reviewer() -> str:
    """Nom écrit dans `review.reviewer` (pseudonyme par défaut : aucune donnée personnelle)."""
    return os.environ.get(REVIEWER_ENV, "").strip() or DEFAULT_REVIEWER


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _config(election_dir: Path) -> dict[str, Any]:
    config: dict[str, Any] = _read(election_dir / "election_config.json")
    return config


# File de revue.


def position_queue(election_dir: Path, *, include_reviewed: bool = False) -> list[dict[str, Any]]:
    """Positions à revoir : signalées d'abord, puis par affirmation et par candidat."""
    config = _config(election_dir)
    statements = _read(election_dir / "statements.json")["statements"]
    s_rank = {s["id"]: i for i, s in enumerate(statements)}
    c_rank = {c["id"]: i for i, c in enumerate(config["candidates"])}
    records = load_records(proposals_path(election_dir, "position"))
    queue = []
    for p in _read(election_dir / "positions.json")["positions"]:
        status = p["review"]["status"]
        if status != "pending" and not include_reviewed:
            continue
        rec = records.get(position_custom_id(p["candidate_id"], p["statement_id"]))
        reasons = list(rec["flags"]) if rec else ["sans proposition"]
        if p["confidence"] == "low" and "confiance_faible" not in reasons:
            reasons.append("confiance_faible")
        priority = min((POSITION_PRIORITY.get(r, 3) for r in reasons), default=4)
        queue.append(
            {
                "candidate_id": p["candidate_id"],
                "statement_id": p["statement_id"],
                "status": status,
                "reasons": reasons,
                "priority": priority,
                "_order": (priority, s_rank[p["statement_id"]], c_rank[p["candidate_id"]]),
            }
        )
    queue.sort(key=lambda e: e["_order"])
    for e in queue:
        del e["_order"]
    return queue


def measure_queue(election_dir: Path, *, include_reviewed: bool = False) -> list[dict[str, Any]]:
    """Mesures à revoir : groupes signalés, puis chiffrages à vérifier, puis le reste."""
    records = load_records(proposals_path(election_dir, "measure"))
    queue = []
    for n, m in enumerate(_read(election_dir / "measures.json")["measures"]):
        status = m["review"]["status"]
        if status != "pending" and not include_reviewed:
            continue
        rec = records.get(measure_custom_id(m["candidate_id"], m["theme"]))
        reasons = list(rec["flags"]) if rec else []
        priority = 0 if reasons else 2
        if m["costing"]["status"] != "intention":
            reasons.append("chiffrage à vérifier")
            priority = min(priority, 1)
        queue.append(
            {
                "id": m["id"],
                "candidate_id": m["candidate_id"],
                "theme": m["theme"],
                "status": status,
                "reasons": reasons,
                "priority": priority,
                "_order": (priority, n),
            }
        )
    queue.sort(key=lambda e: e["_order"])
    for e in queue:
        del e["_order"]
    return queue


def progress(election_dir: Path) -> dict[str, dict[str, int]]:
    out = {}
    for kind, name in (("positions", "positions.json"), ("measures", "measures.json")):
        path = election_dir / name
        items = _read(path)[kind] if path.is_file() else []
        out[kind] = dict(Counter(i["review"]["status"] for i in items))
    return out


# Écriture validée.


def _write_validated(election_dir: Path, name: str, doc: dict[str, Any]) -> None:
    """Écrit le fichier puis le valide avec toute l'élection ; en cas d'échec (problèmes
    trouvés ou exception), rétablit l'ancien contenu : rien n'est conservé."""
    path = election_dir / name
    before = path.read_text(encoding="utf-8")
    tmp = path.with_suffix(".json.tmp")
    try:
        tmp.write_text(dumps(doc, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
        issues = validate_election(election_dir)
    except BaseException:
        path.write_text(before, encoding="utf-8")
        raise
    finally:
        tmp.unlink(missing_ok=True)
    if issues:
        path.write_text(before, encoding="utf-8")
        raise ReviewError("décision refusée : " + "; ".join(map(str, issues)))


def _lookup(election_dir: Path) -> dict[str, dict[str, Any]]:
    try:
        return load_chunk_lookup(election_dir)
    except FileNotFoundError as exc:
        raise ReviewError(
            "texte des extraits absent (sources/chunks.jsonl) : lancer `pipeline chunk`"
        ) from exc


def _check_decision(decision: str, reviewer: str) -> str:
    if decision not in DECISIONS:
        raise ReviewError(f"décision inconnue : {decision} (attendu : {', '.join(DECISIONS)})")
    name = reviewer.strip()
    if not name:
        raise ReviewError("nom du réviseur manquant")
    return name


def _review(decision: str, reviewer: str, on: date, note: str | None) -> dict[str, Any]:
    out: dict[str, Any] = {"status": decision, "reviewer": reviewer, "date": on.isoformat()}
    if note and note.strip():
        out["note"] = note.strip()
    return out


def _candidate_evidence(
    election_dir: Path, candidate_id: str, quotes: list[str]
) -> list[dict[str, Any]]:
    """Citations saisies par le réviseur : chacune doit figurer (à la normalisation près) dans
    un extrait du corpus de ce candidat ; elle est enregistrée telle qu'elle y figure."""
    lookup = _lookup(election_dir)
    mine = [c for c in lookup.values() if c["candidate_id"] == candidate_id]
    out = []
    for quote in quotes:
        found = next(((c, s) for c in mine if (s := exact_span(quote, c["text"]))), None)
        if found is None:
            raise ReviewError(f"citation introuvable dans le corpus de {candidate_id} : {quote}")
        chunk, span = found
        out.append(
            {
                "quote": span,
                "document_title": chunk["document_title"],
                "page": chunk["page_number"],
                "chunk_id": chunk["id"],
            }
        )
    return out


def _original_position(
    election_dir: Path, p: dict[str, Any]
) -> tuple[int | None, list[dict[str, Any]]]:
    """Valeur et citations d'origine (celles écrites depuis la proposition). Tant que la
    position n'est pas corrigée, ce sont les siennes : aucun accès aux sources locales."""
    if p["review"]["status"] != "corrected":
        return p["value"], list(p["evidence"])
    value = p.get("proposed_value")
    rec = load_records(proposals_path(election_dir, "position")).get(
        position_custom_id(p["candidate_id"], p["statement_id"])
    )
    if rec is None or rec["status"] != "ok" or value is None:
        return value, []
    try:
        return value, _evidence(rec["quotes"], _lookup(election_dir), None)
    except KeyError as exc:
        raise ReviewError(f"extrait d'origine introuvable dans sources/ : {exc}") from exc


def review_position(
    election_dir: Path,
    candidate_id: str,
    statement_id: str,
    *,
    decision: str,
    reviewer: str,
    on: date,
    note: str | None = None,
    value: Any = UNSET,
    confidence: str | None = None,
    quotes: list[str] | None = None,
) -> dict[str, Any]:
    """Enregistre une décision ; `value` (entier de -2 à 2 ou None) est requis pour corriger."""
    name = _check_decision(decision, reviewer)
    doc = _read(election_dir / "positions.json")
    index = next(
        (
            i
            for i, p in enumerate(doc["positions"])
            if (p["candidate_id"], p["statement_id"]) == (candidate_id, statement_id)
        ),
        None,
    )
    if index is None:
        raise ReviewError(f"position inconnue : {candidate_id}/{statement_id}")
    p = dict(doc["positions"][index])
    original, original_evidence = _original_position(election_dir, p)
    if decision == "corrected":
        if value is UNSET:
            raise ReviewError("une correction exige une valeur (entier de -2 à 2, ou silence)")
        p["proposed_value"] = original
        p["value"] = value
        if quotes and value is None:
            raise ReviewError("un silence ne prend pas de citation : retirer les citations")
        if quotes:
            p["evidence"] = _candidate_evidence(election_dir, candidate_id, quotes)
        elif p["review"]["status"] != "corrected" and not p["evidence"]:
            p["evidence"] = original_evidence
        if value is None:
            p["evidence"] = []
        elif not p["evidence"]:
            raise ReviewError("valeur sans citation : ajouter une citation du programme")
    else:
        p.pop("proposed_value", None)
        p["value"] = original
        p["evidence"] = original_evidence if original is not None else []
    if confidence is not None:
        p["confidence"] = confidence
    p["review"] = _review(decision, name, on, note)
    doc["positions"][index] = p
    _write_validated(election_dir, "positions.json", doc)
    return p


CORRECTABLE = ("title", "summary", "costing")


def review_measure(
    election_dir: Path,
    measure_id: str,
    *,
    decision: str,
    reviewer: str,
    on: date,
    note: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    costing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Enregistre une décision ; corriger remplace titre, résumé ou chiffrage et conserve
    l'original des champs modifiés dans `proposed` (D30)."""
    name = _check_decision(decision, reviewer)
    doc = _read(election_dir / "measures.json")
    index = next((i for i, m in enumerate(doc["measures"]) if m["id"] == measure_id), None)
    if index is None:
        raise ReviewError(f"mesure inconnue : {measure_id}")
    m = dict(doc["measures"][index])
    original = {k: m.get("proposed", {}).get(k, m[k]) for k in CORRECTABLE}
    for k in CORRECTABLE:
        m[k] = original[k]
    m.pop("proposed", None)
    if decision == "corrected":
        changes = {"title": title, "summary": summary, "costing": costing}
        if costing is not None and costing == original["costing"]:
            costing = None  # chiffrage inchangé : ni réécrit, ni revérifié
        if costing is not None and costing.get("quote"):
            ev = _candidate_evidence(election_dir, m["candidate_id"], [costing["quote"]])[0]
            changes["costing"] = {**costing, "quote": ev["quote"]}
        proposed = {}
        for k, new in changes.items():
            if new is not None and new != original[k]:
                proposed[k] = original[k]
                m[k] = new
        if not proposed:
            raise ReviewError("correction sans changement : valider plutôt")
        m["proposed"] = proposed
    m["review"] = _review(decision, name, on, note)
    doc["measures"][index] = m
    _write_validated(election_dir, "measures.json", doc)
    return m


# Affichage.


def highlight(text: str, quotes: list[str]) -> str:
    """Texte d'un extrait échappé pour le HTML, citations retrouvées entre `<mark>`."""
    spans = sorted(
        {(text.find(s), len(s)) for q in quotes if (s := exact_span(q, text)) and s in text}
    )
    out, pos = [], 0
    for start, length in spans:
        if start < pos:
            continue
        out.append(html.escape(text[pos:start]))
        out.append(f"<mark>{html.escape(text[start : start + length])}</mark>")
        pos = start + length
    out.append(html.escape(text[pos:]))
    return "".join(out)


def pdf_link(chunk: dict[str, Any]) -> str | None:
    """Lien vers la page du document (http ou https seulement)."""
    url = str(chunk.get("source_url") or "")
    if not url.startswith(("https://", "http://")):
        return None
    page = chunk.get("page_number")
    return f"{url}#page={page}" if page else url
