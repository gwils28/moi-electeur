"""Documents du corpus : ajout (`add-source`, PLAN D12) et téléchargement vérifié (`fetch`).

Les fichiers vont dans `data/elections/<id>/sources/` (ignoré par git : les programmes ne sont
pas redistribués) ; seuls l'URL et le sha256 sont versionnés dans `election_config.json`.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .validate import local_path_issue, schema_issues

Fetcher = Callable[[str], bytes]

# Client générique : aucune information sur le mainteneur dans les requêtes.
USER_AGENT = "moi-electeur-pipeline/0.1"
RETRIES = 3
TIMEOUT_S = 120
MAGIC = {"pdf": b"%PDF-"}
EXTENSIONS = {"pdf": ".pdf", "html": ".html", "markdown": ".md"}


class SourceError(Exception):
    pass


def http_fetch(url: str) -> bytes:
    """GET avec quelques reprises (la Wayback Machine limite le débit et renvoie parfois 5xx)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                data: bytes = response.read()
                return data
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == RETRIES:
                raise SourceError(f"{url} : HTTP {exc.code}") from exc
        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            http.client.HTTPException,
        ) as exc:
            if attempt == RETRIES:
                raise SourceError(f"{url} : {exc}") from exc
        time.sleep(5 * attempt)
    raise SourceError(f"{url} : échec")  # pragma: no cover


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _config_path(election_dir: Path) -> Path:
    return election_dir / "election_config.json"


def _read_config(election_dir: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(_config_path(election_dir).read_text(encoding="utf-8"))
    return data


def _write_config(election_dir: Path, config: dict[str, Any]) -> None:
    text = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    _config_path(election_dir).write_text(text, encoding="utf-8")


def _check_content(data: bytes, doc_type: str, url: str) -> None:
    magic = MAGIC.get(doc_type)
    if magic and not data.startswith(magic):
        raise SourceError(f"{url} : le contenu reçu n'est pas un PDF (page d'erreur ?)")
    if not data:
        raise SourceError(f"{url} : contenu vide")


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-") or "document"


def _local_path(url: str, candidate_id: str, doc_type: str, taken: set[str]) -> str:
    """`sources/<candidat>/<nom du fichier d'origine>`, suffixé -2, -3… en cas de collision."""
    name = unquote(Path(urlparse(url).path).name)
    stem = _slug(Path(name).stem)
    ext = EXTENSIONS[doc_type]
    candidate = f"sources/{candidate_id}/{stem}{ext}"
    n = 2
    while candidate in taken:
        candidate = f"sources/{candidate_id}/{stem}-{n}{ext}"
        n += 1
    return candidate


def _write_atomic(path: Path, data: bytes) -> None:
    """Écrit via un fichier temporaire : une interruption ne laisse pas de PDF tronqué."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def add_source(
    election_dir: Path,
    candidate_id: str,
    url: str,
    title: str,
    doc_type: str,
    *,
    fetcher: Fetcher = http_fetch,
    today: date | None = None,
) -> dict[str, Any]:
    """Télécharge le document, calcule son sha256 et ajoute l'entrée au `corpus`."""
    if doc_type not in EXTENSIONS:
        raise SourceError(f"type inconnu : {doc_type} (attendu : {', '.join(EXTENSIONS)})")
    if urlparse(url).scheme not in ("http", "https"):
        raise SourceError(f"URL non HTTP(S) refusée : {url}")
    config = _read_config(election_dir)
    if candidate_id not in {c["id"] for c in config["candidates"]}:
        raise SourceError(f"candidat inconnu : {candidate_id}")
    corpus: list[dict[str, Any]] = config["corpus"]
    if any(d["source_url"] == url for d in corpus):
        raise SourceError(f"URL déjà présente dans le corpus : {url}")

    data = fetcher(url)
    _check_content(data, doc_type, url)
    sha = _sha256(data)
    for d in corpus:
        if d["sha256"] == sha:
            raise SourceError(f"sha256 identique à « {d['document_title']} » : document en double")

    entry = {
        "candidate_id": candidate_id,
        "document_title": title,
        "type": doc_type,
        "source_url": url,
        "local_path": _local_path(url, candidate_id, doc_type, {d["local_path"] for d in corpus}),
        "sha256": sha,
        "retrieved_at": (today or date.today()).isoformat(),
    }
    config["corpus"] = [*corpus, entry]
    issues = schema_issues(config, "election_config.schema.json", "election_config.json")
    if issues:
        raise SourceError("entrée non conforme au schéma :\n" + "\n".join(map(str, issues)))

    _write_atomic(election_dir / entry["local_path"], data)
    _write_config(election_dir, config)
    return entry


@dataclass
class FetchReport:
    downloaded: list[str] = field(default_factory=list)
    present: list[str] = field(default_factory=list)


def fetch_corpus(election_dir: Path, *, fetcher: Fetcher = http_fetch) -> FetchReport:
    """Télécharge les documents manquants et vérifie le sha256 de chacun (idempotent)."""
    report = FetchReport()
    for doc in _read_config(election_dir)["corpus"]:
        problem = local_path_issue(doc["local_path"])
        if problem:
            raise SourceError(problem)
        path = election_dir / doc["local_path"]
        if path.is_file():
            if _sha256(path.read_bytes()) != doc["sha256"]:
                raise SourceError(
                    f"{doc['local_path']} : fichier local altéré (sha256 différent), "
                    "le supprimer puis relancer `fetch`"
                )
            report.present.append(doc["local_path"])
            continue
        data = fetcher(doc["source_url"])
        if _sha256(data) != doc["sha256"]:
            raise SourceError(
                f"{doc['source_url']} : sha256 différent de celui enregistré, "
                "le document distant a changé"
            )
        _write_atomic(path, data)
        report.downloaded.append(doc["local_path"])
    return report
