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
    # M1-02 : Projection 2D, mode A (affirmations taguées)

    | Métadonnée | Valeur |
    |---|---|
    | Date | 2026-11-17 |
    | Auteur | Claude Code (revue : mainteneur) |
    | Données | `demo-fictive` |
    | Modèle / prompt | aucun appel LLM |
    | Graine | aucune |
    | Statut | décision prise |
    | Code | `packages/engine/src/projection.ts` (`projectA`) |

    ## 1. Question et contexte
    Placer utilisateur et candidats sur un échiquier à 2 axes (économie ; société &
    souveraineté), avec la règle « les (x, y) des candidats sont calculés, jamais saisis ».

    ## 2. Alternatives envisagées
    - Coordonnées saisies par des experts : interdit par la règle, invérifiable.
    - **Mode A : chaque affirmation est rattachée à un axe et à un sens** ; la position est
      la moyenne pondérée signée des réponses. Transparent, explicable affirmation par
      affirmation. Dépend de la qualité du tagage (validé humainement).
    - Mode B (ACP) : axes appris des données, voir m1-03.

    ## 3. Formalisation
    $$X = 10 \cdot \frac{\sum_{s \in S_x} w_s\, \mathrm{dir}_s\, v_s}{\sum_{s \in S_x} 2\, w_s}
    \in [-10, 10]$$
    où $S_x$ = affirmations de l'axe $x$ ayant une valeur. Même formule pour $Y$, et **même
    fonction pour l'utilisateur et les candidats**. Si $S_x$ est vide, $X$ n'est pas défini.
    """)
    return


@app.cell
def _():
    import matplotlib.pyplot as plt

    from moi_electeur_pipeline.demo import CANDIDATES, build_demo
    from moi_electeur_pipeline.engine_ref import candidate_answers, project_a

    demo = build_demo()
    statements = demo["statements.json"]["statements"]
    positions = demo["positions.json"]["positions"]
    ids = [s["id"] for s in statements]
    points = {
        c[0]: project_a(candidate_answers(positions, c[0], ids), statements) for c in CANDIDATES
    }
    return CANDIDATES, plt, points


@app.cell
def _(CANDIDATES, plt, points):
    fig, ax = plt.subplots(figsize=(5, 5))
    for cid, name, _p, color, _a, profile in CANDIDATES:
        p = points[cid]
        ax.scatter(p["x"], p["y"], color=color, s=60, zorder=3)
        ax.annotate(name, (p["x"], p["y"]), fontsize=7, xytext=(4, 4), textcoords="offset points")
        ax.scatter(10 * profile[0], 10 * profile[1], color=color, marker="x", alpha=0.5)
        ax.plot([p["x"], 10 * profile[0]], [p["y"], 10 * profile[1]], color=color, alpha=0.3)
    ax.axhline(0, color="grey", lw=0.5)
    ax.axvline(0, color="grey", lw=0.5)
    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    ax.set_xlabel("x : économie")
    ax.set_ylabel("y : société & souveraineté")
    ax.set_title("Mode A (points) vs profil latent de la démo (croix)", fontsize=9)
    fig.tight_layout()
    fig
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 4-5. Résultats et limites
    Les points calculés suivent le profil latent qui a servi à générer la démo, avec un
    écart dû au bruit et à l'arrondi des positions : c'est attendu, et c'est bien le calcul
    qui place les candidats, pas le profil.

    Limites :
    - un candidat silencieux sur un axe n'y a pas de coordonnée (non placé, signalé) ;
    - la position dépend du choix des affirmations et de leur tagage : d'où la validation
      humaine, les sens alternés et le mode B comme point de comparaison ;
    - le filtre par thème recalcule (x, y) sur le sous-ensemble du thème.

    Propriétés testées : bornes, antisymétrie ($v \to -v \Rightarrow (x,y) \to (-x,-y)$),
    invariance d'échelle des poids d'axe, silences exclus.

    ## 6. Décision
    Mode A par défaut (SPEC § 5.3), implémenté dans `projectA`, poids de thème ignorés (D2).
    """)
    return


if __name__ == "__main__":
    app.run()
