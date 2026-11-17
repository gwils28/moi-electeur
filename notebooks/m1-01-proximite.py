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
        # M1-01 : Score de proximité

        | Métadonnée | Valeur |
        |---|---|
        | Date | 2026-11-17 |
        | Auteur | Claude Code (revue : mainteneur) |
        | Données | `demo-fictive` (`pipeline make-demo`), fixture `schemas/fixtures/engine_cases.json` |
        | Modèle / prompt | aucun appel LLM |
        | Graine | 7 (profils utilisateurs simulés) |
        | Statut | décision prise |
        | Code | `packages/engine/src/proximity.ts`, référence `pipeline/.../engine_ref.py` |

        ## 1. Question et contexte
        Comment mesurer la proximité entre les réponses d'un utilisateur et les positions d'un
        candidat, sur une échelle de Likert à 5 niveaux (-2..+2), avec des « Sans avis » côté
        utilisateur et des silences côté programme (SPEC § 5.2) ?

        ## 2. Alternatives envisagées
        | Métrique | Pour | Contre |
        |---|---|---|
        | Accord exact (% de réponses identiques) | simple | ignore « plutôt » vs « tout à fait » |
        | Distance euclidienne | classique | pénalise trop les gros écarts isolés, moins lisible |
        | Corrélation | insensible au niveau | indéfinie si réponses constantes, peu explicable |
        | **Manhattan normalisée pondérée** | lisible (« écart moyen »), bornée, explicable par affirmation | traite l'échelle comme intervalle |

        Retenu : **Manhattan**, comme la plupart des boussoles (ex. outils de type « Smartvote »).

        ## 3. Formalisation
        Sur $S$ = affirmations où utilisateur **et** candidat ont une valeur :

        $$d(c) = \sum_{s \in S} w_{\theta(s)}\,|u_s - c_s|, \qquad d_{max}(c) = \sum_{s \in S} 4\, w_{\theta(s)}$$
        $$\text{proximité} = 100 \cdot \Big(1 - \frac{d(c)}{d_{max}(c)}\Big), \qquad
        \text{couverture} = \frac{|S|}{|\{s : u_s \neq \varnothing\}|}$$

        Invariants testés (Vitest, `fast-check`) : borné dans [0, 100], symétrique, invariant si
        tous les poids sont multipliés par $k$, un silence équivaut à retirer l'affirmation.

        **Pourquoi normaliser sur $S$ et afficher la couverture** : un candidat silencieux sur
        beaucoup de sujets n'est ni avantagé ni pénalisé par le score, mais la couverture faible
        (< 50 %) est signalée à l'utilisateur.
        """
    )
    return


@app.cell
def _():
    import json

    import matplotlib.pyplot as plt
    import pandas as pd

    from moi_electeur_pipeline.paths import repo_root

    cases = json.loads(
        (repo_root() / "schemas" / "fixtures" / "engine_cases.json").read_text(encoding="utf-8")
    )
    return cases, pd, plt


@app.cell
def _(cases, mo, pd):
    rows = []
    for i, u in enumerate(cases["users"]):
        for cid, r in u["proximity"].items():
            rows.append(
                {
                    "utilisateur": i,
                    "candidat": cid,
                    "score": r["score"],
                    "couverture": r["coverage"],
                }
            )
    table = (
        pd.DataFrame(rows).pivot(index="candidat", columns="utilisateur", values="score").round(1)
    )
    mo.vstack(
        [
            mo.md(
                "## 4. Expérimentation\nScores de 4 utilisateurs simulés (réponses et poids "
                "aléatoires) face aux 6 candidats fictifs, calculés par la référence Python. "
                "Le moteur TS reproduit ces valeurs à 1e-9 près (`cross-python.test.ts`)."
            ),
            table,
        ]
    )
    return (table,)


@app.cell
def _(cases, plt):
    from moi_electeur_pipeline.engine_ref import proximity

    statements = cases["statements"]
    user = cases["users"][0]
    cand = cases["candidates"]["c1"]["answers"]
    ks = [1, 2, 3]
    fig, ax = plt.subplots(figsize=(6, 3))
    for theme in sorted({s["theme"] for s in statements}):
        scores = [proximity(user["answers"], cand, statements, {theme: k})["score"] for k in ks]
        ax.plot(ks, scores, marker="o", label=theme)
    ax.set_xlabel("poids du thème (les autres à 1)")
    ax.set_ylabel("proximité avec c1")
    ax.set_xticks(ks)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig
    return


@app.cell
def _(mo):
    mo.md(
        r"""
        Effet des poids : augmenter le poids d'un thème rapproche le score de la proximité
        mesurée sur ce seul thème. C'est l'effet voulu (« ce thème compte plus pour moi »).

        ## 5. Résultats et limites
        - L'échelle de Likert est traitée comme une échelle d'intervalle (écart 2 → 1 vaut 1 → 0).
        - Un « Neutre » (0) est une réponse, un « Sans avis » est exclu : la distinction est
          expliquée dans l'interface.
        - **Décision D2** : les poids de thème n'agissent que sur la proximité, jamais sur la
          projection (x, y), pour que les points candidats ne bougent pas selon l'utilisateur.

        ## 6. Décision
        Formule retenue telle quelle (SPEC § 5.2), implémentée dans `proximity.ts`, vérifiée par
        tests de propriétés et par la fixture croisée Python/TS.
        """
    )
    return


if __name__ == "__main__":
    app.run()
