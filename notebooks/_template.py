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
        # <Jalon>-<nn> : <Sujet>

        | Métadonnée | Valeur |
        |---|---|
        | Date | AAAA-MM-JJ |
        | Auteur | ... |
        | Données | `data/elections/<id>` (version / sha) |
        | Modèle / prompt | ... (ou « aucun appel LLM ») |
        | Graine | ... |
        | Statut | exploration / décision prise |

        ## 1. Question et contexte
        Quelle question ce notebook tranche-t-il ? Lien vers la SPEC (§) et le PLAN.

        ## 2. Hypothèses et alternatives envisagées
        Liste des options, avec ce qui les distingue.

        ## 3. Formalisation
        Formules, notations, invariants attendus.
        """
    )
    return


@app.cell
def _():
    # 4. Expérimentation : charger les données versionnées, fixer les graines, calculer, tracer.
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        ## 5. Résultats et limites

        ## 6. Décision
        Décision prise, lien vers le code et vers `docs/notes-implementation.md`.
        """
    )
    return


if __name__ == "__main__":
    app.run()
