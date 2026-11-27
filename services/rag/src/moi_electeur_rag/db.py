"""Connexion PostgreSQL (psycopg 3 + pgvector) et migrations SQL versionnées (PLAN D18)."""

from __future__ import annotations

import os
from importlib import resources
from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

# Valeurs du docker-compose de développement (aucun secret de production ici).
DEFAULT_DSN = "postgresql://moi_electeur:dev-only-password@localhost:5432/moi_electeur"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DSN)


def connect(dsn: str | None = None) -> psycopg.Connection[dict[str, Any]]:
    conn = psycopg.connect(dsn or database_url(), row_factory=dict_row)
    try:
        register_vector(conn)
    except psycopg.ProgrammingError:
        # Extension `vector` pas encore créée (base neuve avant `migrate`).
        conn.rollback()
    return conn


def migrations() -> list[tuple[str, str]]:
    """(version, SQL) des scripts `sql/NNN_*.sql`, dans l'ordre."""
    files = sorted(
        (f for f in resources.files("moi_electeur_rag").joinpath("sql").iterdir()),
        key=lambda f: f.name,
    )
    return [(f.name.removesuffix(".sql"), f.read_text(encoding="utf-8")) for f in files]


MIGRATION_LOCK = 72_022_027  # clé du verrou consultatif des migrations


def migrate(dsn: str | None = None) -> list[str]:
    """Applique les migrations manquantes, chacune dans sa propre transaction (une migration en
    échec n'annule pas les précédentes) ; renvoie les versions appliquées.

    Un verrou consultatif sérialise les `db-migrate` concurrents (CI, déploiement).
    """
    applied: list[str] = []
    with psycopg.connect(dsn or database_url(), row_factory=dict_row, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK,))
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            done = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}
            for version, script in migrations():
                if version in done:
                    continue
                with conn.transaction():
                    conn.execute(script.encode())
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
                applied.append(version)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK,))
    return applied
