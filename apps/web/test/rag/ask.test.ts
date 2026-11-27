// /api/ask (PLAN § 4.5) : chaîne complète avec client Claude simulé, aucun appel réel.
import Anthropic from "@anthropic-ai/sdk";
import type { AskCitationEvent, AskDoneEvent, AskMetaEvent } from "@moi-electeur/schemas-ts";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RetrieveError } from "../../src/lib/rag/retrieve";
import {
  ALICE_TEXT,
  ask,
  DEFAULT_SCRIPT,
  ELECTION,
  harness,
  notIndexed,
  QUESTION,
  readEvents,
  retrieveResponse,
} from "./helpers";

const body = (extra: Record<string, unknown> = {}) => ({
  election_id: ELECTION,
  question: QUESTION,
  ...extra,
});

afterEach(() => vi.restoreAllMocks());

describe("flux SSE", () => {
  it("meta, deltas, citations vérifiées, done", async () => {
    const h = harness();
    const res = await h.handler(ask(body()));
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toMatch(/^text\/event-stream/);
    expect(res.headers.get("cache-control")).toMatch(/no-store/);
    const events = await readEvents(res);
    expect(events[0]!.type).toBe("meta");
    expect(events.at(-1)!.type).toBe("done");
    const text = events.flatMap((e) => (e.type === "delta" ? [e.text] : [])).join("");
    expect(text).toBe(DEFAULT_SCRIPT.blocks.map((b) => b.text).join(""));
    const cits = events.filter((e): e is AskCitationEvent => e.type === "citation");
    expect(cits).toHaveLength(1);
    expect(cits[0]).toMatchObject({ block: 1, verified: true, page_number: 4 });
    const done = events.at(-1) as AskDoneEvent;
    expect(done).toEqual({
      type: "done",
      stop_reason: "end_turn",
      unverified_citations: 0,
      neutrality_flags: [],
    });
  });

  it("meta : ordre tiré au sort, jetons c1..cN, candidat sans extrait signalé", async () => {
    const h = harness();
    const meta = (await readEvents(await h.handler(ask(body()))))[0] as AskMetaEvent;
    expect(meta).toMatchObject({
      election_id: ELECTION,
      corpus_version: "0123456789abcdef",
      prompt_version: "1",
      model: "claude-haiku-5-5",
      cached: false,
    });
    expect(meta.candidates.map((c) => c.token)).toEqual(["c1", "c2", "c3"]);
    expect(new Set(meta.candidates.map((c) => c.candidate_id))).toEqual(
      new Set(["alice", "bruno", "david"]),
    );
    expect(meta.candidates.find((c) => c.candidate_id === "david")!.has_excerpts).toBe(false);
  });

  it("l'ordre dépend du tirage, pas de l'ordre (alphabétique) de /retrieve", async () => {
    const orders = new Set<string>();
    for (const r of [0.01, 0.5, 0.99, 0.3, 0.7]) {
      const h = harness({ rng: () => r });
      const meta = (await readEvents(await h.handler(ask(body()))))[0] as AskMetaEvent;
      orders.add(meta.candidates.map((c) => c.candidate_id).join(","));
    }
    expect(orders.size).toBeGreaterThan(1);
  });

  it("citation hors des extraits renvoyés : « non vérifiée » et comptée", async () => {
    const h = harness({
      script: {
        blocks: [
          { text: "A", citations: [{ document_index: 0, cited_text: "retraite à 62 ans" }] },
          { text: "B", citations: [{ document_index: 7, cited_text: "retraite" }] },
        ],
      },
    });
    const events = await readEvents(await h.handler(ask(body())));
    const cits = events.filter((e): e is AskCitationEvent => e.type === "citation");
    expect(cits.map((c) => c.verified)).toEqual([false, false]);
    expect(cits[1]).toMatchObject({ chunk_id: null, candidate_id: null, page_number: null });
    expect((events.at(-1) as AskDoneEvent).unverified_citations).toBe(2);
  });

  it("formulation de classement dans la réponse : signalée, texte non réécrit", async () => {
    const h = harness({ script: { blocks: [{ text: "C'est la Meilleure proposition." }] } });
    const events = await readEvents(await h.handler(ask(body())));
    const text = events.flatMap((e) => (e.type === "delta" ? [e.text] : [])).join("");
    expect(text).toBe("C'est la Meilleure proposition.");
    expect((events.at(-1) as AskDoneEvent).neutrality_flags).toEqual(["meilleure"]);
  });

  it("réponse tronquée ou refus : stop_reason transmis", async () => {
    for (const stop of ["max_tokens", "refusal"] as const) {
      const h = harness({ script: { blocks: [{ text: "x" }], stop_reason: stop } });
      const events = await readEvents(await h.handler(ask(body())));
      expect((events.at(-1) as AskDoneEvent).stop_reason).toBe(stop);
    }
  });

  it("erreur de Claude en cours de flux : événement error, pas de trace", async () => {
    const h = harness({
      script: { ...DEFAULT_SCRIPT, failAfterFirstBlock: new Error(`boum ${QUESTION}`) },
    });
    const events = await readEvents(await h.handler(ask(body())));
    const last = events.at(-1)!;
    expect(last.type).toBe("error");
    expect(JSON.stringify(last)).not.toContain(QUESTION);
    expect(h.logs.at(-1)).toMatchObject({ status: 500 });
  });
});

