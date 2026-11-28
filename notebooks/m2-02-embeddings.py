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
    # M2-02 : bge-m3 ou multilingual-e5-large ?

    | Métadonnée | Valeur |
    |---|---|
    | Date | 2026-11-27 |
    | Auteur | Claude Code (revue : mainteneur) |
    | Données | `fr-presidentielle-2022` (794 extraits) ; jeu de fumée `eval/smoke/questions-2022.jsonl` (15 questions) |
    | Fixture | `notebooks/fixtures/m2-retrieval-smoke.json`, produite par `uv run --project eval moi-electeur-eval retrieval` (base indexée et poids requis) |
    | Modèle / prompt | `BAAI/bge-m3`, `intfloat/multilingual-e5-large` (CPU) ; aucun appel LLM |
    | Graine | 7 (bootstrap sur les questions) |
    | Statut | exploration, décision provisoire |
    | Code | `services/rag/src/moi_electeur_rag/embedding.py`, `eval/src/moi_electeur_eval/` |

    ## 1. Question et contexte
    Le service de recherche (SPEC § 6.1, PLAN D15) charge un seul modèle d'embedding. Les deux
    candidats retenus en M2b sont multilingues et produisent des vecteurs de dimension 1024.
    Lequel retrouve le mieux, **par candidat**, les extraits qui traitent la question ?
    Ce notebook ne regarde que la recherche **sémantique seule** ; la fusion avec le plein
    texte est l'objet de m2-03.

    ## 2. Hypothèses et alternatives envisagées
    | Modèle | Pour | Contre |
    |---|---|---|
    | **bge-m3** (défaut actuel) | 8 192 tokens de contexte (aucun extrait tronqué) | similarités plus dispersées, rien d'autre de connu a priori |
    | **multilingual-e5-large** | bon score multilingue publié | 512 tokens : la fin des extraits les plus longs est tronquée ; préfixes `query:` / `passage:` obligatoires |
    | Modèle d'API (OpenAI, Voyage…) | qualité | envoie les questions à un tiers : écarté (RGPD, SPEC § 6.3) |

    ## 3. Formalisation
    Pour la question $q$, le candidat attendu $c$, ses extraits pertinents $R_{qc}$ (annotés à la
    main dans le jeu de fumée) et le classement $L_{qc}$ par similarité cosinus décroissante :

    $$\text{rappel@}k(q,c) = \frac{|L_{qc}[1..k] \cap R_{qc}|}{\min(k, |R_{qc}|)}, \qquad
    \text{succès@}k(q,c) = \mathbb{1}\big[L_{qc}[1..k] \cap R_{qc} \neq \varnothing\big]$$

    Rappel d'une question : moyenne sur ses candidats attendus ; rappel global (macro) : moyenne
    sur les 13 questions qui ont des attendus (les 2 demandes de recommandation n'en ont pas).
    $k = 4$ est la valeur servie par `/retrieve`. Séparation des similarités :
    $\Delta_q = \overline{s}(\text{pertinents}) - \overline{s}(\text{autres})$, rapportée à
    l'étendue $\max - \min$ des similarités de la question.
    """)
    return


@app.cell
def _():
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    from moi_electeur_eval.report import load_fixture, reports
    from moi_electeur_eval.smoke import load_questions
    from moi_electeur_pipeline.paths import repo_root

    fixture = load_fixture(repo_root() / "notebooks" / "fixtures" / "m2-retrieval-smoke.json")
    questions = load_questions(repo_root() / fixture["questions_file"])
    models = list(fixture["models"])
    return fixture, models, np, pd, plt, questions, reports


@app.cell
def _(fixture, mo, models, pd, plt, questions, reports):
    ks = list(range(1, 7))
    curves = {m: [] for m in models}
    for _k in ks:
        _res = reports(fixture, questions, k=_k)
        for _m in models:
            curves[_m].append(_res[(_m, "semantique")].recall)
    res4 = reports(fixture, questions, k=4)
    summary = pd.DataFrame(
        {
            _m: {
                "rappel@4 macro": round(res4[(_m, "semantique")].recall, 3),
                "rappel@4 micro": round(res4[(_m, "semantique")].recall_micro, 3),
                "succès@4": round(res4[(_m, "semantique")].hit_rate, 3),
            }
            for _m in models
        }
    )
    fig_k, ax_k = plt.subplots(figsize=(5, 3))
    for _m, _c in zip(models, ("#4477aa", "#ee6677"), strict=True):
        ax_k.plot(ks, curves[_m], marker="o", label=_m, color=_c)
    ax_k.set_xlabel("k (extraits par candidat)")
    ax_k.set_ylabel("rappel@k (macro)")
    ax_k.axvline(4, color="#999999", linestyle="--", linewidth=1)
    ax_k.legend(fontsize=8)
    fig_k.tight_layout()
    mo.vstack(
        [
            mo.md(
                f"## 4. Expérimentation\n### 4.1 Rappel sémantique\nCorpus `{fixture['corpus_version']}`, "
                f"{len(questions)} questions, recherche exacte par candidat (pas d'index approché)."
            ),
            summary,
            fig_k,
        ]
    )
    return (res4,)


@app.cell
def _(mo, models, np, pd, res4):
    per_q = pd.DataFrame(
        {
            _m: {
                q.question_id: q.recall
                for q in res4[(_m, "semantique")].questions
                if q.recall is not None
            }
            for _m in models
        }
    )
    per_q["écart"] = per_q[models[1]] - per_q[models[0]]
    _rng = np.random.default_rng(7)
    _d = per_q["écart"].to_numpy()
    _boot = np.array([_d[_rng.integers(0, len(_d), len(_d))].mean() for _ in range(5000)])
    ci = (float(np.quantile(_boot, 0.025)), float(np.quantile(_boot, 0.975)))
    mo.vstack(
        [
            mo.md(
                f"### 4.2 Par question\nÉcart moyen ({models[1]} moins {models[0]}) : "
                f"**{_d.mean():+.3f}**, intervalle bootstrap à 95 % sur les questions "
                f"[{ci[0]:+.3f} ; {ci[1]:+.3f}] (5 000 tirages, graine 7)."
            ),
            per_q.round(2),
        ]
    )
    return (ci,)


@app.cell
def _(mo, models, pd, res4):
    _rows = {}
    for _m in models:
        _hits: dict[str, list[float]] = {}
        for _p in res4[(_m, "semantique")].pairs:
            _hits.setdefault(_p.candidate_id, []).append(1.0 if _p.hit else 0.0)
        _rows[_m] = {c: round(sum(v) / len(v), 2) for c, v in sorted(_hits.items())}
    per_cand = pd.DataFrame(_rows)
    mo.vstack(
        [
            mo.md(
                "### 4.3 Succès@4 par candidat\nPart des questions où au moins un extrait "
                "pertinent du candidat figure dans ses 4 premiers (ordre alphabétique)."
            ),
            per_cand,
        ]
    )
    return


@app.cell
def _(fixture, mo, models, pd, plt):
    _rows = []
    for _m in models:
        for _qid, _s in fixture["models"][_m]["similarity"].items():
            _gap = (
                None
                if _s["relevant_mean"] is None
                else (_s["relevant_mean"] - _s["irrelevant_mean"]) / (_s["max"] - _s["min"])
            )
            _rows.append({"modèle": _m, "question": _qid, **_s, "séparation": _gap})
    sims = pd.DataFrame(_rows)
    fig_s, ax_s = plt.subplots(figsize=(7, 3))
    for _i, (_m, _c) in enumerate(zip(models, ("#4477aa", "#ee6677"), strict=True)):
        _sub = sims[sims["modèle"] == _m]
        _x = [j + 0.2 * _i for j in range(len(_sub))]
        ax_s.vlines(_x, _sub["min"], _sub["max"], color=_c, alpha=0.4)
        ax_s.scatter(_x, _sub["p50"], color=_c, s=12, label=f"{_m} (médiane, min-max)")
    ax_s.set_xticks(range(len(sims) // 2), [q[:3] for q in sims["question"][: len(sims) // 2]])
    ax_s.set_ylabel("similarité cosinus")
    ax_s.legend(fontsize=7)
    fig_s.tight_layout()
    sep = sims.groupby("modèle")["séparation"].mean()
    mo.vstack(
        [
            mo.md(
                "### 4.4 Plage des similarités\nLes similarités d'e5 sont tassées dans une plage "
                "étroite et haute (constat M2b sur les thèmes) ; ce qui compte pour le classement "
                "est la séparation relative des extraits pertinents. Séparation moyenne "
                f"(écart pertinents / autres, rapporté à l'étendue) : `{sep.round(3).to_dict()}`."
            ),
            fig_s,
        ]
    )
    return (sep,)


@app.cell
def _(ci, mo, models, res4, sep):
    _bge = res4[(models[0], "semantique")]
    _e5 = res4[(models[1], "semantique")]
    mo.md(
        f"""
        ## 5. Résultats et limites
        - Rappel@4 sémantique : **{models[0]} {_bge.recall:.3f}**, **{models[1]} {_e5.recall:.3f}** ;
          succès@4 : {_bge.hit_rate:.3f} contre {_e5.hit_rate:.3f}.
        - L'écart par question est faible et son intervalle bootstrap
          [{ci[0]:+.3f} ; {ci[1]:+.3f}] touche zéro : avec 13 questions, on ne peut pas conclure.
        - Séparation relative des pertinents : {sep[models[0]]:.3f} ({models[0]}) contre
          {sep[models[1]]:.3f} ({models[1]}) : malgré des valeurs absolues tassées, la séparation
          d'e5 est comparable. Conséquence pratique : **un seuil ou une marge de similarité doit être calibré par
          modèle** (déjà constaté pour les thèmes, D16).
        - Limites : jeu de fumée petit ; annotation faite en lisant le corpus à partir de mots-clés,
          donc susceptible de sous-estimer les extraits pertinents formulés autrement (biais
          défavorable à la recherche sémantique) ; e5 tronque les extraits au-delà de 512 tokens,
          ce qui ne l'a pas pénalisé ici.

        ## 6. Décision
        Pas de changement du modèle par défaut en M2 (`bge-m3`), faute d'écart significatif. La
        comparaison est refaite en M4 sur le jeu complet (≈ 60 questions), avec la même fixture et
        les mêmes fonctions (`moi_electeur_eval.recall`). e5 reste indexé. Notes :
        `docs/notes-implementation.md` (M2d).
        """
    )
    return


if __name__ == "__main__":
    app.run()
