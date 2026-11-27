// Choix du modèle par l'utilisateur : « rapide » (défaut) ou « approfondi » (modèle avec
// réflexion, plafond quotidien et limite de débit propres, en plus des plafonds communs).
import type { AskDeltaEvent, AskMetaEvent } from "@moi-electeur/schemas-ts";
import { describe, expect, it } from "vitest";
import { costUsd } from "../../src/lib/rag/pricing";
import {
  ask,
  BOOST_MODEL,
  DEFAULT_SCRIPT,
  ELECTION,
  harness,
  QUESTION,
  readEvents,
} from "./helpers";

const body = (extra: Record<string, unknown> = {}) => ({
  election_id: ELECTION,
  question: QUESTION,
  ...extra,
});
const deep = (extra: Record<string, unknown> = {}) => body({ mode: "approfondi", ...extra });

describe("mode rapide (défaut)", () => {
  it("sans mode : modèle rapide, effort bas, sans réflexion, meta.mode = rapide", async () => {
    const h = harness();
    const meta = (await readEvents(await h.handler(ask(body()))))[0] as AskMetaEvent;
    expect(meta).toMatchObject({ mode: "rapide", model: "claude-haiku-5-5" });
    const params = h.claude.calls[0]!;
    expect(params.model).toBe("claude-haiku-5-5");
    expect(params.thinking).toBeUndefined();
    expect(params.output_config).toEqual({ effort: "low" });
    expect(params.max_tokens).toBe(4096);
  });

  it("mode rapide explicite : même requête que sans mode", async () => {
    const a = harness({ rng: () => 0 });
    const b = harness({ rng: () => 0 });
    await (await a.handler(ask(body()))).text();
    await (await b.handler(ask(body({ mode: "rapide" })))).text();
    expect(b.claude.calls[0]).toEqual(a.claude.calls[0]);
  });
});

