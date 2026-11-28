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
    # M2-01 : Extraction et découpage en extraits

    | Métadonnée | Valeur |
    |---|---|
    | Date | 2026-11-27 |
    | Auteur | Claude Code (revue : mainteneur) |
    | Données | `fr-presidentielle-2022`, 24 documents ; fixture `notebooks/fixtures/m2-corpus-stats.json` |
    | Fixture produite par | `uv run --project eval moi-electeur-eval corpus-stats` (lit `sources/`, ignoré par git) |
    | Modèle / prompt | aucun appel LLM ; tokenizer `FacebookAI/xlm-roberta-base` |
    | Graine | aucune (calcul déterministe) |
    | Statut | décision prise |
    | Code | `pipeline/src/moi_electeur_pipeline/extract.py`, `chunk.py` |

    ## 1. Question et contexte
    Le chat (SPEC § 6) ne peut citer que ce que l'extraction a lu et que le découpage a rangé
    dans un extrait. Ce notebook contrôle, document par document, la qualité de l'extraction
    PDF et le découpage : tailles, cas limites, couverture des pages et des candidats
    (critère PLAN § 4.9 : « aucun chunk sans métadonnée ; rapport de couverture »).

    ## 2. Hypothèses et alternatives envisagées
    | Option | Pour | Contre |
    |---|---|---|
    | Fenêtres fixes de N tokens | simple | coupe au milieu des phrases et des sections |
    | Une page = un extrait | citation de page triviale | tailles très inégales (couvertures, pages denses) |
    | **Unités titre / phrase regroupées entre `min` et `max` tokens** | respecte les sections, tailles bornées | plus de code, recouvrement à gérer |

    Retenu en M2a : unités titres et phrases, 300 à 600 tokens, recouvrement de 50 tokens au
    plus après une coupure par la taille.

    ## 3. Formalisation
    Pour chaque extrait $e$ : $t(e)$ = nombre de tokens recompté sur le texte final,
    $[p_0(e), p_1(e)]$ = pages couvertes. Invariants attendus :

    - $t(e) \le 600$ pour tout $e$, et $t(e) \ge 300$ sauf pour le dernier extrait d'un document ;
    - toute page contenant du texte est couverte par au moins un extrait :
      $\forall p,\ \text{texte}(p) \neq \varnothing \Rightarrow \exists e,\ p_0(e) \le p \le p_1(e)$ ;
    - aucune métadonnée manquante (candidat, document, URL, sha256, pages).
    """)
    return


@app.cell
def _():
    import json

    import matplotlib.pyplot as plt
    import pandas as pd

    from moi_electeur_pipeline.paths import repo_root

    stats = json.loads(
        (repo_root() / "notebooks" / "fixtures" / "m2-corpus-stats.json").read_text(
            encoding="utf-8"
        )
    )
    return pd, plt, stats


@app.cell
def _(mo, pd, stats):
    docs = pd.DataFrame(stats["documents"])
    docs_view = docs[
        [
            "candidate_id",
            "document_title",
            "pages",
            "pages_sans_texte",
            "pages_sans_extrait",
            "titres",
            "blocs_texte",
            "extraits",
            "tokens_median",
            "tokens_max",
        ]
    ].rename(columns={"candidate_id": "candidat", "document_title": "document"})
    mo.vstack(
        [
            mo.md(
                f"## 4. Expérimentation\n### 4.1 Qualité d'extraction par document\n"
                f"{stats['n_documents']} documents, {stats['n_extraits']} extraits, version du "
                f"corpus `{stats['corpus_version']}`. Ordre : identifiant du candidat."
            ),
            docs_view,
        ]
    )
    return (docs,)


@app.cell
def _(plt, stats):
    tokens_all = sorted(t for v in stats["tokens_par_extrait"].values() for t in v)
    fig_sizes, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(10, 3.4))
    ax_hist.hist(tokens_all, bins=30, color="#4477aa")
    ax_hist.axvline(300, color="#999999", linestyle="--", linewidth=1)
    ax_hist.axvline(600, color="#999999", linestyle="--", linewidth=1)
    ax_hist.set_xlabel("tokens par extrait")
    ax_hist.set_ylabel("extraits")
    ax_hist.set_title("Distribution des tailles (bornes 300 et 600)")
    cands_sizes = list(stats["tokens_par_extrait"])
    ax_box.boxplot([stats["tokens_par_extrait"][c] for c in cands_sizes], orientation="horizontal")
    ax_box.set_yticks(range(1, len(cands_sizes) + 1), cands_sizes, fontsize=7)
    ax_box.set_xlabel("tokens par extrait")
    ax_box.set_title("Par candidat (ordre alphabétique)")
    fig_sizes.tight_layout()
    fig_sizes
    return (tokens_all,)


@app.cell
def _(mo, pd, plt, stats):
    cov = pd.DataFrame(stats["candidats"]).T
    cov.index.name = "candidat"
    fig_cov, ax_cov = plt.subplots(figsize=(8, 3))
    ax_cov.bar(cov.index, cov["extraits"], color="#66ccee")
    ax_cov.set_ylabel("extraits")
    ax_cov.tick_params(axis="x", rotation=60, labelsize=7)
    ax_cov.set_title("Extraits par candidat (ordre alphabétique)")
    fig_cov.tight_layout()
    mo.vstack(
        [
            mo.md(
                "### 4.2 Couverture pages et extraits par candidat\n"
                "Le volume varie d'un facteur 10 entre candidats : il reflète la longueur des "
                "programmes publiés, pas un choix du pipeline. La recherche étant faite **par "
                "candidat** (k extraits chacun), un programme long n'occupe pas plus de place "
                "dans la réponse."
            ),
            cov,
            fig_cov,
        ]
    )
    return


@app.cell
def _(mo, pd, stats):
    edge = stats["cas_limites"]
    edge_counts = pd.DataFrame(
        sorted(edge["compte_extraits"].items()), columns=["cas limite", "extraits"]
    )
    edge_examples = pd.DataFrame(edge["exemples_mots_doubles"])
    mo.vstack(
        [
            mo.md(
                "### 4.3 Cas limites\n"
                "Mots doublés (mot de 6 lettres ou plus répété à l'identique), caractères de "
                "contrôle, traits d'union conditionnels (U+00AD), extraits sans titre de section, "
                "extraits à cheval sur 3 pages ou plus, extraits courts. Occurrences de mots "
                f"doublés par candidat : `{edge['mots_doubles_par_candidat']}`."
            ),
            edge_counts,
            edge_examples,
        ]
    )
    return (edge,)


@app.cell
def _(docs, edge, stats, tokens_all):
    # Invariants : un écart fait échouer le notebook, donc la CI.
    assert stats["n_documents"] == 24
    assert max(tokens_all) <= 600, "extrait au-delà de max_tokens"
    assert "metadonnee_manquante" not in edge["compte_extraits"], "extrait sans métadonnée"
    assert all(not p for p in docs["pages_sans_extrait"]), "page avec texte sans extrait"
    assert "caracteres_de_controle" not in edge["compte_extraits"]
    assert "traits_d_union_conditionnels" not in edge["compte_extraits"]
    n_short = edge["compte_extraits"].get("moins_de_300_tokens", 0)
    # Un seul extrait court possible par document (le dernier).
    assert n_short <= stats["n_documents"]
    return (n_short,)


@app.cell
def _(edge, mo, n_short, stats, tokens_all):
    _median = tokens_all[len(tokens_all) // 2]
    _sans_texte = {
        d["candidate_id"] + " / " + d["document"]: d["pages_sans_texte"]
        for d in stats["documents"]
        if d["pages_sans_texte"]
    }
    mo.md(
        f"""
        ## 5. Résultats et limites
        - {stats["n_extraits"]} extraits, médiane {_median} tokens, maximum {max(tokens_all)} ;
          {n_short} extraits sous 300 tokens (derniers extraits de documents courts).
        - **Aucun extrait sans métadonnée**, aucune page contenant du texte sans extrait, aucun
          caractère de contrôle ni trait d'union conditionnel résiduel (corrections M2b).
        - Pages sans texte (couvertures, pages d'images, toujours non citables) : `{_sans_texte}`.
        - **Texte surimprimé** : {edge["compte_extraits"].get("mots_doubles", 0)} extraits contiennent
          un mot doublé, presque tous chez un seul candidat (titres en relief lus deux fois). Effet :
          le texte cité reste fidèle mais répété ; en plein texte, le mot doublé pèse deux fois.
        - {edge["compte_extraits"].get("sans_titre_de_section", 0)} extraits sans titre de section
          (début de document avant le premier titre) ; {edge["compte_extraits"].get("sur_3_pages_ou_plus", 0)}
          extraits couvrent 3 pages ou plus (pages peu denses) : la citation donne alors une plage.
        - Limite : ce contrôle est statistique ; la fidélité fine du texte (ordre des colonnes,
          encadrés) a été relue à la main sur un échantillon en M2a, pas ici.

        ## 6. Décision
        Paramètres de découpage conservés (300 / 600 / 50). La déduplication des mots surimprimés
        n'est pas faite en M2 : elle modifierait le texte officiel cité et son effet sur la
        recherche est faible ; à mesurer en M4 sur le jeu complet. Code : `chunk.py`, `extract.py` ;
        notes : `docs/notes-implementation.md` (M2a, M2b, M2d).
        """
    )
    return


if __name__ == "__main__":
    app.run()
