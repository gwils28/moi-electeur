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
    # M2-03 : Recherche hybride, sémantique, plein texte et RRF

    | Métadonnée | Valeur |
    |---|---|
    | Date | 2026-11-27 |
    | Auteur | Claude Code (revue : mainteneur) |
    | Données | `fr-presidentielle-2022` (794 extraits) ; jeu de fumée `eval/smoke/questions-2022.jsonl` |
    | Fixture | `notebooks/fixtures/m2-retrieval-smoke.json` (`uv run --project eval moi-electeur-eval retrieval`) |
    | Modèle / prompt | bge-m3 et multilingual-e5-large ; PostgreSQL `french` ; aucun appel LLM |
    | Graine | 7 (bootstrap) |
    | Statut | décision prise : lexèmes fréquents ignorés en plein texte (`MAX_DF` = 0,5, branche `fix/rag-lexical`) |
    | Code | `services/rag/src/moi_electeur_rag/retrieve.py`, `ranking.py` ; `eval/src/moi_electeur_eval/collect.py` |

    ## 1. Question et contexte
    `/retrieve` (SPEC § 6.1, PLAN D17) fusionne, pour chaque candidat, les 20 extraits les plus
    proches sémantiquement et les 20 mieux classés en plein texte (`ts_rank_cd`, mots de la
    question en **OU**), par Reciprocal Rank Fusion. La fusion apporte-t-elle quelque chose par
    rapport à chaque méthode seule, au $k = 4$ servi ? Et chaque candidat reçoit-il bien au
    moins un extrait sur chaque question (critère PLAN § 4.9) ?

    ## 2. Hypothèses et alternatives envisagées
    | Méthode | Pour | Contre |
    |---|---|---|
    | Sémantique seule | robuste aux reformulations | rate les termes rares exacts (sigles : RIC, OTAN, SMIC) |
    | Plein texte seul | exact sur les sigles et noms propres | dépend des mots de la question, sensible aux mots vides |
    | **RRF (servi)** | sans calibrage des scores, robuste | n'aide que si les deux listes sont informatives |
    | Combinaison pondérée des scores | réglable | scores hétérogènes, calibrage par modèle (cf. m2-02) |

    ## 3. Formalisation
    Pour un candidat, avec $r_s(d)$ et $r_\ell(d)$ les rangs (à partir de 1) d'un extrait $d$
    dans les listes sémantique et plein texte (terme absent si $d$ n'y figure pas) :

    $$\text{RRF}(d) = \frac{1}{60 + r_s(d)} + \frac{1}{60 + r_\ell(d)}$$

    Exemple calculé à la main (cellule suivante) : un extrait 1er en sémantique et absent du
    plein texte obtient $1/61 \approx 0{,}01639$ ; un extrait 3e dans les deux listes obtient
    $2/63 \approx 0{,}03175$ et passe devant. Un plein texte bruité déplace donc les extraits
    que la sémantique avait bien classés. Métriques : rappel@k, succès@k et couverture, définis
    dans m2-02 et `moi_electeur_eval.recall`.

    **Plein texte servi** : les lexèmes de la question en OU, sans ceux présents dans plus de
    50 % des extraits de l'élection (`MAX_DF`, compté en SQL via l'index GIN). **Référence
    « brute » (M2b, non servie)** : tous les lexèmes en OU, la requête d'origine, gardée pour
    mesurer l'écart avant/après le correctif.
    """)
    return


@app.cell
def _(mo):
    from moi_electeur_rag.ranking import rrf

    _ex = rrf([["a", "b", "c"], ["x", "y", "c"]])
    assert _ex[0][0] == "c" and abs(_ex[0][1] - 2 / 63) < 1e-12
    assert dict(_ex)["a"] == 1 / 61
    mo.md(
        "Vérification de la formule sur l'exemple (fonction du service) : "
        + ", ".join(f"`{d}` {s:.5f}" for d, s in _ex)
    )
    return


@app.cell
def _():
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    from moi_electeur_eval.report import METHOD_LABELS, load_fixture, reports
    from moi_electeur_eval.smoke import load_questions
    from moi_electeur_pipeline.paths import repo_root

    fixture = load_fixture(repo_root() / "notebooks" / "fixtures" / "m2-retrieval-smoke.json")
    questions = load_questions(repo_root() / fixture["questions_file"])
    models = list(fixture["models"])
    res4 = reports(fixture, questions, k=4)
    return (
        METHOD_LABELS,
        fixture,
        models,
        np,
        pd,
        plt,
        questions,
        reports,
        res4,
    )


@app.cell
def _(METHOD_LABELS, mo, pd, res4):
    table = pd.DataFrame(
        [
            {
                "modèle": _m,
                "méthode": METHOD_LABELS[_meth],
                "rappel@4 macro": round(_r.recall, 3),
                "rappel@4 micro": round(_r.recall_micro, 3),
                "succès@4": round(_r.hit_rate, 3),
                "couverture 12/12 sur 15 questions": "oui" if _r.full_coverage else "non",
            }
            for (_m, _meth), _r in res4.items()
        ]
    )
    mo.vstack([mo.md("## 4. Expérimentation\n### 4.1 Rappel@4 par modèle et méthode"), table])
    return


@app.cell
def _(METHOD_LABELS, fixture, mo, models, plt, questions, reports):
    _ks = list(range(1, 7))
    _methods = ["semantique", "plein_texte", "rrf", "rrf_brut"]
    fig_k, axes_k = plt.subplots(1, len(models), figsize=(10, 3.2), sharey=True)
    for _ax, _m in zip(axes_k, models, strict=True):
        for _meth in _methods:
            _vals = [reports(fixture, questions, k=_k)[(_m, _meth)].recall for _k in _ks]
            _ax.plot(_ks, _vals, marker="o", label=METHOD_LABELS[_meth])
        _ax.axvline(4, color="#999999", linestyle="--", linewidth=1)
        _ax.set_title(_m, fontsize=9)
        _ax.set_xlabel("k")
    axes_k[0].set_ylabel("rappel@k (macro)")
    axes_k[0].legend(fontsize=7)
    fig_k.tight_layout()
    mo.vstack([mo.md("### 4.2 Rappel en fonction de k"), fig_k])
    return


@app.cell
def _(METHOD_LABELS, mo, models, pd, res4):
    _cols = {}
    for (_m, _meth), _r in res4.items():
        _cols[f"{_m[:6]} / {METHOD_LABELS[_meth]}"] = {
            q.question_id: q.recall for q in _r.questions if q.recall is not None
        }
    per_question = pd.DataFrame(_cols).round(2)
    _missed = {q.question_id: q.missed for q in res4[(models[0], "rrf")].questions if q.missed}
    mo.vstack(
        [
            mo.md(
                "### 4.3 Par question\nCandidats attendus sans aucun extrait pertinent dans "
                f"leurs 4 premiers, {models[0]} / RRF servi : `{_missed}`."
            ),
            per_question,
        ]
    )
    return


@app.cell
def _(fixture, mo, models, pd):
    _lex = fixture["models"][models[0]]["lexemes"]
    lexemes = pd.DataFrame(
        [
            {
                "question": _qid,
                "lexèmes": ", ".join(sorted(_d)),
                "retirés (fréquence > 50 %)": ", ".join(
                    f"{w} ({f:.0%})"
                    for w, f in sorted(_d.items())
                    if f > fixture["models"][models[0]]["max_df"]
                ),
            }
            for _qid, _d in _lex.items()
        ]
    )
    mo.vstack(
        [
            mo.md(
                "### 4.4 Diagnostic du plein texte (référence brute, M2b)\n"
                "En configuration `french`, « les » est réduit au lexème `le`, qui **n'est pas "
                "un mot vide** (seul « le » l'est) : il figure dans 99 % des extraits. Avec une "
                "requête en OU, chaque extrait correspond, et `ts_rank_cd` classe d'abord les "
                "extraits où `le` est dense. Le plein texte seul devient presque aléatoire et la "
                "fusion RRF dégrade la sémantique au lieu de la compléter. Le service ignore "
                "désormais ces lexèmes (colonne « retirés »). Autres défauts visibles : "
                "« proposent » n'est pas racinisé (`proposent`), « veulent-ils » produit `veulent-il`."
            ),
            lexemes,
        ]
    )
    return


@app.cell
def _(mo, models, np, res4):
    _rng = np.random.default_rng(7)

    def _diff(a, b):
        _x = np.array([q.recall for q in res4[a].questions if q.recall is not None])
        _y = np.array([q.recall for q in res4[b].questions if q.recall is not None])
        _d = _x - _y
        _boot = [_d[_rng.integers(0, len(_d), len(_d))].mean() for _ in range(5000)]
        return _d.mean(), np.quantile(_boot, 0.025), np.quantile(_boot, 0.975)

    diffs = {
        f"{_m} : RRF servi - sémantique": _diff((_m, "rrf"), (_m, "semantique")) for _m in models
    } | {
        f"{_m} : RRF servi - RRF brut (M2b)": _diff((_m, "rrf"), (_m, "rrf_brut")) for _m in models
    }
    mo.md(
        "### 4.5 Écarts et intervalles bootstrap (95 %, questions rééchantillonnées)\n"
        + "\n".join(f"- {k} : {v[0]:+.3f} [{v[1]:+.3f} ; {v[2]:+.3f}]" for k, v in diffs.items())
    )
    return (diffs,)


@app.cell
def _(diffs, mo, models, res4):
    _bge = models[0]
    _cov = all(r.full_coverage for (_m, meth), r in res4.items() if meth == "rrf")
    assert _cov, "un candidat sans extrait sur une question du jeu de fumée"
    mo.md(
        f"""
        ## 5. Résultats et limites
        - **Couverture** : avec RRF, chaque candidat reçoit 4 extraits sur chacune des 15 questions,
          pour les deux modèles (critère PLAN § 4.9 rempli). C'est structurel : il n'y a pas de
          seuil de score et la sémantique classe toujours tous les extraits du candidat.
        - **Avant le correctif (M2b)** : le RRF brut faisait moins bien que la sémantique seule
          ({res4[(_bge, "rrf_brut")].recall:.3f} contre {res4[(_bge, "semantique")].recall:.3f} en
          rappel@4 avec {_bge}) : plein texte en OU noyé par le lexème `le` (rappel@4 de
          {res4[(_bge, "plein_texte_brut")].recall:.3f} seul).
        - **Plein texte servi** (lexèmes de plus de 50 % des extraits ignorés) : plein texte seul à
          {res4[(_bge, "plein_texte")].recall:.3f}, fusion à {res4[(_bge, "rrf")].recall:.3f}
          ({_bge}) et {res4[(models[1], "rrf")].recall:.3f} ({models[1]}), au-dessus de la
          sémantique seule (écart {diffs[f"{_bge} : RRF servi - sémantique"][0]:+.3f}) ; gain sur
          la référence brute {diffs[f"{_bge} : RRF servi - RRF brut (M2b)"][0]:+.3f}, intervalle
          bootstrap loin de zéro.
        - **Limite importante** : les extraits pertinents ont été trouvés en lisant le corpus à
          partir de mots-clés ; le plein texte est donc avantagé par construction. Le gain du
          correctif est probablement surestimé, mais le diagnostic (`le` dans 99 % des
          extraits) est indépendant de l'annotation. 13 questions seulement.
        - Les candidats « silencieux » des 3 pièges reçoivent aussi 4 extraits (non pertinents par
          définition) : c'est au prompt de répondre « Aucune proposition recensée », voir m2-04.

        ## 6. Décision
        - Prise (2026-11-27, branche `fix/rag-lexical`) : `LEXICAL_SQL` ignore les lexèmes de la
          question dont la fréquence documentaire dépasse 50 % (`MAX_DF`), comptés en SQL ; tests
          `db` dans `services/rag/tests/test_store_retrieve.py`. Choix plutôt qu'une configuration
          `french` personnalisée : générique (tout mot omniprésent, pas seulement `le`), sans
          réindexation.
        - e5 devance bge-m3 avec le RRF servi sur ce jeu, mais sur 13 questions annotées par
          mots-clés : choix du modèle d'embedding maintenu en M4 (jeu d'environ 60 questions).
        - Le jeu de fumée et `moi-electeur-eval report` servent de test de non-régression du
          retrieval. Notes : `docs/notes-implementation.md` (M2d, correctif du plein texte).
        """
    )
    return


if __name__ == "__main__":
    app.run()
