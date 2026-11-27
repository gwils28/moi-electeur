"""`pipeline build` : JSON statiques servis au front (D5 : générés, non commités).

Seules les positions et mesures validated/corrected sont écrites (CLAUDE.md).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .engine_ref import LOADED_STATUSES, candidate_answers
from .pca import fit_pca
from .validate import Issue, compass_ready, schema_issues, validate_election

SOURCE_FILES = ["election_config.json", "statements.json", "positions.json", "measures.json"]


class BuildError(Exception):
    def __init__(self, issues: list[Issue]) -> None:
        super().__init__("\n".join(map(str, issues)))
        self.issues = issues


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(doc: Any) -> str:
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":"))


def build_election(election_dir: Path, out_root: Path) -> Path:
    """Écrit les JSON du front. Élection « corpus seul » (PLAN D13) ou boussole en préparation
    (affirmations sans positions, M3) : pas de boussole, seule la configuration (candidats,
    thèmes, sources) est publiée, pour l'explorateur (M2d)."""
    issues = validate_election(election_dir)
    if issues:
        raise BuildError(issues)
    election_id = election_dir.name
    if not compass_ready(election_dir):
        target = out_root / election_id
        target.mkdir(parents=True, exist_ok=True)
        # Fichiers d'une boussole publiée auparavant : retirés, sinon le front les chargerait.
        for stale in target.iterdir():
            if stale.is_file() and stale.name != "election_config.json":
                stale.unlink()
        config_doc = _read(election_dir / "election_config.json")
        (target / "election_config.json").write_text(_dump(config_doc), encoding="utf-8")
        return target
    docs = {f: _read(election_dir / f) for f in SOURCE_FILES if (election_dir / f).is_file()}
    config = docs["election_config.json"]
    statements = docs["statements.json"]["statements"]
    positions = [
        p for p in docs["positions.json"]["positions"] if p["review"]["status"] in LOADED_STATUSES
    ]
    measures = [
        m
        for m in docs.get("measures.json", {"measures": []})["measures"]
        if m["review"]["status"] in LOADED_STATUSES
    ]
    ids = [s["id"] for s in statements]
    answers = {c["id"]: candidate_answers(positions, c["id"], ids) for c in config["candidates"]}
    pca = fit_pca(election_id, statements, answers)
    pca_issues = schema_issues(pca, "pca_model.schema.json", "pca_model.json")
    if pca_issues:
        raise BuildError(pca_issues)

    out = {
        "election_config.json": config,
        "statements.json": docs["statements.json"],
        "positions.json": {"election_id": election_id, "positions": positions},
        "measures.json": {"election_id": election_id, "measures": measures},
        "pca_model.json": pca,
    }
    corpus_version = hashlib.sha256(
        b"".join((election_dir / f).read_bytes() for f in docs)
    ).hexdigest()[:16]
    target = out_root / election_id
    target.mkdir(parents=True, exist_ok=True)
    files = []
    for name, doc in out.items():
        text = _dump(doc)
        (target / name).write_text(text, encoding="utf-8")
        files.append({"path": name, "sha256": hashlib.sha256(text.encode()).hexdigest()})
    manifest = {
        "election_id": election_id,
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus_version": corpus_version,
        "files": files,
    }
    manifest_issues = schema_issues(manifest, "manifest.schema.json", "manifest.json")
    if manifest_issues:
        raise BuildError(manifest_issues)
    (target / "manifest.json").write_text(_dump(manifest), encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée autonome (`python -m moi_electeur_pipeline.build [--out DIR]`), utilisé
    par l'image web : n'importe ni la CLI, ni le service de recherche, ni le client Claude."""
    import argparse
    import sys

    from .paths import elections_dir, repo_root

    parser = argparse.ArgumentParser(description="JSON statiques du front (toutes les élections).")
    parser.add_argument(
        "--out", type=Path, default=repo_root() / "apps" / "web" / "public" / "data"
    )
    args = parser.parse_args(argv)
    for d in sorted(p for p in elections_dir().iterdir() if p.is_dir()):
        try:
            written = build_election(d, args.out)
        except BuildError as exc:
            print(f"ÉCHEC {d.name} :\n{exc}", file=sys.stderr)
            return 1
        print(f"Écrit {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
