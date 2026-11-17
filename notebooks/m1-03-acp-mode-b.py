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
        # M1-03 : Projection 2D, mode B (analyse en composantes principales)

        | Métadonnée | Valeur |
        |---|---|
        | Date | 2026-11-17 |
        | Auteur | Claude Code (revue : mainteneur) |
        | Données | `demo-fictive`, fixture `schemas/fixtures/pca_toy.json` |
        | Modèle / prompt | aucun appel LLM |
        | Graine | aucune (SVD déterministe) |
        | Statut | décision prise (D3, D4) |
        | Code | `pipeline/.../pca.py` (ajustement), `packages/engine/src/projection.ts` (`projectB`) |

        ## 1. Question et contexte
        Le mode A impose les axes a priori. Le mode B les **apprend** des positions des
        candidats : quelles oppositions structurent réellement l'offre électorale ?

        ## 2. Alternatives envisagées
        - ACP sur la matrice candidats × affirmations (**retenu**, SPEC § 5.3) ;
        - analyse des correspondances multiples (plus adaptée aux modalités, moins lisible) ;
        - MDS sur les distances de Manhattan (cohérent avec la proximité, mais pas de projection
          simple d'un nouvel individu).

        ## 3. Formalisation
        $M \in \mathbb{R}^{C \times S}$ (silences et positions non validées imputés à 0),
        $\bar m$ moyenne par affirmation, SVD $M - \bar m = U \Sigma V^\top$. Composantes
        $v_1, v_2$ = 2 premières lignes de $V^\top$. Un individu de valeurs $u$ est projeté par
        $z_k = \lambda_k\, v_k \cdot (u - \bar m)$, borné à $[-10, 10]$.

        - **D3 (signe)** : la SVD fixe $v_k$ au signe près. On oriente $v_k$ pour que les scores
          candidats corrèlent positivement avec l'axe $k$ du mode A : un candidat « à droite » en
          mode A reste à droite en mode B.
        - **D4 (échelle)** : $\lambda_k = 9 / \max_c |z_{c,k}|$ est fixé par les candidats seuls ;
          l'utilisateur ne déforme jamais le repère, il est borné et l'interface le signale.

        Le pipeline calcule $(\bar m, v_1, v_2, \lambda)$ ; le navigateur fait la projection.
        """
    )
    return


@app.cell
def _():
    import json

    import matplotlib.pyplot as plt
    import numpy as np

    from moi_electeur_pipeline.demo import CANDIDATES, build_demo
    from moi_electeur_pipeline.engine_ref import candidate_answers, project_a
    from moi_electeur_pipeline.paths import repo_root
    from moi_electeur_pipeline.pca import fit_pca, project_b

    toy = json.loads((repo_root() / "schemas" / "fixtures" / "pca_toy.json").read_text())
    toy_model = fit_pca("fixture", toy["statements"], toy["candidates"])
    np.testing.assert_allclose(toy_model["components"], toy["model"]["components"], atol=1e-9)
    return CANDIDATES, build_demo, candidate_answers, fit_pca, np, plt, project_a, project_b


@app.cell
def _(mo):
    mo.md(
        """
        ## 4. Expérimentation
        **Vérification sur la fixture jouet** (calculable à la main) : l'ajustement retrouve
        exactement les composantes attendues (assertion ci-dessus). Les tests pytest et Vitest
        utilisent la même fixture.
        """
    )
    return


@app.cell
def _(CANDIDATES, build_demo, candidate_answers, fit_pca, project_a, project_b):
    demo = build_demo()
    statements = demo["statements.json"]["statements"]
    positions = demo["positions.json"]["positions"]
    ids = [s["id"] for s in statements]
    answers = {c[0]: candidate_answers(positions, c[0], ids) for c in CANDIDATES}
    model = fit_pca("demo-fictive", statements, answers)
    pts_a = {c: project_a(a, statements) for c, a in answers.items()}
    pts_b = {c: project_b(a, model)[:2] for c, a in answers.items()}
    text = {s["id"]: s["text"] for s in statements}
    return model, pts_a, pts_b, text


@app.cell
def _(CANDIDATES, model, plt, pts_a, pts_b):
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.5))
    for ax, pts, title in [(axes[0], pts_a, "Mode A"), (axes[1], pts_b, "Mode B (ACP)")]:
        for cid, name, _p, color, _a, _pr in CANDIDATES:
            p = pts[cid]
            x, y = (p["x"], p["y"]) if isinstance(p, dict) else p
            ax.scatter(x, y, color=color, s=50)
            ax.annotate(
                name.split()[0], (x, y), fontsize=7, xytext=(3, 3), textcoords="offset points"
            )
        ax.axhline(0, color="grey", lw=0.5)
        ax.axvline(0, color="grey", lw=0.5)
        ax.set_xlim(-10.5, 10.5)
        ax.set_ylim(-10.5, 10.5)
        ax.set_title(title, fontsize=9)
    evr = model["explained_variance_ratio"]
    axes[1].set_xlabel(f"composante 1 ({evr[0]:.0%})")
    axes[1].set_ylabel(f"composante 2 ({evr[1]:.0%})")
    fig.tight_layout()
    fig
    return (evr,)


@app.cell
def _(evr, mo, model, text):
    tops = "\n".join(
        f"- **Composante {k + 1}** : " + " ; ".join(f"« {text[i]} »" for i in ids)
        for k, ids in enumerate(model["top_statements"])
    )
    mo.md(
        f"""
        Sur la démo, les deux composantes expliquent {evr[0]:.0%} et {evr[1]:.0%} de la
        variance. Affirmations les plus contributives (affichées dans l'interface pour
        interpréter les axes) :

        {tops}

        ## 5. Résultats et limites
        - Avec peu de candidats (6 ici, 12 en 2022), l'ACP est instable : un candidat atypique
          peut faire tourner les axes. D'où le mode A par défaut et la variance affichée.
        - L'imputation des silences à 0 (« neutre ») est un choix conservateur qui rapproche les
          candidats silencieux du centre.
        - Le filtre par thème n'a pas de sens avec un modèle global : il est désactivé en mode B.

        ## 6. Décision
        Mode B livré tel que spécifié, avec D3 (orientation sur le mode A) et D4 (échelle fixée
        par les candidats, bornage signalé). `pipeline build` produit `pca_model.json`.
        """
    )
    return


if __name__ == "__main__":
    app.run()