describe("requête envoyée à Claude", () => {
  it("un bloc document par extrait, citations natives, titre {{cN}} · document · p. X", async () => {
    const h = harness({ rng: () => 0 });
    const meta = (await readEvents(await h.handler(ask(body()))))[0] as AskMetaEvent;
    const params = h.claude.calls[0]!;
    expect(params.model).toBe("claude-haiku-5-5");
    expect(params.stream === undefined || params.stream === true).toBe(true);
    expect(params.max_tokens).toBeLessThanOrEqual(8192);
    expect(params.system).toBeDefined();
    const user = params.messages.at(-1)!;
    expect(user.role).toBe("user");
    const blocks = user.content as Anthropic.ContentBlockParam[];
    const docs = blocks.filter((b): b is Anthropic.DocumentBlockParam => b.type === "document");
    expect(docs).toHaveLength(2);
    const tokenOf = (id: string) => meta.candidates.find((c) => c.candidate_id === id)!.token;
    for (const d of docs) {
      expect(d.citations).toEqual({ enabled: true });
      expect(d.source).toMatchObject({ type: "text", media_type: "text/plain" });
    }
    const alice = docs.find((d) => (d.source as Anthropic.PlainTextSource).data === ALICE_TEXT)!;
    expect(alice.title).toBe(`{{${tokenOf("alice")}}} · Programme · p. 4`);
    const text = blocks.filter((b): b is Anthropic.TextBlockParam => b.type === "text");
    expect(text).toHaveLength(1);
    const order = meta.candidates.map((c) => `{{${c.token}}}`).join(", ");
    expect(text[0]!.text).toContain(order);
    expect(text[0]!.text).toContain(QUESTION);
    // Candidat sans extrait : désigné pour la phrase de silence.
    expect(text[0]!.text).toMatch(
      new RegExp(`aucun extrait[^\\n]*\\{\\{${tokenOf("david")}\\}\\}`, "i"),
    );
    // Les noms et identifiants des candidats ne sont jamais transmis à Claude.
    expect(JSON.stringify(params)).not.toMatch(/alice|bruno|david/);
  });

  it("historique : jetons des tours précédents ré-attribués au tirage courant", async () => {
    const h = harness({ rng: () => 0 });
    const history = [
      {
        question: "Et sur l'école ?",
        answer: "### {{c1}}\n\nTexte A.\n\n### {{c2}}\n\nTexte B.",
        candidates: ["bruno", "alice"],
      },
    ];
    const meta = (await readEvents(await h.handler(ask(body({ history })))))[0] as AskMetaEvent;
    const tokenOf = (id: string) => meta.candidates.find((c) => c.candidate_id === id)!.token;
    const msgs = h.claude.calls[0]!.messages;
    expect(msgs.map((m) => m.role)).toEqual(["user", "assistant", "user"]);
    expect(msgs[0]!.content).toBe("Et sur l'école ?");
    expect(msgs[1]!.content).toBe(
      `### {{${tokenOf("bruno")}}}\n\nTexte A.\n\n### {{${tokenOf("alice")}}}\n\nTexte B.`,
    );
  });

  it("historique : candidat absent de la sélection courante neutralisé", async () => {
    const h = harness();
    const history = [{ question: "q", answer: "{{c1}} et {{c2}}", candidates: ["alice", "zoe"] }];
    const meta = (await readEvents(await h.handler(ask(body({ history })))))[0] as AskMetaEvent;
    const alice = meta.candidates.find((c) => c.candidate_id === "alice")!.token;
    const prev = h.claude.calls[0]!.messages[1]!.content as string;
    expect(prev).toBe(`{{${alice}}} et [candidat hors sélection]`);
  });

  it("filtres transmis à /retrieve avec k = 4", async () => {
    const h = harness();
    await readEvents(
      await h.handler(ask(body({ candidate_ids: ["alice", "bruno"], theme: "social" }))),
    );
    expect(h.retrieveCalls[0]).toEqual({
      election_id: ELECTION,
      question: QUESTION,
      candidate_ids: ["alice", "bruno"],
      theme: "social",
      k: 4,
    });
  });
});

