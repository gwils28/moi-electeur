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
        # M3-02 : Revue humaine des propositions 2022

        | Métadonnée | Valeur |
        |---|---|
        | Date | 2026-11-27 |
        | Auteur | Claude Code (revue : mainteneur) |
        | Données | `data/elections/fr-presidentielle-2022/{positions,measures}.json`, `proposals/*.jsonl` |
        | Modèle / prompt | aucun appel LLM (lecture des décisions de revue) |
        | Graine | aucune |
        | Statut | constat : validation en bloc, fiabilité à mesurer en M4 |
        | Code | `pipeline/src/moi_electeur_pipeline/review.py`, `review/` |

        ## 1. Question et contexte
        La revue humaine (PLAN § 5.3, D31) devait mesurer la fiabilité de l'extraction par
        Claude : taux de validation, de correction et de rejet, écart moyen des corrections,
        corrections par thème et par niveau de confiance. Ce notebook lit les décisions
        enregistrées dans `positions.json` et `measures.json`.

        ## 2. Hypothèses et alternatives envisagées
        | Mode de revue | Ce qu'il mesure |
        |---|---|
        | Relecture une à une (prévue) | taux de correction réel, par thème et par confiance |
        | **Validation en bloc (retenue par le mainteneur)** | rien sur la fiabilité : toutes les propositions sont acceptées telles quelles |
        | Échantillon relu à la main (M4) | fiabilité estimée avec un intervalle, sur un codage de référence |

        ## 3. Formalisation
        Taux de correction = corrigées / revues ; écart moyen = moyenne de |valeur − valeur
        proposée| sur les positions corrigées. Une validation en bloc est repérée par sa note
        de revue.
        """
    )
    return


@app.cell
def _():
    import json
    from collections import Counter

    import pandas as pd

    from moi_electeur_pipeline.paths import elections_dir

    election = elections_dir() / "fr-presidentielle-2022"

    def _load(name, key):
        path = election / name
        return json.loads(path.read_text(encoding="utf-8"))[key] if path.is_file() else []

    positions = _load("positions.json", "positions")
    measures = _load("measures.json", "measures")
    BULK = "Validation en bloc"
    return BULK, Counter, measures, pd, positions


@app.cell
def _(BULK, Counter, measures, mo, pd, positions):
    def _summary(items, label):
        status = Counter(i["review"]["status"] for i in items)
        bulk = sum(BULK in (i["review"].get("note") or "") for i in items)
        return {
            "fichier": label,
            "total": len(items),
            **{s: status.get(s, 0) for s in ("pending", "validated", "corrected", "rejected")},
            "validation en bloc": bulk,
        }

    table = pd.DataFrame(
        [_summary(positions, "positions"), _summary(measures, "mesures")]
    ).set_index("fichier")
    corrected = [p for p in positions if p["review"]["status"] == "corrected"]
    gap = (
        sum(abs((p["value"] or 0) - (p.get("proposed_value") or 0)) for p in corrected)
        / len(corrected)
        if corrected
        else None
    )
    mo.vstack(
        [
            mo.md("## 4. Expérimentation"),
            table,
            mo.md(
                f"Positions corrigées : **{len(corrected)}** ; écart moyen des corrections : "
                f"{'non calculable' if gap is None else f'{gap:.2f}'}."
            ),
        ]
    )
    return


@app.cell
def _(BULK, mo, positions):
    _bulk = sum(BULK in (p["review"].get("note") or "") for p in positions)
    mo.md(
        f"""
        ## 5. Résultats et limites

        - {_bulk} positions sur {len(positions)} portent la note de validation en bloc : elles
          ont été acceptées telles que Claude les a proposées (prompt v2), sans relecture
          individuelle. Les taux de correction ne mesurent donc pas la fiabilité de
          l'extraction ; ils valent zéro par construction.
        - Ce qui reste établi par l'extraction elle-même (m3-01) : 307 citations de positions
          sur 309 retrouvées dans les extraits, valeur refusée faute de citation remplacée par
          un silence de confiance faible, montants vérifiés dans leur citation.
        - Points qu'une relecture individuelle aurait examinés : les 15 positions de confiance
          faible, les 2 citations non retrouvées (colonnes entremêlées du PDF d'une candidate),
          les silences fréquents (s29 Corse 11 sur 12, s10 uniforme 10 sur 12), et les
          candidats dont peu de positions sont renseignées (coordonnées plus fragiles).

        ## 6. Décision
        Boussole 2022 publiée sur décision du mainteneur. La fiabilité de l'extraction sera
        mesurée en M4 sur un échantillon codé à la main (codage de référence), et la page
        méthodologie (M5) devra indiquer que les positions 2022 ont été validées en bloc.
        """
    )
    return


if __name__ == "__main__":
    app.run()
