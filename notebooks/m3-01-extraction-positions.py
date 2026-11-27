import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(
        r"""
        # M3-01 : Extraction des positions et des mesures par Claude

        | Métadonnée | Valeur |
        |---|---|
        | Date | 2026-11-28 |
        | Auteur | Claude Code (revue : mainteneur) |
        | Données | `data/elections/fr-presidentielle-2022/proposals/*.jsonl` (versionnés, aucun texte d'extrait hors citations) |
        | Modèle / prompt | Sonnet 5.5, réflexion adaptative, effort `medium` ; `prompts/positions_system.md` et `measures_system.md` (v1 pilote, v2) |
        | Graine | aucune (lecture seule) |
        | Statut | pilote revu, prompt v2 retenu ; lots complets en Batch API |
        | Code | `pipeline/src/moi_electeur_pipeline/propose.py`, commandes `propose-positions`, `propose-measures`, `batch-status` |

        ## 1. Question et contexte
        La boussole 2022 repose sur 360 positions (12 candidats × 30 affirmations) et le
        comparateur sur les mesures phares de 72 couples (candidat, thème), proposées par Claude
        à partir des extraits des programmes (PLAN § 5.2, D24 à D29), puis revues une à une par le
        mainteneur (M3c). Ce notebook décrit ce que l'extraction a produit, avant la revue :
        silences, valeurs, confiance, citations retrouvées, chiffrages, coût ; il compare aussi
        les deux versions du prompt sur le pilote (melenchon, pecresse).

        ## 2. Hypothèses et alternatives envisagées
        | Choix | Retenu | Alternative |
        |---|---|---|
        | Unité de requête | un couple (candidat, affirmation), 6 extraits | les 30 affirmations d'un candidat en une requête (contexte long, contamination) |
        | Preuves | citations vérifiées après coup dans l'extrait désigné | citations natives (incompatibles avec la sortie structurée) |
        | Anonymat | aucun nom ni titre de document ajouté | masquage des noms dans le texte même (citations alors inexactes) |
        | Envoi | pilote en appels directs, puis Batch API (-50 %) | tout en appels directs |

        ## 3. Formalisation
        Pour chaque couple, la dernière proposition faite avec la version courante du prompt
        compte. Taux de citations retrouvées = citations vérifiées / citations proposées. Une
        valeur non nulle sans citation retrouvée est refusée (`invalid`, écrite comme silence de
        confiance faible pour la revue). Aucun indicateur ne compare les candidats entre eux :
        les tableaux décrivent la couverture de chaque programme par les affirmations.
        """
    )
    return


@app.cell
def _():
    import json

    import pandas as pd

    from moi_electeur_pipeline.paths import elections_dir
    from moi_electeur_pipeline.propose import load_prompt

    election = elections_dir() / "fr-presidentielle-2022"

    def lines(kind):
        path = election / "proposals" / f"{kind}.jsonl"
        if not path.is_file():
            return []
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]

    all_positions = lines("positions")
    all_measures = lines("measures")
    versions = {
        "position": load_prompt("positions_system").version,
        "measure": load_prompt("measures_system").version,
    }

    def latest(records, version):
        out = {}
        for r in records:
            if r["prompt_version"] == version:
                out[r["custom_id"]] = r
        return list(out.values())

    positions = latest(all_positions, versions["position"])
    measures = latest(all_measures, versions["measure"])
    return all_measures, all_positions, measures, pd, positions, versions


@app.cell
def _(measures, mo, positions, versions):
    mo.md(
        f"""
        ## 4. Expérimentation

        Prompt courant : positions v{versions["position"]}, mesures v{versions["measure"]}.
        Propositions courantes : **{len(positions)}** positions sur 360,
        **{len(measures)}** couples de mesures sur 72.
        """
    )
    return


@app.cell
def _(pd, positions):
    def value_label(r):
        if r["status"] == "error":
            return "erreur"
        if r["status"] == "invalid":
            return "refusée"
        v = r["output"]["value"]
        return "silence" if v is None else f"{v:+d}"

    pos = pd.DataFrame(
        [
            {
                "candidat": r["candidate_id"],
                "affirmation": r["target"],
                "valeur": value_label(r),
                "confiance": (r["output"] or {}).get("confidence"),
                "citations": len(r["quotes"]),
                "vérifiées": sum(q["verified"] for q in r["quotes"]),
                "signalements": ", ".join(r["flags"]),
                "mode": r["mode"],
                "coût": r["cost_usd"],
                "sortie": r["usage"]["output_tokens"],
            }
            for r in positions
        ]
    )
    order = ["-2", "-1", "+0", "+1", "+2", "silence", "refusée", "erreur"]
    distribution = (
        pd.crosstab(pos["candidat"], pos["valeur"]).reindex(columns=order, fill_value=0)
        if len(pos)
        else pd.DataFrame()
    )
    distribution
    return (pos,)