describe("validation de l'entrée", () => {
  it.each([
    ["JSON invalide", "{"],
    ["question vide", { election_id: ELECTION, question: "" }],
    ["question trop longue", { election_id: ELECTION, question: "x".repeat(501) }],
    ["caractère de contrôle", { election_id: ELECTION, question: "retraite\u0000" }],
    ["champ inconnu", { election_id: ELECTION, question: "q", debug: true }],
    ["élection mal formée", { election_id: "Pas un slug", question: "q" }],
    [
      "plus de 3 tours d'historique",
      {
        election_id: ELECTION,
        question: "q",
        history: Array.from({ length: 4 }, () => ({
          question: "q",
          answer: "a",
          candidates: ["a"],
        })),
      },
    ],
    [
      "jeton d'historique sans candidat",
      {
        election_id: ELECTION,
        question: "q",
        history: [{ question: "q", answer: "{{c2}}", candidates: ["alice"] }],
      },
    ],
  ])("%s : 400 sans appel à /retrieve ni à Claude", async (_name, payload) => {
    const h = harness();
    const res = await h.handler(ask(payload));
    expect(res.status).toBe(400);
    expect(h.retrieveCalls).toHaveLength(0);
    expect(h.claude.calls).toHaveLength(0);
    expect(await res.text()).not.toContain("retraite");
  });

  it("corps trop volumineux : 413", async () => {
    const h = harness();
    const res = await h.handler(ask(JSON.stringify(body({ pad: "x".repeat(200_000) }))));
    expect(res.status).toBe(413);
  });
});

describe("limite de débit (10 questions / 10 min par IP)", () => {
  it("11e question refusée (429, Retry-After), autre IP libre, fenêtre glissante", async () => {
    const h = harness();
    for (let i = 0; i < 10; i++) {
      expect((await h.handler(ask(body(), "198.51.100.1"))).status).toBe(200);
    }
    const refused = await h.handler(ask(body(), "198.51.100.1"));
    expect(refused.status).toBe(429);
    expect(Number(refused.headers.get("retry-after"))).toBeGreaterThan(0);
    expect((await h.handler(ask(body(), "198.51.100.2"))).status).toBe(200);
    h.clock.t += 10 * 60_000 + 1;
    expect((await h.handler(ask(body(), "198.51.100.1"))).status).toBe(200);
  });

  it("l'IP n'est jamais conservée en clair", async () => {
    const h = harness();
    await h.handler(ask(body(), "198.51.100.77"));
    expect(h.limiter.keys().join(" ")).not.toContain("198.51.100.77");
    expect(JSON.stringify(h.logs)).not.toContain("198.51.100.77");
  });

  it("derrière le proxy : la dernière adresse de X-Forwarded-For compte", async () => {
    const h = harness();
    for (let i = 0; i < 10; i++) await h.handler(ask(body(), `10.0.0.${i}, 198.51.100.9`));
    expect((await h.handler(ask(body(), "10.9.9.9, 198.51.100.9"))).status).toBe(429);
  });
});

describe("plafond budgétaire quotidien", () => {
  it("coût calculé depuis l'usage renvoyé et la table de tarifs", async () => {
    const h = harness({
      script: { ...DEFAULT_SCRIPT, usage: { input_tokens: 16_000, output_tokens: 1_500 } },
    });
    await readEvents(await h.handler(ask(body())));
    // Haiku 5.5 : 0,10 $ / M en entrée, 0,50 $ / M en sortie.
    expect(h.budget.spent()).toBeCloseTo(0.0016 + 0.00075, 10);
    expect(h.logs.at(-1)!.cost_usd).toBeCloseTo(0.00235, 10);
  });

  it("budget épuisé : 503 avec message, Claude non appelé", async () => {
    const h = harness({ budgetUsd: 0.001 });
    h.budget.record(0.001);
    const res = await h.handler(ask(body()));
    expect(res.status).toBe(503);
    expect((await res.json()).error).toBe("budget_exhausted");
    expect(h.claude.calls).toHaveLength(0);
  });

  it("une requête dont le coût maximal dépasserait le reste du budget est refusée", async () => {
    const h = harness({ budgetUsd: 0.002 });
    h.budget.record(0.0019);
    expect((await h.handler(ask(body()))).status).toBe(503);
  });

  it("le compteur repart à zéro le jour suivant (UTC)", async () => {
    const h = harness({ budgetUsd: 0.01 });
    h.budget.record(0.01);
    expect((await h.handler(ask(body()))).status).toBe(503);
    h.clock.t += 24 * 3600_000;
    expect((await h.handler(ask(body()))).status).toBe(200);
  });

  it("modèle sans tarif connu : refus (budget invérifiable)", async () => {
    const h = harness({ model: "claude-inconnu" });
    const res = await h.handler(ask(body()));
    expect(res.status).toBe(503);
    expect(h.claude.calls).toHaveLength(0);
  });

  it("erreur en cours de flux : le coût maximal réservé reste imputé", async () => {
    const h = harness({ script: { ...DEFAULT_SCRIPT, failAfterFirstBlock: new Error("coupure") } });
    await readEvents(await h.handler(ask(body())));
    expect(h.budget.spent()).toBeGreaterThan(0);
  });
});