describe("mode approfondi", () => {
  it("modèle approfondi avec réflexion adaptative, mêmes extraits que le mode rapide", async () => {
    const fast = harness({ rng: () => 0 });
    await (await fast.handler(ask(body()))).text();
    const h = harness({ rng: () => 0 });
    const meta = (await readEvents(await h.handler(ask(deep()))))[0] as AskMetaEvent;
    expect(meta).toMatchObject({ mode: "approfondi", model: BOOST_MODEL });
    const params = h.claude.calls[0]!;
    expect(params.model).toBe(BOOST_MODEL);
    expect(params.thinking).toEqual({ type: "adaptive" });
    expect(params.output_config).toEqual({ effort: "medium" });
    expect(params.max_tokens).toBe(8192);
    expect(params.messages).toEqual(fast.claude.calls[0]!.messages);
    expect(params.system).toEqual(fast.claude.calls[0]!.system);
    expect(h.logs.at(-1)).toMatchObject({ status: 200, model: BOOST_MODEL });
  });

  it("la réflexion du modèle n'est jamais relayée ni mise en cache", async () => {
    const h = harness({
      script: {
        ...DEFAULT_SCRIPT,
        blocks: [
          { text: "PENSEE-INTERNE sur la question", thinking: true },
          ...DEFAULT_SCRIPT.blocks,
        ],
      },
    });
    const res = await h.handler(ask(deep()));
    const raw = await res.clone().text();
    expect(raw).not.toContain("PENSEE-INTERNE");
    const events = await readEvents(res);
    const text = events
      .filter((e): e is AskDeltaEvent => e.type === "delta")
      .map((e) => e.text)
      .join("");
    expect(text).toContain("### {{c1}}");
    expect(text).toContain("départ à 60 ans");
    const cits = events.filter((e) => e.type === "citation");
    expect(cits).toHaveLength(1);
    expect(cits[0]).toMatchObject({ verified: true });
    const again = await (await h.handler(ask(deep()))).text();
    expect(again).toContain('"cached":true');
    expect(again).not.toContain("PENSEE-INTERNE");
  });

  it("non configuré : 503 mode_unavailable, ni recherche ni appel à Claude", async () => {
    const h = harness({ boost: false });
    const res = await h.handler(ask(deep()));
    expect(res.status).toBe(503);
    expect(await res.json()).toMatchObject({ error: "mode_unavailable" });
    expect(h.retrieveCalls).toHaveLength(0);
    expect(h.claude.calls).toHaveLength(0);
    expect((await h.handler(ask(body()))).status).toBe(200);
  });

  it("modèle approfondi sans tarif connu : 503 mode_unavailable", async () => {
    const h = harness({ boost: { model: "claude-inconnu" } });
    const res = await h.handler(ask(deep()));
    expect(res.status).toBe(503);
    expect(await res.json()).toMatchObject({ error: "mode_unavailable" });
    expect(h.claude.calls).toHaveLength(0);
  });

  it("mode inconnu : 400", async () => {
    const h = harness();
    const res = await h.handler(ask(body({ mode: "turbo" })));
    expect(res.status).toBe(400);
    expect(h.claude.calls).toHaveLength(0);
  });

  it("limite de débit propre : au-delà, 429 mode_rate_limited, le mode rapide reste ouvert", async () => {
    const h = harness({ boost: { limit: 3 } });
    for (let i = 0; i < 3; i++)
      expect((await h.handler(ask(deep({ question: `q${i}` })))).status).toBe(200);
    const res = await h.handler(ask(deep({ question: "q4" })));
    expect(res.status).toBe(429);
    expect(await res.json()).toMatchObject({ error: "mode_rate_limited" });
    expect(Number(res.headers.get("retry-after"))).toBeGreaterThan(0);
    expect((await h.handler(ask(body({ question: "q5" })))).status).toBe(200);
  });

  it("plafond propre épuisé : 503 mode_budget_exhausted, le mode rapide reste ouvert", async () => {
    const h = harness();
    h.boostBudget!.record(0.5);
    const res = await h.handler(ask(deep()));
    expect(res.status).toBe(503);
    expect(await res.json()).toMatchObject({ error: "mode_budget_exhausted" });
    expect(h.claude.calls).toHaveLength(0);
    expect((await h.handler(ask(body()))).status).toBe(200);
  });

  it("le plafond commun s'applique aussi au mode approfondi", async () => {
    const h = harness();
    h.budget.record(1);
    const res = await h.handler(ask(deep()));
    expect(res.status).toBe(503);
    expect(await res.json()).toMatchObject({ error: "budget_exhausted" });
  });

  it("dépense imputée aux deux plafonds (coût réel au tarif du modèle approfondi)", async () => {
    const h = harness();
    await (await h.handler(ask(deep()))).text();
    // 10 000 tokens d'entrée à 2 $/M + 1 000 de sortie à 10 $/M.
    expect(h.budget.spent()).toBeCloseTo(0.03, 10);
    expect(h.boostBudget!.spent()).toBeCloseTo(0.03, 10);
    expect(h.logs.at(-1)!.cost_usd).toBeCloseTo(0.03, 10);
  });

  it("réservation refusée par le plafond approfondi : rien ne reste réservé au plafond commun", async () => {
    const h = harness({ boost: { budgetUsd: 0.05 } });
    const res = await h.handler(ask(deep()));
    expect(res.status).toBe(503);
    expect(await res.json()).toMatchObject({ error: "mode_budget_exhausted" });
    expect(h.budget.spent()).toBe(0);
    expect(h.budget.reserve(1)).not.toBeNull();
  });

  it("cache distinct par mode ; une réponse approfondie en cache reste servie plafond épuisé", async () => {
    const h = harness();
    await (await h.handler(ask(body()))).text();
    const first = (await readEvents(await h.handler(ask(deep()))))[0] as AskMetaEvent;
    expect(first.cached).toBe(false);
    expect(h.claude.calls).toHaveLength(2);
    h.boostBudget!.record(0.5);
    const again = (await readEvents(await h.handler(ask(deep()))))[0] as AskMetaEvent;
    expect(again).toMatchObject({ cached: true, mode: "approfondi", model: BOOST_MODEL });
    expect(h.claude.calls).toHaveLength(2);
  });
});

describe("tarif du modèle approfondi", () => {
  it("Sonnet 5.5 : lecture du cache à 0,10 $/M (et non 0,1 x l'entrée)", () => {
    expect(
      costUsd(BOOST_MODEL, {
        input_tokens: 0,
        output_tokens: 0,
        cache_read_input_tokens: 1_000_000,
      }),
    ).toBeCloseTo(0.1, 10);
  });
});
