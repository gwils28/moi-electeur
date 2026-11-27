import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Revue des positions")


@app.cell
def _():
    import json
    import os
    from datetime import date
    from pathlib import Path

    import marimo as mo

    from moi_electeur_pipeline.paths import elections_dir
    from moi_electeur_pipeline.propose import (
        load_chunk_lookup,
        load_records,
        position_custom_id,
        proposals_path,
    )
    from moi_electeur_pipeline.review import (
        ReviewError,
        default_reviewer,
        highlight,
        pdf_link,
        position_queue,
        progress,
        review_position,
    )

    election = Path(
        os.environ.get("MOI_ELECTEUR_ELECTION") or elections_dir() / "fr-presidentielle-2022"
    )
    config = json.loads((election / "election_config.json").read_text(encoding="utf-8"))
    statements = {
        s["id"]: s
        for s in json.loads((election / "statements.json").read_text(encoding="utf-8"))[
            "statements"
        ]
    }
    candidates = {c["id"]: c for c in config["candidates"]}
    try:
        lookup = load_chunk_lookup(election)
    except FileNotFoundError:
        lookup = {}
    return (
        ReviewError,
        candidates,
        date,
        default_reviewer,
        election,
        highlight,
        json,
        load_records,
        lookup,
        mo,
        pdf_link,
        position_custom_id,
        position_queue,
        progress,
        proposals_path,
        review_position,
        statements,
    )


@app.cell
def _(mo):
    mo.md(
        """
        # Revue des positions (M3c)

        Chaque position proposée par Claude est **validée**, **corrigée** ou **rejetée** ;
        la décision est écrite aussitôt dans `positions.json`, après validation de toute
        l'élection (un enregistrement invalide est refusé et rien n'est modifié). La file
        présente d'abord les propositions signalées. La proposition d'origine reste dans
        `proposals/positions.jsonl`.
        """
    )
    return


@app.cell
def _(mo):
    get_refresh, set_refresh = mo.state(0)
    get_index, set_index = mo.state(0)
    get_message, set_message = mo.state("")
    return get_index, get_message, get_refresh, set_index, set_message, set_refresh


@app.cell
def _(default_reviewer, mo):
    reviewer = mo.ui.text(value=default_reviewer(), label="Réviseur")
    include_reviewed = mo.ui.checkbox(label="Inclure les positions déjà revues")
    blind = mo.ui.checkbox(label="Masquer le nom du candidat")
    mo.hstack([reviewer, include_reviewed, blind], justify="start")
    return blind, include_reviewed, reviewer


@app.cell
def _(election, get_refresh, include_reviewed, mo, position_queue, progress):
    get_refresh()
    queue = position_queue(election, include_reviewed=include_reviewed.value)
    counts = progress(election)["positions"]
    total = sum(counts.values())
    done = total - counts.get("pending", 0)
    mo.md(f"**Avancement** : {done} / {total} positions revues ; {len(queue)} dans la file.")
    return (queue,)


@app.cell
def _(get_index, mo, queue, set_index):
    def _move(step):
        set_index(lambda i: max(0, min(len(queue) - 1, i + step)) if queue else 0)

    previous = mo.ui.button(label="← Précédente", on_click=lambda _: _move(-1))
    following = mo.ui.button(label="Suivante →", on_click=lambda _: _move(1))
    position_index = min(get_index(), max(len(queue) - 1, 0))
    mo.hstack(
        [previous, following, mo.md(f"{position_index + 1 if queue else 0} / {len(queue)}")],
        justify="start",
    )
    return (position_index,)


@app.cell
def _(
    blind,
    candidates,
    election,
    load_records,
    position_custom_id,
    position_index,
    proposals_path,
    queue,
    statements,
):
    import json as _json

    entry = queue[position_index] if queue else None
    current = proposal = None
    if entry is not None:
        _positions = _json.loads((election / "positions.json").read_text(encoding="utf-8"))
        current = next(
            p
            for p in _positions["positions"]
            if (p["candidate_id"], p["statement_id"])
            == (entry["candidate_id"], entry["statement_id"])
        )
        proposal = load_records(proposals_path(election, "position")).get(
            position_custom_id(entry["candidate_id"], entry["statement_id"])
        )
    statement = statements[entry["statement_id"]] if entry else None
    who = None
    if entry is not None:
        _c = candidates[entry["candidate_id"]]
        who = _c["blind_alias"] if blind.value else f"{_c['name']} ({_c['party']})"
    return current, entry, proposal, statement, who