@app.cell
def _(mo, pos):
    if len(pos):
        n_quotes = int(pos["citations"].sum())
        verified = int(pos["vérifiées"].sum())
        silences = int((pos["valeur"] == "silence").sum())
        low = int((pos["confiance"] == "low").sum())
        flagged = int((pos["signalements"] != "").sum())
        summary = mo.md(
            f"""
            - Silences : **{silences}** sur {len(pos)} ({silences / len(pos):.0%}).
            - Citations retrouvées : **{verified} / {n_quotes}**.
            - Confiance faible : {low} ; propositions signalées : {flagged}.
            - Sortie moyenne : {pos["sortie"].mean():.0f} tokens ; coût total
              {pos["coût"].sum():.2f} $ (dont {pos.loc[pos["mode"] == "batch", "coût"].sum():.2f} $ en lot).
            """
        )
    else:
        summary = mo.md("Aucune proposition de position.")
    summary
    return


@app.cell
def _(pd, pos):
    import json as _json

    from moi_electeur_pipeline.paths import elections_dir as _dir

    _path = _dir() / "fr-presidentielle-2022" / "statements.json"
    _st = _json.loads(_path.read_text(encoding="utf-8"))["statements"]
    themes = {s["id"]: s["theme"] for s in _st}
    if len(pos):
        by_theme = pos.assign(thème=pos["affirmation"].map(themes))
        silences_by_theme = (
            by_theme.assign(silence=by_theme["valeur"] == "silence")
            .groupby("thème")["silence"]
            .mean()
            .round(2)
            .rename("part de silences")
        )
        silence_by_statement = (
            by_theme.assign(silence=by_theme["valeur"] == "silence")
            .groupby("affirmation")["silence"]
            .sum()
            .rename("silences (sur le nombre de candidats traités)")
        )
    else:
        silences_by_theme = silence_by_statement = pd.Series(dtype=float)
    silences_by_theme, silence_by_statement
    return


@app.cell
def _(all_positions, pd):
    # Pilote : effet du passage v1 -> v2 sur les mêmes couples.
    by_version = {}
    for _r in all_positions:
        by_version.setdefault(_r["prompt_version"], {})[_r["custom_id"]] = _r
    v1, v2 = by_version.get(1, {}), by_version.get(2, {})
    changes = pd.DataFrame(
        [
            {
                "couple": cid,
                "v1": v1[cid]["output"]["value"],
                "v2": v2[cid]["output"]["value"],
                "justification v2": v2[cid]["output"]["rationale"][:120],
            }
            for cid in sorted(set(v1) & set(v2))
            if v1[cid]["output"]
            and v2[cid]["output"]
            and v1[cid]["output"]["value"] != v2[cid]["output"]["value"]
        ]
    )
    changes
    return


@app.cell
def _(measures, pd):
    rows = []
    for _r in measures:
        for _i, _m in enumerate((_r["output"] or {}).get("measures", [])):
            cited = any(
                q["verified"] and q["role"] == "evidence" and q["measure"] == _i
                for q in _r["quotes"]
            )
            rows.append(
                {
                    "candidat": _r["candidate_id"],
                    "thème": _r["target"],
                    "chiffrage": _m["costing"]["status"],
                    "citée": cited,
                }
            )
    mes = pd.DataFrame(rows)
    costing = pd.crosstab(mes["candidat"], mes["chiffrage"]) if len(mes) else pd.DataFrame()
    flags = pd.Series([f for r in measures for f in r["flags"]], dtype=object).value_counts()
    cost_measures = sum(r["cost_usd"] for r in measures)
    costing, flags, f"{len(mes)} mesures, coût {cost_measures:.2f} $"
    return


@app.cell
def _(all_measures, all_positions, mo):
    total = sum(r["cost_usd"] for r in all_positions + all_measures)
    mo.md(
        f"""
        ## 5. Résultats et limites

        - Coût cumulé de l'extraction (pilote v1 et v2 compris) : **{total:.2f} $**.
        - Pilote : le prompt v1 accordait des ±2 sans engagement explicite et tirait des valeurs
          de sujets voisins ; le v2 ramène ces cas à ±1 ou au silence (tableau des changements
          ci-dessus) et n'attribue plus de montant global à une seule mesure.
        - Limites : la recherche fournit 6 extraits par couple ; un engagement absent de ces
          extraits devient un silence (faux silence possible, à mesurer en M4 sur l'échantillon
          codé à la main). Les noms écrits dans le texte des programmes ne sont pas masqués.
          Les propositions ne sont publiées qu'après la revue humaine (M3c).

        ## 6. Décision
        Prompt v2 retenu pour le lot complet (PLAN D28). Signalements (citation non retrouvée,
        confiance faible, montant non retrouvé) placés en tête de la file de revue (D31). Détails
        dans `docs/notes-implementation.md` (M3b).
        """
    )
    return


if __name__ == "__main__":
    app.run()
