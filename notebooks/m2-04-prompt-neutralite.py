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
        # M2-04 : Prompt de neutralité, analyse de réponses enregistrées

        | Métadonnée | Valeur |
        |---|---|
        | Date | 2026-11-27 |
        | Auteur | Claude Code (revue : mainteneur) |
        | Données | 2 réponses SSE réelles de `POST /api/ask` (`notebooks/fixtures/m2-ask-nucleaire-*.sse`, `m2-ask-runs.json`), corpus `0b54d163dbe7f40a` |
        | Modèle / prompt | `claude-haiku-5-5` (mode rapide), `claude-sonnet-5-5` (mode approfondi) ; `prompts/rag_system.md` version 1 |
        | Coût | 0,0075 $ + 0,134 $, dépensés une fois le 2026-11-27 ; **aucun appel en CI** |
        | Graine | ordre des candidats tiré par le serveur (enregistré dans l'événement `meta`) |
        | Statut | exploration (2 réponses), à étendre en M4 |
        | Code | `apps/web/src/lib/rag/` (route `/api/ask`), `prompts/rag_system.md`, `prompts/forbidden_words.json` |

        ## 1. Question et contexte
        Le prompt système impose (SPEC § 6.2, § 1) : désigner les candidats par un jeton `{{cN}}`
        sans jamais les nommer, traiter chacun dans l'ordre tiré au sort avec une place comparable,
        écrire exactement « Aucune proposition recensée dans le programme officiel sur ce point. »
        quand les extraits ne traitent pas la question, appuyer chaque affirmation sur une
        citation, et ne jamais classer. Les deux réponses enregistrées respectent-elles ces règles ?
        Les sections « vides » sont-elles de vrais silences ?

        ## 2. Hypothèses et alternatives envisagées
        | Contrôle | Méthode retenue | Alternative |
        |---|---|---|
        | Anonymat | recherche des noms, noms de famille et partis de `election_config.json` dans la prose | juge LLM (coûteux, non déterministe) |
        | Silences | égalité exacte avec la phrase imposée ; confrontation au jeu de fumée | lecture humaine seule |
        | Citations | champ `verified` du flux + candidat de la citation = candidat de la section | revérifier les sous-chaînes (fait par la route) |
        | Équilibre | longueur des sections en caractères et en phrases | nombre de citations |
        | Classement | motifs de `prompts/forbidden_words.json` (source unique, aussi utilisée par la route) | lexique plus large |

        ## 3. Formalisation
        Réponse $T$ = concaténation des `delta`. Sections : $T$ découpé sur les lignes
        `### {{cN}}`. Pour une section non vide $s$ : $\ell(s)$ = longueur en caractères,
        $n(s)$ = nombre de phrases ; équilibre mesuré par le coefficient de variation
        $\mathrm{CV} = \sigma(\ell) / \mu(\ell)$ et le rapport $\max \ell / \min \ell$. Silence faux :
        section vide pour un candidat qui a des extraits pertinents dans le jeu de fumée
        (question `q01-nucleaire`).
        """
    )
    return


@app.cell
def _():
    import json
    import re

    import pandas as pd

    from moi_electeur_eval.report import load_fixture
    from moi_electeur_eval.smoke import load_questions
    from moi_electeur_pipeline.paths import repo_root

    root = repo_root()
    fixtures = root / "notebooks" / "fixtures"
    runs = json.loads((fixtures / "m2-ask-runs.json").read_text(encoding="utf-8"))
    config = json.loads(
        (root / "data" / "elections" / "fr-presidentielle-2022" / "election_config.json").read_text(
            encoding="utf-8"
        )
    )
    forbidden = json.loads((root / "prompts" / "forbidden_words.json").read_text(encoding="utf-8"))
    smoke = {q.id: q for q in load_questions()}["q01-nucleaire"]
    retrieval = load_fixture(fixtures / "m2-retrieval-smoke.json")

    SILENCE = "Aucune proposition recensée dans le programme officiel sur ce point."

    def parse_sse(text):
        """Événements `data:` d'un flux SSE, dans l'ordre."""
        events = []
        for block in text.split("\n\n"):
            for line in block.splitlines():
                if line.startswith("data: "):
                    events.append(json.loads(line[len("data: ") :]))
        return events

    def sections(events):
        """Texte complet, sections {jeton: texte} et bloc -> jeton (pour les citations)."""
        text, block_token, current = "", {}, None
        header = re.compile(r"### \{\{(c\d+)\}\}")
        for e in events:
            if e["type"] != "delta":
                continue
            before = text
            text += e["text"]
            found = header.findall(text)
            current = found[-1] if found else None
            # Un bloc appartient à la section ouverte au moment de son premier fragment.
            if e["block"] not in block_token:
                opened = header.findall(before + e["text"][:1])
                block_token[e["block"]] = opened[-1] if opened else current
        parts = re.split(r"^### \{\{(c\d+)\}\}\s*$", text, flags=re.M)
        body = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
        return text, parts[0], body, block_token

    return (
        SILENCE,
        config,
        fixtures,
        forbidden,
        parse_sse,
        pd,
        re,
        retrieval,
        runs,
        sections,
        smoke,
    )


@app.cell
def _(fixtures, mo, parse_sse, pd, runs, sections):
    answers = {}
    for _run in runs["runs"]:
        _events = parse_sse((fixtures / _run["fichier"]).read_text(encoding="utf-8"))
        _meta = _events[0]
        _done = _events[-1]
        _text, _preamble, _body, _blocks = sections(_events)
        answers[_run["modele"]] = {
            "run": _run,
            "events": _events,
            "meta": _meta,
            "done": _done,
            "text": _text,
            "preamble": _preamble,
            "body": _body,
            "blocks": _blocks,
            "token_to_candidate": {c["token"]: c["candidate_id"] for c in _meta["candidates"]},
        }
    overview = pd.DataFrame(
        [
            {
                "modèle": _m,
                "mode": _a["run"]["mode"],
                "coût ($)": _a["run"]["cout_usd"],
                "tokens entrée": _a["run"]["tokens_entree"],
                "tokens sortie": _a["run"]["tokens_sortie"],
                "latence (s)": _a["run"]["latence_s"],
                "caractères": len(_a["text"]),
                "citations": sum(1 for e in _a["events"] if e["type"] == "citation"),
                "fin": _a["done"]["stop_reason"],
                "signalements route": len(_a["done"]["neutrality_flags"]),
            }
            for _m, _a in answers.items()
        ]
    )
    mo.vstack(
        [
            mo.md(
                f"## 4. Expérimentation\nQuestion : « {runs['question']} », 12 candidats, 4 extraits chacun."
            ),
            overview,
        ]
    )
    return (answers,)


@app.cell
def _(answers, config, mo, pd, re):
    # 4.1 Jetons seuls : structure et absence de noms.
    _names = []
    for _c in config["candidates"]:
        _names += [_c["name"], _c["name"].split(" ", 1)[1], _c["party"]]
    _name_re = re.compile(
        "|".join(
            r"(?<!\w)" + re.escape(n) + r"(?!\w)"
            for n in sorted(set(_names), key=len, reverse=True)
        ),
        re.IGNORECASE,
    )
    _rows = []
    for _m, _a in answers.items():
        _order = [c["token"] for c in _a["meta"]["candidates"]]
        _rows.append(
            {
                "modèle": _m,
                "sections dans l'ordre du tirage": list(_a["body"]) == _order,
                "texte avant la 1re section": repr(_a["preamble"].strip()),
                "jetons hors tirage": sorted(
                    set(re.findall(r"\{\{(c\d+)\}\}", _a["text"])) - set(_order)
                ),
                "noms ou partis dans la prose": _name_re.findall(_a["text"]),
            }
        )
    tokens_check = pd.DataFrame(_rows)
    for _r in _rows:
        assert _r["sections dans l'ordre du tirage"] and not _r["noms ou partis dans la prose"]
        assert not _r["jetons hors tirage"] and _r["texte avant la 1re section"] == "''"
    mo.vstack(
        [
            mo.md(
                "### 4.1 Jetons `{{cN}}` seuls\nRecherche de "
                f"{len(set(_names))} noms complets, noms de famille et partis dans la prose."
            ),
            tokens_check,
        ]
    )
    return (tokens_check,)


@app.cell
def _(SILENCE, answers, mo, pd, retrieval, smoke):
    # 4.2 Silences : phrase exacte, puis confrontation au jeu de fumée et à la recherche.
    _rrf = retrieval["models"]["bge-m3"]["rankings"]["rrf"]["q01-nucleaire"]
    _rows = []
    for _m, _a in answers.items():
        for _tok, _txt in _a["body"].items():
            _cand = _a["token_to_candidate"][_tok]
            if "Aucune proposition" not in _txt:
                continue
            _expected = smoke.relevant(_cand)
            _rows.append(
                {
                    "modèle": _m,
                    "jeton": _tok,
                    "candidat": _cand,
                    "phrase exacte": _txt == SILENCE,
                    "silence attendu (jeu de fumée)": _cand in smoke.silent,
                    "extraits pertinents annotés": len(_expected),
                    "dont dans les 4 servis (bge-m3, RRF)": len(set(_rrf[_cand][:4]) & _expected),
                }
            )
    silences = pd.DataFrame(_rows)
    assert silences["phrase exacte"].all()
    false_silences = silences[~silences["silence attendu (jeu de fumée)"]]
    mo.vstack(
        [
            mo.md(
                "### 4.2 Silences\nToutes les sections vides reprennent la phrase imposée "
                "à l'identique. Confrontées au jeu de fumée, une seule correspond à un vrai "
                "silence du programme ; les autres sont des **silences faux** : le candidat traite "
                "le sujet, mais aucun des 4 extraits servis par `/retrieve` (bge-m3, RRF) n'est "
                "pertinent. Le modèle a donc bien appliqué la consigne ; l'erreur vient de la "
                "recherche (voir m2-03, plein texte noyé par le lexème `le`)."
            ),
            silences,
        ]
    )
    return false_silences, silences


@app.cell
def _(answers, mo, pd, smoke):
    # 4.3 Citations : vérifiées, du bon candidat, sur des extraits annotés pertinents.
    _rows = []
    for _m, _a in answers.items():
        _cits = [e for e in _a["events"] if e["type"] == "citation"]
        _own = [
            c
            for c in _cits
            if _a["token_to_candidate"].get(_a["blocks"].get(c["block"])) == c["candidate_id"]
        ]
        _rel = [c for c in _cits if c["chunk_id"] in smoke.relevant(c["candidate_id"])]
        _rows.append(
            {
                "modèle": _m,
                "citations": len(_cits),
                "vérifiées": sum(c["verified"] for c in _cits),
                "du candidat de la section": len(_own),
                "sur un extrait annoté pertinent": len(_rel),
                "non vérifiées (route)": _a["done"]["unverified_citations"],
                "sections non vides sans citation": [
                    t
                    for t, txt in _a["body"].items()
                    if "Aucune proposition" not in txt
                    and t not in {_a["blocks"].get(c["block"]) for c in _cits}
                ],
            }
        )
    citations = pd.DataFrame(_rows)
    for _r in _rows:
        assert _r["vérifiées"] == _r["citations"] == _r["du candidat de la section"]
    mo.vstack([mo.md("### 4.3 Citations"), citations])
    return (citations,)


@app.cell
def _(answers, mo, pd, re):
    # 4.4 Équilibre des sections non vides.
    def _sentences(txt):
        return len([s for s in re.split(r"(?<=[.!?])\s+", txt.strip()) if s])

    _rows = []
    for _m, _a in answers.items():
        _lens = [len(t) for t in _a["body"].values() if "Aucune proposition" not in t]
        _sent = [_sentences(t) for t in _a["body"].values() if "Aucune proposition" not in t]
        _mean = sum(_lens) / len(_lens)
        _sd = (sum((x - _mean) ** 2 for x in _lens) / len(_lens)) ** 0.5
        _rows.append(
            {
                "modèle": _m,
                "sections non vides": len(_lens),
                "caractères min / moy. / max": f"{min(_lens)} / {_mean:.0f} / {max(_lens)}",
                "CV": round(_sd / _mean, 2),
                "max / min": round(max(_lens) / min(_lens), 2),
                "phrases min-max": f"{min(_sent)}-{max(_sent)}",
            }
        )
    balance = pd.DataFrame(_rows)
    mo.vstack(
        [
            mo.md(
                "### 4.4 Place comparable\nLe prompt demande deux à quatre phrases par candidat."
            ),
            balance,
        ]
    )
    return (balance,)


@app.cell
def _(answers, forbidden, mo, pd, re):
    # 4.5 Formulations interdites et ton (première personne reprise des programmes).
    _forbidden_re = re.compile("|".join(forbidden["patterns"]), re.IGNORECASE)
    _first_person = re.compile(r"(?<!\w)(nous|notre|nos|je|j['’]|mon|ma|mes)(?!\w)", re.IGNORECASE)
    _rows = []
    for _m, _a in answers.items():
        _rows.append(
            {
                "modèle": _m,
                "formulations interdites": _forbidden_re.findall(_a["text"]),
                "signalements de la route": _a["done"]["neutrality_flags"],
                "1re personne (reprise des programmes)": [
                    m.group(0) for m in _first_person.finditer(_a["text"])
                ],
            }
        )
    tone = pd.DataFrame(_rows)
    for _r in _rows:
        assert not _r["formulations interdites"] and not _r["signalements de la route"]
    mo.vstack([mo.md("### 4.5 Formulations interdites et ton"), tone])
    return (tone,)


@app.cell
def _(balance, false_silences, mo, tone):
    _fs = {
        m: sorted(false_silences[false_silences["modèle"] == m]["candidat"])
        for m in false_silences["modèle"].unique()
    }
    _fp = dict(zip(tone["modèle"], tone["1re personne (reprise des programmes)"], strict=True))
    mo.md(
        f"""
        ## 5. Résultats et limites
        - **Anonymat respecté** : aucune des deux réponses ne nomme un candidat ni un parti ;
          sections exactement dans l'ordre tiré au sort, sans introduction ni conclusion.
        - **Phrase de silence exacte** partout. Mais **silences faux** dus à la recherche :
          `{_fs}`. Le seul vrai silence du jeu de fumée sur cette question est bien rendu.
          Les deux modèles déclarent exactement les mêmes silences : ils reçoivent les mêmes
          extraits, ce qui confirme que la cause est la recherche et non le modèle.
        - **Citations** : toutes vérifiées par la route, toutes issues d'un extrait du candidat de la
          section et d'un extrait annoté pertinent dans le jeu de fumée ; chaque section non vide
          en porte au moins une.
        - **Équilibre** : `{balance.to_dict("records")}`. Écart du simple au double environ entre la
          section la plus courte et la plus longue, dans la consigne de 2 à 4 phrases.
        - **Ton** : aucune formulation interdite, aucun signalement. La première personne apparaît
          quand le modèle reprend le texte d'un programme (`{_fp}`), surtout avec Haiku : ce n'est
          pas un classement, mais c'est une entorse au ton encyclopédique.
        - Limites : deux réponses, une seule question ; pas de demande de recommandation testée en
          réel (le jeu de fumée en contient deux, à rejouer en M4 avec un coût annoncé).

        ## 6. Décision
        Prompt `version: 1` conservé : les règles de forme sont respectées. Priorité à la
        recherche (m2-03) pour réduire les silences faux. Piste de prompt pour M4 : demander de
        reformuler à la troisième personne plutôt que de recopier (« nous » → « le programme »).
        Notes : `docs/notes-implementation.md` (M2d).
        """
    )
    return


if __name__ == "__main__":
    app.run()
