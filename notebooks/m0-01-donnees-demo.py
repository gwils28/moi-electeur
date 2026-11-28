import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(r"""
    # M0-01 : Construction des données de démonstration

    | Métadonnée | Valeur |
    |---|---|
    | Date | 2026-11-17 |
    | Auteur | Claude Code (revue : mainteneur) |
    | Données | `data/elections/demo-fictive`, généré par `pipeline make-demo` |
    | Modèle / prompt | aucun appel LLM |
    | Graine | `SEED = 2027` (`moi_electeur_pipeline.demo`) |
    | Statut | décision prise (PLAN D9) |

    ## 1. Question et contexte
    Les jalons M0 et M1 doivent avancer avant de disposer d'un vrai corpus (M2/M3).
    Il faut donc une élection **fictive** qui respecte toutes les règles de la SPEC (§ 4.2) :
    25 à 35 affirmations, au moins 4 par thème et 10 par axe, sens alternés, positions
    revues, plus quelques cas limites (silence, positions rejetées).

    ## 2. Alternatives envisagées
    - **Positions saisies à la main** : fastidieux, et peu de contrôle sur la cohérence.
    - **Positions tirées au hasard** : aucune structure, l'échiquier serait illisible.
    - **Retenu : positions dérivées d'un profil idéologique latent + bruit seedé.**
      Les données sont plausibles (structure 2D visible), reproductibles, et le bruit
      évite que le mode A redonne exactement le profil.

    ## 3. Formalisation
    Chaque candidat fictif $c$ a un profil $(e_x, e_y) \in [-1, 1]^2$. Pour une affirmation
    $s$ d'axe $a(s)$ et de sens $d(s) \in \{-1, +1\}$ :

    $$v_{c,s} = \operatorname{clip}_{[-2, 2]}\Big(\operatorname{round}\big(2\, d(s)\, e_{a(s)} + \varepsilon\big)\Big),
    \qquad \varepsilon \sim \mathcal{N}(0, 0{,}5^2)$$

    Le profil n'est **jamais** affiché : les coordonnées de l'échiquier seront recalculées
    par le moteur depuis les positions (règle « (x, y) calculés, jamais saisis »).
    """)
    return


@app.cell
def _():
    import pandas as pd

    from moi_electeur_pipeline.demo import CANDIDATES, build_demo
    from moi_electeur_pipeline.paths import elections_dir
    from moi_electeur_pipeline.validate import validate_election

    demo = build_demo()
    statements = pd.DataFrame(demo["statements.json"]["statements"])
    positions = pd.DataFrame(demo["positions.json"]["positions"])
    return (
        CANDIDATES,
        elections_dir,
        pd,
        positions,
        statements,
        validate_election,
    )


@app.cell
def _(mo, statements):
    coverage = statements.pivot_table(
        index="theme", columns="axis", values="id", aggfunc="count", fill_value=0
    )
    directions = statements.groupby("axis")["direction"].value_counts().unstack(fill_value=0)
    assert statements["theme"].value_counts().min() >= 4
    assert (statements["axis"].value_counts() >= 10).all()
    assert (directions > 0).all().all(), "chaque axe doit mêler les deux sens"
    mo.vstack(
        [
            mo.md("## 4. Contrôles de couverture\nAffirmations par thème et par axe :"),
            coverage,
            mo.md("Sens par axe (biais d'acquiescement limité si les deux sont présents) :"),
            directions,
        ]
    )
    return


@app.cell
def _(mo, positions):
    status = positions["review"].map(lambda r: r["status"]).value_counts()
    silences = int(positions["value"].isna().sum())
    assert silences == 1 and status.get("rejected", 0) == 2
    mo.md(
        f"""
        **Cas limites présents** : {silences} silence (exclu du calcul de distance) et
        {status.get("rejected", 0)} positions `rejected` (que le front ne doit jamais charger).
        """
    )
    return


@app.cell
def _(CANDIDATES, pd, positions, statements):
    # Vérification de cohérence : moyenne signée des positions par axe vs profil latent.
    merged = positions.merge(statements, left_on="statement_id", right_on="id")
    merged = merged[merged["value"].notna()]
    merged["signed"] = merged["value"] * merged["direction"] / 2
    observed = merged.pivot_table(index="candidate_id", columns="axis", values="signed")
    latent = pd.DataFrame({c[0]: {"x": c[5][0], "y": c[5][1]} for c in CANDIDATES}).T.rename(
        columns=lambda a: f"profil_{a}"
    )
    comparison = observed.join(latent)
    corr = {a: comparison[a].corr(comparison[f"profil_{a}"]) for a in ("x", "y")}
    assert min(corr.values()) > 0.9
    return comparison, corr


@app.cell
def _(comparison, corr, mo):
    mo.vstack(
        [
            mo.md(
                f"""
                ## 5. Résultats et limites
                Moyenne signée des positions par axe (proche, mais pas égale, de ce que
                calculera le mode A) comparée au profil latent. Corrélations :
                x = {corr["x"]:.2f}, y = {corr["y"]:.2f}.
                Le bruit décale légèrement les candidats, comme attendu.
                """
            ),
            comparison.round(2),
            mo.md(
                """
                **Limites** : les candidats sont inventés et les citations sont des extraits
                fictifs ; ces données ne servent qu'au développement et aux tests.
                """
            ),
        ]
    )
    return


@app.cell
def _(elections_dir, mo, validate_election):
    issues = validate_election(elections_dir() / "demo-fictive")
    assert issues == [], issues
    mo.md(
        """
        ## 6. Décision
        Données retenues telles quelles, régénérables par `uv run pipeline make-demo`,
        vérifiées par `uv run pipeline validate` (aucun problème) et par la CI
        (`make-demo --check`). Voir `pipeline/src/moi_electeur_pipeline/demo.py`.
        """
    )
    return


if __name__ == "__main__":
    app.run()
