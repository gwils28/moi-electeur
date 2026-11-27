"""Accès à l'API Claude pour l'extraction (PLAN D27, D32) : tarifs, client réel, clé.

Le reste du pipeline ne voit que le protocole `LlmClient` (dictionnaires simples), ce qui permet
de tester l'extraction avec un client simulé : aucun appel réel en CI.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .paths import repo_root


@dataclass(frozen=True)
class Price:
    """Dollars par million de tokens."""

    input: float
    output: float
    cache_read: float
    cache_write: float


# Tarifs publics (claude-api, novembre 2026). L'écriture en cache coûte 1,25 fois l'entrée.
PRICES: dict[str, Price] = {
    "claude-sonnet-5-5": Price(input=2.0, output=10.0, cache_read=0.1, cache_write=2.5),
    "claude-haiku-5-5": Price(input=0.1, output=0.5, cache_read=0.01, cache_write=0.125),
}
BATCH_DISCOUNT = 0.5
# Créer un lot n'est pas idempotent : un nouvel essai après un délai dépassé pourrait créer, et
# facturer, un second lot que `batches.json` ne connaîtrait pas.
BATCH_MAX_RETRIES = 0


class UnknownModelError(Exception):
    pass


def price(model: str) -> Price:
    try:
        return PRICES[model]
    except KeyError:
        raise UnknownModelError(f"modèle sans tarif connu : {model}") from None


def cost_usd(model: str, usage: dict[str, int], *, batch: bool = False) -> float:
    p = price(model)
    total = (
        usage.get("input_tokens", 0) * p.input
        + usage.get("output_tokens", 0) * p.output
        + usage.get("cache_read_input_tokens", 0) * p.cache_read
        + usage.get("cache_creation_input_tokens", 0) * p.cache_write
    ) / 1_000_000
    return total * (BATCH_DISCOUNT if batch else 1.0)


class LlmClient(Protocol):
    def create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Message complet (dictionnaire de l'API) pour une requête Messages."""
        ...

    def submit_batch(self, requests: list[dict[str, Any]]) -> str:
        """Envoie un lot de `{custom_id, params}` ; renvoie l'identifiant du lot."""
        ...

    def batch_status(self, batch_id: str) -> dict[str, Any]:
        """`{status, counts}` ; `status` vaut `ended` une fois le lot terminé."""
        ...

    def batch_results(self, batch_id: str) -> Iterator[dict[str, Any]]:
        """`{custom_id, type, message, error}` par requête d'un lot terminé."""
        ...


class AnthropicClient:
    """Client réel (SDK officiel `anthropic`). Clé lue dans `ANTHROPIC_API_KEY`."""

    def __init__(self) -> None:
        import anthropic

        self._client = anthropic.Anthropic(max_retries=4)

    def create(self, params: dict[str, Any]) -> dict[str, Any]:
        message = self._client.messages.create(**params)
        dumped: dict[str, Any] = message.model_dump(mode="json")
        return dumped

    def submit_batch(self, requests: list[dict[str, Any]]) -> str:
        client = self._client.with_options(max_retries=BATCH_MAX_RETRIES)
        batch = client.messages.batches.create(requests=requests)  # type: ignore[arg-type]
        return batch.id

    def batch_status(self, batch_id: str) -> dict[str, Any]:
        batch = self._client.messages.batches.retrieve(batch_id)
        return {
            "status": batch.processing_status,
            "counts": batch.request_counts.model_dump(mode="json"),
        }

    def batch_results(self, batch_id: str) -> Iterator[dict[str, Any]]:
        for entry in self._client.messages.batches.results(batch_id):
            result = entry.result
            message = None
            error = None
            if result.type == "succeeded":
                message = result.message.model_dump(mode="json")
            elif result.type == "errored":
                error = result.error.model_dump_json()
            else:
                error = result.type
            yield {
                "custom_id": entry.custom_id,
                "type": result.type,
                "message": message,
                "error": error,
            }


def load_api_key(env_file: Path | None = None) -> bool:
    """Charge `ANTHROPIC_API_KEY` depuis `.env` à la racine si elle n'est pas déjà définie.

    La valeur n'est jamais affichée ni journalisée. Renvoie vrai si une clé est disponible.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    path = env_file or repo_root() / ".env"
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key.strip() == "ANTHROPIC_API_KEY":
            value = value.strip().strip('"').strip("'")
            if value:
                os.environ["ANTHROPIC_API_KEY"] = value
                return True
    return False