describe("cache des réponses (première question seulement)", () => {
  it("même question : re-streamée sans Claude ni budget, cached = true", async () => {
    const h = harness();
    const first = await readEvents(await h.handler(ask(body())));
    const spent = h.budget.spent();
    const second = await readEvents(
      await h.handler(ask(body({ question: `  ${QUESTION.toUpperCase()} ` }))),
    );
    expect(h.claude.calls).toHaveLength(1);
    expect(h.budget.spent()).toBe(spent);
    expect((second[0] as AskMetaEvent).cached).toBe(true);
    expect(second.slice(1)).toEqual(first.slice(1));
    expect(h.logs.at(-1)).toMatchObject({ cache_hit: true, cost_usd: 0 });
  });

  it("avec historique : jamais servie depuis le cache", async () => {
    const h = harness();
    await readEvents(await h.handler(ask(body())));
    const history = [{ question: "q", answer: "a", candidates: ["alice"] }];
    await readEvents(await h.handler(ask(body({ history }))));
    expect(h.claude.calls).toHaveLength(2);
  });

  it("filtres ou version du corpus différents : pas de partage", async () => {
    let version = "0123456789abcdef";
    const h = harness({ retrieve: async () => retrieveResponse({ corpus_version: version }) });
    await readEvents(await h.handler(ask(body())));
    await readEvents(await h.handler(ask(body({ theme: "social" }))));
    await readEvents(await h.handler(ask(body({ candidate_ids: ["alice"] }))));
    expect(h.claude.calls).toHaveLength(3);
    version = "fedcba9876543210"; // réindexation
    await readEvents(await h.handler(ask(body())));
    expect(h.claude.calls).toHaveLength(4);
  });

  it("réponse en erreur, tronquée ou refusée : non mise en cache", async () => {
    for (const script of [
      { ...DEFAULT_SCRIPT, failAfterFirstBlock: new Error("x") },
      { blocks: [{ text: "x" }], stop_reason: "max_tokens" as const },
      { blocks: [{ text: "x" }], stop_reason: "refusal" as const },
    ]) {
      const h = harness({ script });
      await readEvents(await h.handler(ask(body())));
      expect(h.cache.size()).toBe(0);
    }
  });
});

describe("erreurs avant le flux", () => {
  it("élection non indexée : 404", async () => {
    const h = harness({ retrieve: notIndexed });
    expect((await h.handler(ask(body()))).status).toBe(404);
  });

  it("rag-service indisponible : 502, Claude non appelé", async () => {
    const h = harness({
      retrieve: async () => {
        throw new RetrieveError(503);
      },
    });
    expect((await h.handler(ask(body()))).status).toBe(502);
    expect(h.claude.calls).toHaveLength(0);
  });

  it("clé API absente : 503 « chat non configuré »", async () => {
    const h = harness({ noClient: true });
    const res = await h.handler(ask(body()));
    expect(res.status).toBe(503);
    expect((await res.json()).error).toBe("chat_unavailable");
  });

  it("méthode autre que POST : 405", async () => {
    const h = harness();
    expect((await h.handler(new Request("http://localhost/api/ask"))).status).toBe(405);
  });
});

