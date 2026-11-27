"""Base PostgreSQL éphémère pour les tests marqués `db` (PLAN D19).

Une base `test_<aléa>` est créée sur le serveur de `DATABASE_URL` (Postgres du compose en local,
service container en CI) puis supprimée. Sans serveur joignable : test ignoré en local,
échec en CI (variable `CI`), pour qu'aucun test `db` ne passe inaperçu.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import conninfo, sql

from .db import DEFAULT_DSN


class DatabaseUnavailable(Exception):
    pass


@contextmanager
def temporary_database(admin_dsn: str | None = None) -> Iterator[str]:
    admin_dsn = admin_dsn or os.environ.get("DATABASE_URL", DEFAULT_DSN)
    name = f"test_{secrets.token_hex(6)}"
    try:
        admin = psycopg.connect(admin_dsn, autocommit=True, connect_timeout=3)
    except psycopg.OperationalError as exc:
        raise DatabaseUnavailable(str(exc)) from exc
    with admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        yield conninfo.make_conninfo(admin_dsn, dbname=name)
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
            )
