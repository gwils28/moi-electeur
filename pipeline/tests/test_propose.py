"""Extraction des positions et des mesures (PLAN § 5.2, D24 à D29, D32), avec client simulé.

Aucun appel réel : le client et la recherche sont des doublures. Les données sont celles de la
démo fictive (6 candidats, 30 affirmations, 6 thèmes), privées de leurs positions et mesures.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from moi_electeur_pipeline.build import build_election
from moi_electeur_pipeline.demo import build_demo
from moi_electeur_pipeline.llm import BATCH_DISCOUNT, UnknownModelError, cost_usd
from moi_electeur_pipeline.propose import (
    MAX_MEASURES,
    MEASURE_SETTINGS,
    POSITION_SETTINGS,
    Item,
    collect_batches,
    done_ids,
    estimate_cost,
    load_prompt,
    load_records,
    make_record,
    measure_items,
    normalize,
    output_schema,
    parse_amounts,
    pending_ids,
    position_items,
    proposals_path,
    run_direct,
    submit_batch,
    write_measures,
    write_positions,
)
from moi_electeur_pipeline.validate import schema_issues, validate_election

NOW = datetime(2026, 11, 28, 10, 0, tzinfo=UTC)
CORPUS = "abcdef0123456789"


# Données : démo sans positions ni mesures, et quelques extraits par candidat.


def _chunk(cand: str, n: int, text: str, theme: str | None = None) -> dict[str, Any]:
    return {
        "id": f"{cand}{'0' * 10}-{n:04d}",
        "election_id": "demo-fictive",
        "candidate_id": cand,
        "document_title": f"Programme de Nom{cand.upper()}",
        "source_url": f"https://example.org/{cand}.pdf",
        "document_sha256": cand * 32,
        "page_number": n + 1,
        "page_end": n + 1,
        "section_title": None,
        "theme": theme,
        "text": text,
        "token_count": len(text.split()),
        "corpus_version": CORPUS,
    }


def _chunks(cand: str) -> list[dict[str, Any]]:
    return [
        _chunk(cand, 0, "Nous créerons un impôt sur la fortune financière dès 2027.", "economie"),
        _chunk(
            cand, 1, "L’âge de départ sera ramené à 60 ans. Coût : 10 milliards d'euros par an."
        ),
        _chunk(cand, 2, "Nous construirons six réacteurs nucléaires.", "ecologie"),
    ]


@pytest.fixture
def election(tmp_path: Path) -> Path:
    docs = build_demo()
    del docs["positions.json"], docs["measures.json"]
    target = tmp_path / "demo-fictive"
    target.mkdir()
    for name, doc in docs.items():
        (target / name).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    (target / "sources").mkdir()
    lines = [json.dumps(c, ensure_ascii=False) for cand in _cands(target) for c in _chunks(cand)]
    (target / "sources" / "chunks.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _read(election: Path, name: str) -> Any:
    return json.loads((election / name).read_text(encoding="utf-8"))


def _cands(election: Path) -> list[str]:
    return [c["id"] for c in _read(election, "election_config.json")["candidates"]]


def retriever(cand: str, query: str, theme: str | None, k: int) -> list[dict[str, Any]]:
    chunks = [c for c in _chunks(cand) if theme is None or c["theme"] == theme]
    return chunks[:k]


# Client simulé : réponses construites à partir des extraits du message.


EXTRACT = re.compile(r'<extrait numero="(\d+)">\n(.*?)\n</extrait>', re.S)


def extracts(params: dict[str, Any]) -> list[str]:
    return [m.group(2) for m in EXTRACT.finditer(params["messages"][0]["content"])]


def message(out: Any, *, stop: str = "end_turn", raw: str | None = None) -> dict[str, Any]:
    text = raw if raw is not None else json.dumps(out, ensure_ascii=False)
    return {
        "stop_reason": stop,
        "content": [{"type": "thinking", "thinking": "…"}, {"type": "text", "text": text}],
        "usage": {
            "input_tokens": 5000,
            "output_tokens": 1000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }


def position_reply(params: dict[str, Any]) -> dict[str, Any]:
    first = extracts(params)[0]
    return message(
        {
            "value": 1,
            "confidence": "high",
            "quotes": [{"extrait": 1, "text": first}],
            "rationale": "L'extrait va dans le sens de l'affirmation.",
        }
    )


def measure_reply(params: dict[str, Any]) -> dict[str, Any]:
    return message(
        {
            "measures": [
                {
                    "title": "Ramener l'âge de départ à 60 ans",
                    "summary": "L'âge légal de départ serait ramené à 60 ans.",
                    "costing": {
                        "status": "chiffre",
                        "amount_eur": 1e10,
                        "period": "par an",
                        "quote": "Coût : 10 milliards d'euros par an.",
                    },
                    "quotes": [{"extrait": 2, "text": "L'âge de départ sera ramené à 60 ans."}],
                }
            ]
        }
    )


class FakeClient:
    def __init__(self, reply: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        self.reply = reply
        self.calls: list[dict[str, Any]] = []
        self.batches: dict[str, list[dict[str, Any]]] = {}
        self.status = "ended"

    def create(self, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(params)
        return self.reply(params)

    def submit_batch(self, requests: list[dict[str, Any]]) -> str:
        batch_id = f"msgbatch_{len(self.batches)}"
        self.batches[batch_id] = requests
        return batch_id

    def batch_status(self, batch_id: str) -> dict[str, Any]:
        return {"status": self.status, "counts": {"succeeded": len(self.batches[batch_id])}}

    def batch_results(self, batch_id: str) -> Iterator[dict[str, Any]]:
        for r in self.batches[batch_id]:
            yield {
                "custom_id": r["custom_id"],
                "type": "succeeded",
                "message": self.reply(r["params"]),
                "error": None,
            }


def _position_items(election: Path, **kw: Any) -> list[Item]:
    statements = _read(election, "statements.json")["statements"]
    return position_items(
        _read(election, "election_config.json"),
        statements,
        retriever,
        prompt=load_prompt("positions_system"),
        **kw,
    )


def _measure_items(election: Path, **kw: Any) -> list[Item]:
    return measure_items(
        _read(election, "election_config.json"),
        retriever,
        prompt=load_prompt("measures_system"),
        **kw,
    )


def _record(item: Item, response: dict[str, Any] | None, **kw: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "mode": "direct",
        "batch_id": None,
        "election_id": "demo-fictive",
        "prompt_version": 1,
        "model": POSITION_SETTINGS.model,
        "now": NOW,
    }
    return make_record(item, response, **{**args, **kw})


def _position(value: int | None, quotes: list[dict[str, Any]], conf: str = "high") -> Any:
    return message({"value": value, "confidence": conf, "quotes": quotes, "rationale": "R."})


# Prompts et requêtes.


def test_prompts_versionnes() -> None:
    for name in ("positions_system", "measures_system"):
        prompt = load_prompt(name)
        assert prompt.version >= 1
        assert not prompt.text.startswith("---") and "version:" not in prompt.text


def test_requete_position_aveugle(election: Path) -> None:
    items = _position_items(election, candidates=["c1"])
    assert len(items) == 30 and items[0].custom_id == "p-c1-s01"
    params = items[0].params
    assert params["model"] == "claude-sonnet-5-5"
    assert params["thinking"] == {"type": "adaptive"}
    assert params["output_config"]["effort"] == "medium"
    assert params["output_config"]["format"] == {
        "type": "json_schema",
        "schema": output_schema("position"),
    }
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}
    content = params["messages"][0]["content"]
    statement = _read(election, "statements.json")["statements"][0]["text"]
    assert statement in content
    assert extracts(params) == [c["text"] for c in _chunks("c1")]
    config = _read(election, "election_config.json")
    name = next(c["name"] for c in config["candidates"] if c["id"] == "c1")
    assert name not in json.dumps(params, ensure_ascii=False)
    assert "Programme de" not in content  # titre du document (souvent révélateur) absent


def test_schemas_de_sortie_compatibles_avec_la_sortie_structuree() -> None:
    forbidden = {"minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems", "$id"}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            assert not forbidden & node.keys(), node
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False, node
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for kind in ("position", "measure"):
        schema = output_schema(kind)
        walk(schema)
        assert "$schema" not in schema


def test_affirmations_et_candidats_filtres(election: Path) -> None:
    items = _position_items(election, candidates=["c2", "c1"])
    assert {i.candidate_id for i in items} == {"c1", "c2"} and len(items) == 60
    assert not _position_items(election, candidates=["c1"], done={i.custom_id for i in items})


def test_candidat_inconnu_refuse(election: Path) -> None:
    with pytest.raises(ValueError, match="inconnu"):
        _position_items(election, candidates=["c99"])


# Vérification des citations (D25).


def test_normalisation() -> None:
    assert normalize("L’âge  de départ\n sera") == "L'âge de départ sera"
    assert normalize(" « oui » ") == "« oui »"


def test_citation_verifiee_a_espaces_et_apostrophes_pres(election: Path) -> None:
    item = _position_items(election, candidates=["c1"])[0]
    quote = {"extrait": 2, "text": "L'âge de départ sera ramené  à 60 ans."}
    rec = _record(item, _position(2, [quote]))
    assert rec["status"] == "ok" and rec["flags"] == []
    assert rec["quotes"] == [
        {
            "measure": None,
            "role": "evidence",
            "chunk_id": item.chunks[1]["id"],
            "text": "L’âge de départ sera ramené à 60 ans.",  # empan exact de l'extrait
            "verified": True,
        }
    ]
    assert rec["chunk_ids"] == [c["id"] for c in item.chunks]
    assert rec["corpus_version"] == CORPUS
    assert schema_issues(rec, "proposal.schema.json", "proposal") == []


def test_citation_absente_signalee(election: Path) -> None:
    item = _position_items(election, candidates=["c1"])[0]
    good = {"extrait": 1, "text": item.chunks[0]["text"]}
    bad = {"extrait": 1, "text": "Une phrase qui ne figure pas dans l'extrait."}
    rec = _record(item, _position(1, [good, bad]))
    assert rec["status"] == "ok"
    assert rec["flags"] == ["citation_non_retrouvee"]
    assert [q["verified"] for q in rec["quotes"]] == [True, False]


def test_citation_trop_courte_non_verifiee(election: Path) -> None:
    item = _position_items(election, candidates=["c1"])[0]
    rec = _record(item, _position(1, [{"extrait": 1, "text": "impôt"}]))
    assert rec["status"] == "invalid"
    assert "valeur_sans_citation" in rec["flags"]


def test_valeur_sans_citation_refusee(election: Path) -> None:
    item = _position_items(election, candidates=["c1"])[0]
    rec = _record(item, _position(2, []))
    assert rec["status"] == "invalid" and rec["flags"] == ["valeur_sans_citation"]


def test_silence_sans_citation_accepte(election: Path) -> None:
    item = _position_items(election, candidates=["c1"])[0]
    rec = _record(item, _position(None, []))
    assert rec["status"] == "ok" and rec["flags"] == []


def test_extrait_inconnu_signale(election: Path) -> None:
    item = _position_items(election, candidates=["c1"])[0]
    good = {"extrait": 1, "text": item.chunks[0]["text"]}
    rec = _record(item, _position(1, [good, {"extrait": 9, "text": "Texte quelconque ici."}]))
    assert set(rec["flags"]) == {"extrait_inconnu", "citation_non_retrouvee"}
    assert rec["quotes"][1]["chunk_id"] is None


def test_confiance_faible_signalee(election: Path) -> None:
    item = _position_items(election, candidates=["c1"])[0]
    rec = _record(item, _position(None, [], conf="low"))
    assert rec["flags"] == ["confiance_faible"]


@pytest.mark.parametrize(
    "response",
    [
        message(None, stop="max_tokens", raw='{"value": 1'),
        message(None, stop="refusal", raw=""),
        message(None, raw="pas du JSON"),
        message({"value": 5, "confidence": "high", "quotes": [], "rationale": "R."}),
        None,
    ],
)
def test_sortie_inexploitable_en_erreur(election: Path, response: dict[str, Any] | None) -> None:
    item = _position_items(election, candidates=["c1"])[0]
    rec = _record(item, response, error=None if response else "overloaded_error")
    assert rec["status"] == "error" and rec["output"] is None and rec["error"]
    assert schema_issues(rec, "proposal.schema.json", "proposal") == []
    assert done_ids({rec["custom_id"]: rec}) == set()  # redemandée au prochain lancement


# Coût (D32).


def test_cout_reel_et_remise_batch() -> None:
    usage = {
        "input_tokens": 5000,
        "output_tokens": 1000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    assert cost_usd("claude-sonnet-5-5", usage) == pytest.approx(0.02)
    assert cost_usd("claude-sonnet-5-5", usage, batch=True) == pytest.approx(0.02 * BATCH_DISCOUNT)
    cached = {**usage, "input_tokens": 0, "cache_read_input_tokens": 1_000_000}
    assert cost_usd("claude-sonnet-5-5", cached) == pytest.approx(0.01 + 0.1)
    with pytest.raises(UnknownModelError):
        cost_usd("modele-inconnu", usage)


def test_estimation_du_cout(election: Path) -> None:
    items = _position_items(election, candidates=["c1", "c2"])
    direct = estimate_cost(items, batch=False)
    assert 0.1 < direct < 5
    assert estimate_cost(items, batch=True) == pytest.approx(direct * BATCH_DISCOUNT)


# Appels directs (pilote) et lots.


def test_appels_directs_ecrits_et_repris(election: Path) -> None:
    client = FakeClient(position_reply)
    items = _position_items(election, candidates=["c1"])
    records = run_direct(
        client, items, election_dir=election, kind="position", prompt_version=1, now=NOW
    )
    assert len(client.calls) == 30 and all(r["status"] == "ok" for r in records)
    stored = load_records(proposals_path(election, "position"))
    assert set(stored) == {i.custom_id for i in items}
    for rec in stored.values():
        assert schema_issues(rec, "proposal.schema.json", "proposal") == []
        assert rec["mode"] == "direct" and rec["cost_usd"] == pytest.approx(0.02)
    assert not _position_items(election, candidates=["c1"], done=done_ids(stored))


def test_lot_soumis_puis_collecte(election: Path) -> None:
    client = FakeClient(position_reply)
    items = _position_items(election, candidates=["c1"])
    batch_id = submit_batch(
        client, items, election_dir=election, kind="position", prompt_version=1, now=NOW
    )
    assert client.calls == [] and len(client.batches[batch_id]) == 30
    assert client.batches[batch_id][0] == {"custom_id": "p-c1-s01", "params": items[0].params}
    assert pending_ids(election) == {i.custom_id for i in items}
    assert not load_records(proposals_path(election, "position"))

    client.status = "in_progress"
    assert collect_batches(client, election, now=NOW) == [(batch_id, "in_progress", 0)]
    assert not load_records(proposals_path(election, "position"))

    client.status = "ended"
    assert collect_batches(client, election, now=NOW) == [(batch_id, "ended", 30)]
    stored = load_records(proposals_path(election, "position"))
    assert len(stored) == 30
    rec = stored["p-c1-s01"]
    assert rec["mode"] == "batch" and rec["batch_id"] == batch_id and rec["status"] == "ok"
    assert rec["cost_usd"] == pytest.approx(0.01)
    assert pending_ids(election) == set()
    assert collect_batches(client, election, now=NOW) == []  # déjà collecté


def test_lot_erreur_individuelle_redemandee(election: Path) -> None:
    client = FakeClient(position_reply)
    items = _position_items(election, candidates=["c1"])[:2]
    batch_id = submit_batch(
        client, items, election_dir=election, kind="position", prompt_version=1, now=NOW
    )

    def results(_: str) -> Iterator[dict[str, Any]]:
        yield {"custom_id": "p-c1-s01", "type": "errored", "message": None, "error": "overloaded"}
        yield {"custom_id": "p-c1-s02", "type": "expired", "message": None, "error": None}

    client.batch_results = results  # type: ignore[method-assign]
    collect_batches(client, election, now=NOW)
    stored = load_records(proposals_path(election, "position"))
    assert {r["status"] for r in stored.values()} == {"error"}
    assert done_ids(stored) == set() and pending_ids(election) == set()
    assert batch_id


# Écriture de positions.json (D29).


def _all_positions(election: Path) -> dict[str, dict[str, Any]]:
    client = FakeClient(position_reply)
    run_direct(
        client,
        _position_items(election),
        election_dir=election,
        kind="position",
        prompt_version=1,
        now=NOW,
    )
    return load_records(proposals_path(election, "position"))


def _write_positions(election: Path, records: dict[str, dict[str, Any]]) -> tuple[bool, int]:
    return write_positions(
        election,
        _read(election, "election_config.json"),
        _read(election, "statements.json")["statements"],
        records,
    )


def test_positions_incompletes_non_ecrites(election: Path) -> None:
    records = _all_positions(election)
    records.pop("p-c1-s01")
    assert _write_positions(election, records) == (False, 1)
    assert not (election / "positions.json").exists()


def test_positions_ecrites_en_attente_et_valides(election: Path, tmp_path: Path) -> None:
    records = _all_positions(election)
    assert _write_positions(election, records) == (True, 0)
    positions = _read(election, "positions.json")["positions"]
    assert len(positions) == 180
    p = positions[0]
    assert (p["candidate_id"], p["statement_id"], p["value"]) == ("c1", "s01", 1)
    assert p["review"] == {"status": "pending"}
    assert p["proposed_by"] == "claude-sonnet-5-5 positions v1"
    assert p["evidence"] == [
        {
            "quote": _chunks("c1")[0]["text"],
            "document_title": "Programme de NomC1",
            "page": 1,
            "chunk_id": _chunks("c1")[0]["id"],
        }
    ]
    assert validate_election(election) == []
    # Positions en attente de revue : aucune boussole publiée (configuration seule).
    target = build_election(election, tmp_path / "out")
    assert sorted(f.name for f in target.iterdir()) == ["election_config.json"]


def test_position_invalide_ecrite_en_silence_peu_sure(election: Path) -> None:
    records = _all_positions(election)
    item = _position_items(election, candidates=["c1"])[0]
    records[item.custom_id] = _record(item, _position(2, []))
    _write_positions(election, records)
    p = _read(election, "positions.json")["positions"][0]
    assert (p["value"], p["confidence"], p["evidence"]) == (None, "low", [])


def test_positions_revues_conservees(election: Path) -> None:
    records = _all_positions(election)
    _write_positions(election, records)
    doc = _read(election, "positions.json")
    doc["positions"][0]["review"] = {"status": "validated", "reviewer": "w", "date": "2026-11-28"}
    doc["positions"][0]["value"] = 2
    (election / "positions.json").write_text(json.dumps(doc), encoding="utf-8")
    item = _position_items(election, candidates=["c1"])[0]
    records[item.custom_id] = _record(item, _position(None, []))
    records["p-c1-s02"] = _record(
        _position_items(election, candidates=["c1"])[1], _position(None, [])
    )
    _write_positions(election, records)
    positions = _read(election, "positions.json")["positions"]
    assert positions[0]["value"] == 2 and positions[0]["review"]["status"] == "validated"
    assert positions[1]["value"] is None  # en attente : remplacée par la dernière proposition


# Mesures (D26).


def test_requete_mesures_filtre_de_theme_et_repli(election: Path) -> None:
    items = _measure_items(election, candidates=["c1"])
    assert len(items) == 6 and items[0].custom_id == "m-c1-economie"
    params = items[0].params
    assert params["max_tokens"] == MEASURE_SETTINGS.max_tokens
    assert params["output_config"]["format"]["schema"] == output_schema("measure")
    # Un seul extrait classé « economie » (< 4) : repli sur la recherche sans filtre de thème.
    assert len(items[0].chunks) == 3
    config = _read(election, "election_config.json")
    theme = config["themes"][0]
    assert (
        f"{theme['label']} : {theme.get('description') or theme['label']}"
        in (params["messages"][0]["content"])
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Coût : 10 milliards d'euros par an.", 1e10),
        ("soit 1,5 milliard d’euros", 1.5e9),
        ("pour 500 millions d'euros", 5e8),
        ("un budget de 12 Md€", 1.2e10),
        ("environ 200 M€ par an", 2e8),
        ("une prime de 1 000 euros", 1000.0),
        ("une prime de 1 000 €", 1000.0),
        ("50 000 000 000 €", 5e10),
    ],
)
def test_montants_lus_dans_la_citation(text: str, expected: float) -> None:
    assert expected in parse_amounts(text)


def _measure_record(election: Path, measures: list[dict[str, Any]]) -> dict[str, Any]:
    item = _measure_items(election, candidates=["c1"])[0]
    return _record(item, message({"measures": measures}))


def _measure(**over: Any) -> dict[str, Any]:
    base = measure_reply({})
    m: dict[str, Any] = json.loads(base["content"][1]["text"])["measures"][0]
    return {**m, **over}


def test_montant_verifie(election: Path) -> None:
    rec = _measure_record(election, [_measure()])
    assert rec["status"] == "ok" and rec["flags"] == []
    roles = [(q["measure"], q["role"], q["verified"]) for q in rec["quotes"]]
    assert roles == [(0, "evidence", True), (0, "costing", True)]


def test_montant_absent_de_la_citation_signale(election: Path) -> None:
    costing = {**_measure()["costing"], "amount_eur": 2e10}
    rec = _measure_record(election, [_measure(costing=costing)])
    assert rec["flags"] == ["montant_non_retrouve"]


def test_citation_du_chiffrage_absente_signalee(election: Path) -> None:
    costing = {**_measure()["costing"], "quote": "Coût : 10 milliards d'euros sur cinq ans."}
    rec = _measure_record(election, [_measure(costing=costing)])
    assert set(rec["flags"]) == {"citation_non_retrouvee"}


@pytest.mark.parametrize(
    "costing",
    [
        {"status": "chiffre", "amount_eur": None, "period": None, "quote": None},
        {"status": "intention", "amount_eur": 1e9, "period": None, "quote": None},
        {"status": "partiel", "amount_eur": 1e9, "period": None, "quote": None},
    ],
)
def test_chiffrage_incoherent_signale(election: Path, costing: dict[str, Any]) -> None:
    rec = _measure_record(election, [_measure(costing=costing)])
    assert "chiffrage_incoherent" in rec["flags"]


def test_mesure_sans_citation_signalee(election: Path) -> None:
    rec = _measure_record(election, [_measure(quotes=[])])
    assert rec["flags"] == ["mesure_sans_citation"]


def test_trop_de_mesures_signale(election: Path) -> None:
    rec = _measure_record(election, [_measure() for _ in range(MAX_MEASURES + 2)])
    assert rec["flags"] == ["trop_de_mesures"]


def _all_measures(election: Path, reply: Callable[[dict[str, Any]], dict[str, Any]]) -> Any:
    run_direct(
        FakeClient(reply),
        _measure_items(election),
        election_dir=election,
        kind="measure",
        prompt_version=1,
        now=NOW,
    )
    return load_records(proposals_path(election, "measure"))


def test_mesures_ecrites_identifiants_deterministes(election: Path) -> None:
    records = _all_measures(election, measure_reply)
    config = _read(election, "election_config.json")
    assert write_measures(election, config, records) == (False, 0)  # positions d'abord
    _write_positions(election, _all_positions(election))
    assert write_measures(election, config, records) == (True, 0)
    first = _read(election, "measures.json")
    measures = first["measures"]
    assert len(measures) == 36
    assert [m["id"] for m in measures[:3]] == ["m001", "m002", "m003"]
    assert (measures[0]["candidate_id"], measures[0]["theme"]) == ("c1", "economie")
    assert (measures[1]["candidate_id"], measures[1]["theme"]) == ("c1", "social")
    assert measures[0]["costing"]["amount_eur"] == 1e10
    assert measures[0]["review"] == {"status": "pending"}
    assert measures[0]["evidence"][0]["chunk_id"] == _chunks("c1")[1]["id"]
    assert validate_election(election) == []
    write_measures(election, config, records)
    assert _read(election, "measures.json") == first


def test_mesures_filtrees_a_l_ecriture(election: Path) -> None:
    _write_positions(election, _all_positions(election))

    def reply(params: dict[str, Any]) -> dict[str, Any]:
        return message({"measures": [_measure(quotes=[])] + [_measure()] * (MAX_MEASURES + 1)})

    records = _all_measures(election, reply)
    write_measures(election, _read(election, "election_config.json"), records)
    measures = _read(election, "measures.json")["measures"]
    assert len(measures) == 36 * MAX_MEASURES  # 5 par couple, sans la mesure non citée


def test_mesures_incompletes_non_ecrites(election: Path) -> None:
    _write_positions(election, _all_positions(election))
    records = _all_measures(election, measure_reply)
    records.pop("m-c1-economie")
    config = _read(election, "election_config.json")
    assert write_measures(election, config, records) == (False, 1)


# CLI (D32) : estimation, plafond, confirmation, pilote, lot puis collecte.


@pytest.fixture
def cli(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    from contextlib import contextmanager

    from moi_electeur_pipeline import cli as cli_module

    state: dict[str, Any] = {"client": None}

    @contextmanager
    def fake_open(election_id: str, model: str, dsn: str | None) -> Iterator[Any]:
        yield retriever

    def fake_client() -> FakeClient:
        reply = state["reply"]
        state["client"] = state["client"] or FakeClient(reply)
        return state["client"]

    monkeypatch.setattr(cli_module, "open_retriever", fake_open)
    monkeypatch.setattr(cli_module, "make_client", fake_client)
    monkeypatch.setattr(cli_module, "load_api_key", lambda: True)
    state["reply"] = position_reply
    yield state


def _invoke(*args: str) -> Any:
    from typer.testing import CliRunner

    from moi_electeur_pipeline.cli import app

    return CliRunner().invoke(app, list(args))


def test_cli_estimation_sans_envoi(election: Path, cli: dict[str, Any]) -> None:
    result = _invoke("propose-positions", str(election), "--dry-run")
    assert result.exit_code == 0, result.output
    assert "180 requêtes" in result.output and "$" in result.output
    assert cli["client"] is None


def test_cli_confirmation_obligatoire(election: Path, cli: dict[str, Any]) -> None:
    result = _invoke("propose-positions", str(election), "--candidates", "c1", "--pilot")
    assert result.exit_code == 1 and "--yes" in result.output
    assert cli["client"] is None and not (election / "proposals").exists()


def test_cli_plafond_de_cout(election: Path, cli: dict[str, Any]) -> None:
    result = _invoke("propose-positions", str(election), "--max-usd", "0.01", "--yes")
    assert result.exit_code == 1 and "plafond" in result.output
    assert cli["client"] is None


def test_cli_pilote_puis_reprise(election: Path, cli: dict[str, Any]) -> None:
    args = ["propose-positions", str(election), "--candidates", "c1,c2", "--pilot", "--yes"]
    result = _invoke(*args)
    assert result.exit_code == 0, result.output
    assert len(cli["client"].calls) == 60
    assert "60 ok" in result.output and "manquent" in result.output
    assert not (election / "positions.json").exists()
    again = _invoke(*args)
    assert again.exit_code == 0 and "Rien à demander" in again.output
    assert len(cli["client"].calls) == 60


def test_cli_lot_puis_collecte_et_ecriture(election: Path, cli: dict[str, Any]) -> None:
    result = _invoke("propose-positions", str(election), "--yes")
    assert result.exit_code == 0, result.output
    assert "msgbatch_0" in result.output and cli["client"].calls == []
    assert not _invoke("propose-positions", str(election), "--yes").output.count("msgbatch_1")
    status = _invoke("batch-status", str(election))
    assert status.exit_code == 0, status.output
    assert "msgbatch_0" in status.output and "180" in status.output
    assert "positions.json écrit" in status.output
    assert validate_election(election) == []


def test_cli_mesures_pilote(election: Path, cli: dict[str, Any]) -> None:
    cli["reply"] = measure_reply
    result = _invoke("propose-measures", str(election), "--candidates", "c1", "--pilot", "--yes")
    assert result.exit_code == 0, result.output
    assert len(cli["client"].calls) == 6
    assert len(load_records(proposals_path(election, "measure"))) == 6


def test_rapport_de_relecture(election: Path) -> None:
    from moi_electeur_pipeline.propose import render_report

    _all_positions(election)
    item = _position_items(election, candidates=["c2"])[0]
    path = proposals_path(election, "position")
    from moi_electeur_pipeline.propose import append_record

    append_record(path, _record(item, _position(2, [])))
    report = render_report(election, "position", candidates=["c1", "c2"])
    statement = _read(election, "statements.json")["statements"][0]
    assert f"### s01 · {statement['text']}" in report
    assert "**+1**" in report and "✅" in report
    assert "valeur_sans_citation" in report and "refusée" in report
    _all_measures(election, measure_reply)
    measures = render_report(election, "measure", candidates=["c1"])
    assert "Ramener l'âge de départ à 60 ans" in measures and "10 000 000 000 €" in measures


def test_propositions_d_une_autre_version_redemandees(election: Path) -> None:
    item = _position_items(election, candidates=["c1"])[0]
    old = _record(item, _position(None, []), prompt_version=1)
    assert done_ids({old["custom_id"]: old}, prompt_version=1) == {old["custom_id"]}
    assert done_ids({old["custom_id"]: old}, prompt_version=2) == set()


def test_citations_adjacentes_recollees(election: Path) -> None:
    item = _position_items(election, candidates=["c1"])[1]  # extrait 2 : deux phrases
    first = {"extrait": 2, "text": "L’âge de départ sera ramené à 60 ans."}
    second = {"extrait": 2, "text": "Coût : 10 milliards d'euros par an."}
    other = {"extrait": 1, "text": item.chunks[0]["text"]}
    rec = _record(item, _position(2, [first, second, other]))
    assert [q["text"] for q in rec["quotes"]] == [
        "L’âge de départ sera ramené à 60 ans. Coût : 10 milliards d'euros par an.",
        item.chunks[0]["text"],
    ]
    assert all(q["verified"] for q in rec["quotes"])


def test_cesure_du_pdf_ignoree(election: Path) -> None:
    item = _position_items(election, candidates=["c1"])[0]
    chunk = {
        **item.chunks[0],
        "text": "Le Parlement aura le der-nier mot, avec les sociaux-démo- crates.",
    }
    hyphenated = Item(item.kind, item.custom_id, item.candidate_id, item.target, (chunk,))
    quotes = [
        {"extrait": 1, "text": "Le Parlement aura le dernier mot, avec les sociaux-démocrates."}
    ]
    rec = _record(hyphenated, _position(2, quotes))
    assert rec["status"] == "ok" and rec["quotes"][0]["verified"]
    # Stockée telle qu'elle figure dans le document (sous-chaîne exacte), césures comprises.
    assert rec["quotes"][0]["text"] == chunk["text"]


def test_reverification_sans_appel(election: Path) -> None:
    from moi_electeur_pipeline.propose import recheck_records

    _all_positions(election)
    path = proposals_path(election, "position")
    lines = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["quotes"][0]["verified"] = False
    first["flags"] = ["citation_non_retrouvee"]
    lines[0] = json.dumps(first, ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert recheck_records(election, "position") == 1
    rec = load_records(path)[first["custom_id"]]
    assert rec["quotes"][0]["verified"] and rec["flags"] == []
    assert rec["cost_usd"] == first["cost_usd"] and rec["created_at"] == first["created_at"]
    assert len(path.read_text(encoding="utf-8").splitlines()) == len(lines)
    assert recheck_records(election, "position") == 0


def test_tiret_cadratin_des_programmes_echappe(election: Path) -> None:
    """Une citation exacte peut contenir U+2014 (interdit dans les fichiers du dépôt) : il est
    écrit échappé dans les JSON (même donnée une fois lue) et en entité HTML dans les rapports."""
    em = chr(0x2014)
    item = _position_items(election, candidates=["c1"])[0]
    chunk = {**item.chunks[0], "text": f"Nous interdirons les néonicotinoïdes {em} insecticides."}
    lookup_path = election / "sources" / "chunks.jsonl"
    lines = lookup_path.read_text(encoding="utf-8").splitlines()
    lines[0] = json.dumps(chunk, ensure_ascii=False)
    lookup_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    records = _all_positions(election)
    quote = {"extrait": 1, "text": chunk["text"]}
    from moi_electeur_pipeline.propose import append_record, render_report

    rec = _record(Item(item.kind, item.custom_id, "c1", "s01", (chunk,)), _position(1, [quote]))
    append_record(proposals_path(election, "position"), rec)
    records[rec["custom_id"]] = rec
    _write_positions(election, records)
    for path in (proposals_path(election, "position"), election / "positions.json"):
        assert em not in path.read_text(encoding="utf-8")
    assert (
        _read(election, "positions.json")["positions"][0]["evidence"][0]["quote"] == chunk["text"]
    )
    report = render_report(election, "position", candidates=["c1"])
    assert em not in report and "&#8212;" in report


@pytest.mark.parametrize(
    ("text", "expected"),
    [("soit 2.5 milliards d'euros", 2.5e9), ("pour 10 M euros", 1e7), ("12 Md euros", 1.2e10)],
)
def test_montants_decimaux_et_unites(text: str, expected: float) -> None:
    assert expected in parse_amounts(text)


def _measures_with(election: Path, measure: dict[str, Any]) -> list[dict[str, Any]]:
    _write_positions(election, _all_positions(election))
    records = _all_measures(election, lambda _: message({"measures": [measure]}))
    write_measures(election, _read(election, "election_config.json"), records)
    return list(_read(election, "measures.json")["measures"])


def test_chiffrage_signale_ramene_a_intention(election: Path) -> None:
    costing = {**_measure()["costing"], "amount_eur": 2e10}  # montant absent de la citation
    m = _measures_with(election, _measure(costing=costing))[0]
    assert m["costing"] == {
        "status": "intention",
        "amount_eur": None,
        "period": None,
        "quote": None,
    }


def test_chiffrage_verifie_conserve_et_cite(election: Path) -> None:
    m = _measures_with(election, _measure())[0]
    assert m["costing"]["status"] == "chiffre" and m["costing"]["amount_eur"] == 1e10
    assert m["costing"]["quote"] == "Coût : 10 milliards d'euros par an."
    pages = [(e["quote"], e["page"]) for e in m["evidence"]]
    assert ("Coût : 10 milliards d'euros par an.", 2) in pages  # page du chiffrage visible


def test_mesures_revues_non_reecrites_sans_erreur(election: Path, cli: dict[str, Any]) -> None:
    _measures_with(election, _measure())
    doc = _read(election, "measures.json")
    doc["measures"][0]["review"] = {"status": "validated", "reviewer": "w", "date": "2026-11-28"}
    (election / "measures.json").write_text(json.dumps(doc), encoding="utf-8")
    result = _invoke("batch-status", str(election))
    assert result.exit_code == 0, result.output
    assert "mesures revues" in result.output
    assert _read(election, "measures.json") == doc


def test_boussole_publiable_une_fois_tout_revu(election: Path) -> None:
    from moi_electeur_pipeline.validate import compass_ready

    assert not compass_ready(election)
    _write_positions(election, _all_positions(election))
    assert not compass_ready(election)
    doc = _read(election, "positions.json")
    for p in doc["positions"]:
        p["review"] = {"status": "validated", "reviewer": "w", "date": "2026-11-28"}
    (election / "positions.json").write_text(json.dumps(doc), encoding="utf-8")
    assert compass_ready(election)


def test_cle_lue_dans_env_sans_affichage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from moi_electeur_pipeline.llm import load_api_key

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    env = tmp_path / ".env"
    assert not load_api_key(env)
    env.write_text('AUTRE=1\nANTHROPIC_API_KEY="sk-test-123"\n', encoding="utf-8")
    assert load_api_key(env)
    import os

    assert os.environ["ANTHROPIC_API_KEY"] == "sk-test-123"
    out = capsys.readouterr()
    assert "sk-test" not in out.out + out.err


def test_lot_cree_sans_nouvelle_tentative() -> None:
    from moi_electeur_pipeline.llm import BATCH_MAX_RETRIES

    assert BATCH_MAX_RETRIES == 0  # un nouvel essai pourrait créer (et facturer) un second lot


def test_erreur_tronquee(election: Path) -> None:
    item = _position_items(election, candidates=["c1"])[0]
    rec = _record(item, None, error="x" * 5000)
    assert len(rec["error"]) <= 500
