import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Revue des mesures")


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
        measure_custom_id,
        proposals_path,
    )
    from moi_electeur_pipeline.review import (
        ReviewError,
        default_reviewer,
        highlight,
        measure_queue,
        pdf_link,
        progress,
        review_measure,
    )

    election = Path(
        os.environ.get("MOI_ELECTEUR_ELECTION") or elections_dir() / "fr-presidentielle-2022"
    )
    config = json.loads((election / "election_config.json").read_text(encoding="utf-8"))
    candidates = {c["id"]: c for c in config["candidates"]}
    themes = {t["id"]: t["label"] for t in config["themes"]}
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
        measure_custom_id,
        measure_queue,
        mo,
        pdf_link,
        progress,
        proposals_path,
        review_measure,
        themes,
    )


@app.cell
def _(mo):
    mo.md(
        """
        # Revue des mesures (M3c)

        Chaque mesure phare proposée par Claude est **validée**, **corrigée** (titre, résumé,
        chiffrage) ou **rejetée** ; la décision est écrite aussitôt dans `measures.json`, après
        validation de toute l'élection. Les champs corrigés gardent leur valeur d'origine dans
        `proposed`. La file présente d'abord les groupes signalés, puis les chiffrages.
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
    include_reviewed = mo.ui.checkbox(label="Inclure les mesures déjà revues")
    blind = mo.ui.checkbox(label="Masquer le nom du candidat")
    mo.hstack([reviewer, include_reviewed, blind], justify="start")
    return blind, include_reviewed, reviewer


@app.cell
def _(election, get_refresh, include_reviewed, measure_queue, mo, progress):
    get_refresh()
    queue = measure_queue(election, include_reviewed=include_reviewed.value)
    counts = progress(election)["measures"]
    total = sum(counts.values())
    done = total - counts.get("pending", 0)
    mo.md(f"**Avancement** : {done} / {total} mesures revues ; {len(queue)} dans la file.")
    return (queue,)


@app.cell
def _(mo, queue, set_index):
    # Boutons seuls : marimo ne réexécute pas la cellule qui appelle le setter, la lecture de
    # l'index se fait donc dans la cellule suivante.
    def _move(step):
        set_index(lambda i: max(0, min(len(queue) - 1, i + step)) if queue else 0)

    previous = mo.ui.button(label="← Précédente", on_click=lambda _: _move(-1))
    following = mo.ui.button(label="Suivante →", on_click=lambda _: _move(1))
    return following, previous


@app.cell
def _(following, get_index, mo, previous, queue):
    measure_index = min(get_index(), max(len(queue) - 1, 0))
    mo.hstack(
        [previous, following, mo.md(f"{measure_index + 1 if queue else 0} / {len(queue)}")],
        justify="start",
    )
    return (measure_index,)


@app.cell
def _(
    blind,
    candidates,
    election,
    json,
    load_records,
    measure_custom_id,
    measure_index,
    proposals_path,
    queue,
):
    entry = queue[measure_index] if queue else None
    current = proposal = who = None
    if entry is not None:
        _doc = json.loads((election / "measures.json").read_text(encoding="utf-8"))
        current = next(m for m in _doc["measures"] if m["id"] == entry["id"])
        proposal = load_records(proposals_path(election, "measure")).get(
            measure_custom_id(entry["candidate_id"], entry["theme"])
        )
        _c = candidates[entry["candidate_id"]]
        who = _c["blind_alias"] if blind.value else f"{_c['name']} ({_c['party']})"
    return current, entry, proposal, who


@app.cell
def _(current, entry, mo, proposal, themes, who):
    def _costing(c):
        label = c["status"]
        if c["amount_eur"] is not None:
            label += f" : {c['amount_eur']:,.0f} €".replace(",", " ")
        if c["period"]:
            label += f" {c['period']}"
        return label

    if entry is None:
        view = mo.md("**File vide** : toutes les mesures de la file sont revues.")
    else:
        _original = {**current, **current.get("proposed", {})}
        _from_model = next(
            (
                m
                for m in ((proposal or {}).get("output") or {}).get("measures", [])
                if m["title"] == _original["title"]
            ),
            None,
        )
        _model_costing = _costing(_from_model["costing"]) if _from_model else "_introuvable_"
        _model = [
            m["title"] + " (" + m["costing"]["status"] + ")"
            for m in ((proposal or {}).get("output") or {}).get("measures", [])
        ]
        _listed = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(_model)) or "_aucune_"
        _rows = [
            f"## {current['id']} · {current['title']}",
            "",
            "| | |",
            "|---|---|",
            f"| Candidat · thème | **{who}** · {themes.get(current['theme'], current['theme'])} |",
            f"| Résumé | {current['summary']} |",
            f"| Chiffrage | **{_costing(current['costing'])}** |",
            f"| Chiffrage avant revue | {_costing(_original['costing'])} |",
            f"| Chiffrage proposé par le modèle | {_model_costing} |",
            f"| Citation du chiffrage | {current['costing']['quote'] or '_aucune_'} |",
            f"| Statut | **{current['review']['status']}** |",
            f"| Signalements du groupe | {', '.join(entry['reasons']) or 'aucun'} |",
            "",
            "Mesures proposées pour ce couple (candidat, thème) :",
            "",
            _listed,
        ]
        view = mo.md("\n".join(_rows))
    view
    return


@app.cell
def _(current, entry, highlight, lookup, mo, pdf_link):
    if entry is None:
        extracts = mo.md("")
    else:
        _quotes = [e["quote"] for e in current["evidence"]]
        if current["costing"]["quote"]:
            _quotes.append(current["costing"]["quote"])
        _items = {}
        for _e in current["evidence"]:
            _chunk = lookup.get(_e["chunk_id"] or "")
            _key = f"{_e['document_title']} · p. {_e['page']}"
            if _chunk is None:
                _items[_key] = mo.md(f"« {_e['quote']} » (texte absent : sources/chunks.jsonl)")
                continue
            _link = pdf_link(_chunk)
            _source = (
                f'<p><a href="{_link}" target="_blank" rel="noopener">Ouvrir la page</a></p>'
                if _link
                else ""
            )
            _body = highlight(_chunk["text"], _quotes)
            _items[_key] = mo.Html(f"<div style='white-space: pre-wrap'>{_body}</div>{_source}")
        extracts = mo.vstack(
            [
                mo.md("**Citations** (surlignées dans leur extrait)"),
                mo.accordion(_items, multiple=True) if _items else mo.md("_aucune_"),
            ]
        )
    extracts
    return


@app.cell
def _(current, entry, mo):
    _c = (
        current["costing"]
        if current
        else {"status": "intention", "amount_eur": None, "period": None, "quote": None}
    )
    title = mo.ui.text(value=current["title"] if current else "", label="Titre", full_width=True)
    summary = mo.ui.text_area(
        value=current["summary"] if current else "", label="Résumé", full_width=True
    )
    status = mo.ui.dropdown(
        options=["chiffre", "partiel", "intention"], value=_c["status"], label="Chiffrage"
    )
    amount = mo.ui.text(
        value="" if _c["amount_eur"] is None else f"{_c['amount_eur']:.0f}", label="Montant (euros)"
    )
    period = mo.ui.text(value=_c["period"] or "", label="Période")
    cost_quote = mo.ui.text_area(
        value=_c["quote"] or "",
        label="Citation du chiffrage (recopiée du programme)",
        full_width=True,
    )
    note = mo.ui.text_area(label="Note de revue (facultative)", full_width=True)
    form = mo.vstack(
        [title, summary, mo.hstack([status, amount, period], justify="start"), cost_quote, note]
    )
    form if entry is not None else mo.md("")
    return amount, cost_quote, note, period, status, summary, title


@app.cell
def _(
    ReviewError,
    amount,
    cost_quote,
    date,
    election,
    entry,
    mo,
    note,
    period,
    review_measure,
    reviewer,
    set_message,
    set_refresh,
    status,
    summary,
    title,
):
    def _decide(decision):
        if entry is None:
            return
        kwargs = {"note": note.value or None}
        if decision == "corrected":
            try:
                _amount = (
                    float(amount.value.replace(" ", "").replace(",", "."))
                    if amount.value.strip()
                    else None
                )
            except ValueError:
                set_message("⚠️ Montant illisible (nombre en euros).")
                return
            kwargs.update(
                title=title.value.strip(),
                summary=summary.value.strip(),
                costing={
                    "status": status.value,
                    "amount_eur": _amount,
                    "period": period.value.strip() or None,
                    "quote": cost_quote.value.strip() or None,
                },
            )
        try:
            review_measure(
                election,
                entry["id"],
                decision=decision,
                reviewer=reviewer.value,
                on=date.today(),
                **kwargs,
            )
        except ReviewError as exc:
            set_message(f"⚠️ {exc}")
            return
        set_message(f"✅ {entry['id']} : {decision}.")
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