describe("aucune trace de la question (SPEC § 6.3, RGPD art. 9)", () => {
  function captureOutput() {
    const written: string[] = [];
    const grab = (...args: unknown[]) => {
      written.push(
        args.map((a) => (typeof a === "string" ? a : (JSON.stringify(a) ?? String(a)))).join(" "),
      );
    };
    for (const level of ["log", "info", "warn", "error", "debug", "trace"] as const) {
      vi.spyOn(console, level).mockImplementation(grab);
    }
    vi.spyOn(process.stdout, "write").mockImplementation((chunk: unknown) => {
      written.push(String(chunk));
      return true;
    });
    vi.spyOn(process.stderr, "write").mockImplementation((chunk: unknown) => {
      written.push(String(chunk));
      return true;
    });
    return written;
  }

  it("ni dans la console ni dans les journaux, succès, cache et erreurs compris", async () => {
    const written = captureOutput();
    const history = [
      {
        question: "Mon opinion intime sur l'IVG ?",
        answer: "Réponse {{c1}}",
        candidates: ["alice"],
      },
    ];
    const cases = [
      harness(),
      harness({ script: { ...DEFAULT_SCRIPT, failAfterFirstBlock: new Error(QUESTION) } }),
      harness({
        retrieve: async () => {
          throw new Error(QUESTION);
        },
      }),
    ];
    for (const h of cases) {
      await (await h.handler(ask(body({ history })))).text();
      await (await h.handler(ask(body()))).text();
      await (await h.handler(ask(body()))).text(); // cache
      written.push(JSON.stringify(h.logs));
    }
    const all = written.join("\n");
    expect(all).not.toContain("retraite");
    expect(all).not.toContain("IVG");
  });

  it("enregistrement de journal limité aux champs autorisés", async () => {
    const h = harness();
    await (await h.handler(ask(body()))).text();
    expect(Object.keys(h.logs[0]!).sort()).toEqual(
      [
        "cache_hit",
        "cost_usd",
        "latency_ms",
        "model",
        "neutrality_flags",
        "status",
        "tokens_in",
        "tokens_out",
        "ts",
        "unverified_citations",
      ].sort(),
    );
  });
});

describe("suites de la relecture", () => {
  // rng = 0 : ordre [bruno, david, alice], donc c1 = bruno, c3 = alice ; document 0 = bruno.
  it("citation d'un extrait d'un autre candidat que la section en cours : non vérifiée", async () => {
    const h = harness({
      rng: () => 0,
      script: {
        blocks: [
          { text: "### {{c1}}\n\n" },
          {
            text: "Départ à 65 ans.",
            citations: [{ document_index: 0, cited_text: "porté à 65 ans" }],
          },
          { text: "\n\n### {{c3}}\n\n" },
          { text: "Idem.", citations: [{ document_index: 0, cited_text: "porté à 65 ans" }] },
        ],
      },
    });
    const events = await readEvents(await h.handler(ask(body())));
    const cits = events.filter((e): e is AskCitationEvent => e.type === "citation");
    expect(cits.map((c) => [c.candidate_id, c.verified])).toEqual([
      ["bruno", true],
      ["bruno", false],
    ]);
    expect((events.at(-1) as AskDoneEvent).unverified_citations).toBe(1);
  });

  it("budget épuisé : une réponse déjà en cache reste servie", async () => {
    const h = harness({ budgetUsd: 0.05 });
    await readEvents(await h.handler(ask(body())));
    h.budget.record(1);
    const res = await h.handler(ask(body()));
    expect(res.status).toBe(200);
    expect(((await readEvents(res))[0] as AskMetaEvent).cached).toBe(true);
    expect((await h.handler(ask(body({ theme: "social" })))).status).toBe(503);
  });

  it("API surchargée (529) avant toute génération : llm_unavailable, rien d'imputé", async () => {
    const overloaded = new Anthropic.InternalServerError(
      529,
      undefined,
      "overloaded",
      new Headers(),
    );
    const h = harness({ script: { ...DEFAULT_SCRIPT, failAtStart: overloaded } });
    const events = await readEvents(await h.handler(ask(body())));
    expect(events.at(-1)).toMatchObject({ type: "error", code: "llm_unavailable" });
    expect(h.budget.spent()).toBe(0);
    expect(h.logs.at(-1)).toMatchObject({ status: 503, cost_usd: 0 });
  });

  it("client déconnecté : la génération est interrompue", async () => {
    const h = harness();
    const ctrl = new AbortController();
    await h.handler(ask(body(), undefined, ctrl.signal));
    expect(h.claude.signals[0]!.aborted).toBe(false);
    ctrl.abort();
    expect(h.claude.signals[0]!.aborted).toBe(true);
  });

  it("Content-Length déclaré trop grand : 413 sans lecture du corps", async () => {
    const h = harness();
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "content-type": "application/json", "content-length": "5000000" },
      body: "{}",
    });
    expect((await h.handler(req)).status).toBe(413);
  });
});