@app.cell
def _(current, entry, mo, proposal, statement, who):
    def _label(v):
        return "silence" if v is None else f"{v:+d}"

    if entry is None:
        view = mo.md("**File vide** : toutes les positions de la file sont revues.")
    else:
        _out = (proposal or {}).get("output") or {}
        _flags = ", ".join(entry["reasons"]) or "aucun"
        _proposed = current.get("proposed_value", current["value"])
        _conf = _out.get("confidence", current["confidence"])
        if proposal is not None and proposal["status"] == "invalid":
            _proposal_label = (
                f"**refusée par les vérifications** (le modèle proposait "
                f"{_label(_out.get('value'))}, confiance {_conf}) ; écrite en silence"
            )
        else:
            _proposal_label = f"**{_label(_proposed)}** (confiance {_conf})"
        view = mo.md(
            f"""
            ## {statement["id"]} · {statement["text"]}

            Axe {statement["axis"]}, sens {statement["direction"]:+d}, poids {statement["weight_in_axis"]}.

            | | |
            |---|---|
            | Candidat | **{who}** |
            | Valeur proposée | {_proposal_label} |
            | Valeur actuelle | {_label(current["value"])} ; statut **{current["review"]["status"]}** |
            | Signalements | {_flags} |
            | Proposition | {current["proposed_by"]} ; {proposal["status"] if proposal else "absente"} |

            > {_out.get("rationale", "")}
            """
        )
    view
    return


@app.cell
def _(current, entry, highlight, lookup, mo, pdf_link, proposal):
    if entry is None:
        extracts = mo.md("")
    else:
        _quotes = [e["quote"] for e in current["evidence"]] + [
            q["text"] for q in (proposal or {}).get("quotes", [])
        ]
        _items = {}
        for _n, _cid in enumerate((proposal or {}).get("chunk_ids", []), 1):
            _chunk = lookup.get(_cid)
            if _chunk is None:
                _items[f"Extrait {_n} (texte absent : sources/chunks.jsonl)"] = mo.md("")
                continue
            _link = pdf_link(_chunk)
            _title = f"Extrait {_n} · {_chunk['document_title']} · p. {_chunk['page_number']}"
            _body = highlight(_chunk["text"], _quotes)
            _source = (
                f'<p><a href="{_link}" target="_blank" rel="noopener">Ouvrir la page</a></p>'
                if _link
                else ""
            )
            _items[_title] = mo.Html(f"<div style='white-space: pre-wrap'>{_body}</div>{_source}")
        _cited = (
            "\n".join(
                f"- {'✅' if q['verified'] else '❌ non retrouvée'} « {q['text']} »"
                for q in (proposal or {}).get("quotes", [])
            )
            or "_aucune_"
        )
        extracts = mo.vstack(
            [
                mo.md(f"**Citations proposées**\n\n{_cited}"),
                mo.md("**Extraits fournis au modèle** (citations surlignées)"),
                mo.accordion(_items, multiple=True) if _items else mo.md("_aucun_"),
            ]
        )
    extracts
    return


@app.cell
def _(entry, mo):
    value = mo.ui.dropdown(
        options=["+2", "+1", "0", "-1", "-2", "silence"], value=None, label="Valeur corrigée"
    )
    confidence = mo.ui.dropdown(
        options=["high", "medium", "low"], value=None, label="Confiance (facultatif)"
    )
    quotes = mo.ui.text_area(
        label="Citations corrigées (une par ligne, recopiées du programme ; vide : inchangées)",
        full_width=True,
    )
    note = mo.ui.text_area(label="Note de revue (facultative)", full_width=True)
    form = mo.vstack([mo.hstack([value, confidence], justify="start"), quotes, note])
    form if entry is not None else mo.md("")
    return confidence, note, quotes, value


@app.cell
def _(
    ReviewError,
    confidence,
    date,
    election,
    entry,
    mo,
    note,
    quotes,
    review_position,
    reviewer,
    set_message,
    set_refresh,
    value,
):
    def _decide(decision):
        if entry is None:
            return
        kwargs = {"note": note.value or None}
        if decision == "corrected":
            if value.value is None:
                set_message("⚠️ Choisir la valeur corrigée.")
                return
            kwargs["value"] = None if value.value == "silence" else int(value.value)
            kwargs["confidence"] = confidence.value
            lines = [x.strip() for x in quotes.value.splitlines() if x.strip()]
            kwargs["quotes"] = lines or None
        try:
            review_position(
                election,
                entry["candidate_id"],
                entry["statement_id"],
                decision=decision,
                reviewer=reviewer.value,
                on=date.today(),
                **kwargs,
            )
        except ReviewError as exc:
            set_message(f"⚠️ {exc}")
            return
        set_message(f"✅ {entry['candidate_id']}/{entry['statement_id']} : {decision}.")
        set_refresh(lambda n: n + 1)

    validate_button = mo.ui.button(
        label="Valider", kind="success", on_click=lambda _: _decide("validated")
    )
    correct_button = mo.ui.button(
        label="Corriger", kind="warn", on_click=lambda _: _decide("corrected")
    )
    reject_button = mo.ui.button(
        label="Rejeter", kind="danger", on_click=lambda _: _decide("rejected")
    )
    (
        mo.hstack([validate_button, correct_button, reject_button], justify="start")
        if entry is not None
        else mo.md("")
    )
    return


@app.cell
def _(get_message, mo):
    mo.md(get_message())
    return


if __name__ == "__main__":
    app.run()
