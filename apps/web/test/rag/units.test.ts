// Briques de /api/ask : cache LRU, tarifs, citations, neutralité, prompt, limite de débit.
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { currentSection } from "../../src/lib/rag/ask";
import { DailyBudget } from "../../src/lib/rag/budget";
import { consoleLog } from "../../src/lib/rag/log";
import { secureRandom } from "../../src/lib/rag/rng";
import { cacheKey, LruCache } from "../../src/lib/rag/cache";
import { normalizeSpaces, verifyCitation } from "../../src/lib/rag/citations";
import { findRankingTerms } from "../../src/lib/rag/neutrality";
import { costUsd, PRICES, PRICING_VERSION, UnknownModelError } from "../../src/lib/rag/pricing";
import { loadSystemPrompt } from "../../src/lib/rag/prompt";
import { RateLimiter } from "../../src/lib/rag/rate-limit";
import { encodeEvent } from "../../src/lib/rag/sse";
import { ALICE_TEXT, BRUNO_TEXT, chunk } from "./helpers";

describe("LruCache", () => {
  it("expire après le TTL et évince le moins récemment lu", () => {
    const clock = { t: 0 };
    const c = new LruCache<number>({ max: 2, ttlMs: 1000, now: () => clock.t });
    c.set("a", 1);
    c.set("b", 2);
    expect(c.get("a")).toBe(1); // « a » devient le plus récent
    c.set("c", 3);
    expect(c.get("b")).toBeUndefined();
    expect(c.get("a")).toBe(1);
    clock.t = 1001;
    expect(c.get("a")).toBeUndefined();
    expect(c.size()).toBeLessThanOrEqual(1);
  });

  it("clé : question normalisée, filtres triés, modèle, corpus, prompt", () => {
    const base = {
      election_id: "e",
      question: "Retraite à  60 ans ?",
      candidate_ids: ["b", "a"],
      theme: null,
      model: "m",
      corpus_version: "v",
      prompt_version: "1",
    };
    const k = cacheKey(base);
    expect(k).toMatch(/^[0-9a-f]{64}$/);
    expect(cacheKey({ ...base, question: " retraite à 60 ANS ? " })).toBe(k);
    expect(cacheKey({ ...base, candidate_ids: ["a", "b"] })).toBe(k);
    for (const change of [
      { question: "Retraite à 62 ans ?" },
      { candidate_ids: ["a"] },
      { candidate_ids: null },
      { theme: "social" },
      { model: "m2" },
      { corpus_version: "w" },
      { prompt_version: "2" },
      { election_id: "f" },
    ]) {
      expect(cacheKey({ ...base, ...change })).not.toBe(k);
    }
  });
});

describe("tarifs", () => {
  it("table versionnée, Haiku 5.5 présent", () => {
    expect(PRICING_VERSION).toMatch(/^\d{4}-\d{2}/);
    expect(PRICES["claude-haiku-5-5"]).toBeDefined();
  });

  it("coût Haiku 5.5 calculé à la main, cache compris", () => {
    const usage = {
      input_tokens: 10_000,
      output_tokens: 2_000,
      cache_creation_input_tokens: 1_000,
      cache_read_input_tokens: 4_000,
    };
    // 10 000 × 0,10 + 1 000 × 0,125 + 4 000 × 0,01 + 2 000 × 0,50, en $ par million
    expect(costUsd("claude-haiku-5-5", usage)).toBeCloseTo(0.002165, 12);
  });

  it("au-delà de 100 000 tokens d'entrée, tarif long contexte d'Haiku 5.5", () => {
    const usage = { input_tokens: 150_000, output_tokens: 1_000 };
    // 150 000 × 0,50 + 1 000 × 2,50
    expect(costUsd("claude-haiku-5-5", usage)).toBeCloseTo(0.0775, 12);
  });

  it("modèle inconnu : erreur explicite", () => {
    expect(() => costUsd("claude-inconnu", { input_tokens: 1, output_tokens: 1 })).toThrow(
      UnknownModelError,
    );
  });
});

describe("post-validation des citations", () => {
  const docs = [chunk("alice", 0, ALICE_TEXT, 4), chunk("bruno", 0, BRUNO_TEXT, 7)];

  it("sous-chaîne exacte ou à espaces près : vérifiée, métadonnées de l'extrait", () => {
    expect(
      verifyCitation({ document_index: 1, cited_text: "porté à 65 ans, progressivement" }, docs),
    ).toMatchObject({
      verified: true,
      chunk_id: docs[1]!.id,
      candidate_id: "bruno",
      page_number: 7,
      source_url: "https://example.org/bruno.pdf",
    });
  });

  it("texte absent de l'extrait cité (même s'il est dans un autre) : non vérifiée", () => {
    expect(verifyCitation({ document_index: 1, cited_text: "60 ans" }, docs).verified).toBe(false);
  });

  it("index de document hors bornes : non vérifiée, sans métadonnée", () => {
    expect(verifyCitation({ document_index: 5, cited_text: "x" }, docs)).toMatchObject({
      verified: false,
      chunk_id: null,
      page_number: null,
    });
  });

  it("citation vide : non vérifiée", () => {
    expect(verifyCitation({ document_index: 0, cited_text: "  " }, docs).verified).toBe(false);
  });

  it("normalisation : espaces Unicode et retours à la ligne", () => {
    expect(normalizeSpaces("a  b\n\tc ")).toBe("a b c");
  });
});

describe("garde-fou de neutralité", () => {
  it("même liste que le contrôle CI (prompts/forbidden_words.json)", () => {
    const words = JSON.parse(
      readFileSync(join(import.meta.dirname, "../../../../prompts/forbidden_words.json"), "utf-8"),
    );
    expect(words.patterns.length).toBeGreaterThan(5);
  });

  it.each([
    ["Le meilleur programme", ["meilleur"]],
    ["Nous recommandons ceci", ["recommandons"]],
    ["Le plus crédible des deux", ["plus crédible"]],
    ["Votez pour lui", ["votez"]],
    ["Favoriser l'emploi dans l'empire", []],
    ["L'inspiré, l'émeilleur", []],
    ["Aucune proposition recensée dans le programme officiel sur ce point.", []],
  ])("%s", (text, expected) => {
    expect(findRankingTerms(text)).toEqual(expected);
  });

  it("occurrences multiples dédoublonnées, en minuscules", () => {
    expect(findRankingTerms("MEILLEUR, meilleur, pire")).toEqual(["meilleur", "pire"]);
  });
});

describe("prompt système", () => {
  it("prompts/rag_system.md versionné et non vide", () => {
    const p = loadSystemPrompt();
    expect(p.version).toMatch(/^\d+$/);
    expect(p.text).toContain(
      "Aucune proposition recensée dans le programme officiel sur ce point.",
    );
    expect(p.text).not.toMatch(/^---/);
  });

  it("en-tête `version:` obligatoire", () => {
    const dir = mkdtempSync(join(tmpdir(), "prompt-"));
    writeFileSync(join(dir, "p.md"), "Sans en-tête\n");
    expect(() => loadSystemPrompt(join(dir, "p.md"))).toThrow(/version/);
  });
});

describe("RateLimiter", () => {
  it("purge les entrées expirées", () => {
    const clock = { t: 0 };
    const l = new RateLimiter({ limit: 2, windowMs: 1000, now: () => clock.t });
    expect(l.hit("a").ok).toBe(true);
    expect(l.hit("a").ok).toBe(true);
    const third = l.hit("a");
    expect(third.ok).toBe(false);
    expect(third.retryAfterS).toBe(1);
    clock.t = 2000;
    l.hit("b");
    expect(l.keys()).toHaveLength(1);
  });
});

describe("SSE", () => {
  it("event = type, data = JSON sur une ligne", () => {
    expect(encodeEvent({ type: "delta", block: 0, text: "a\nb" })).toBe(
      'event: delta\ndata: {"type":"delta","block":0,"text":"a\\nb"}\n\n',
    );
  });
});

describe("suites de la relecture (briques)", () => {
  it("tirage de production : réels de [0, 1), variés", () => {
    const xs = Array.from({ length: 200 }, secureRandom);
    expect(xs.every((x) => x >= 0 && x < 1)).toBe(true);
    expect(new Set(xs).size).toBeGreaterThan(190);
  });

  it("réservations simultanées : leur somme ne dépasse jamais le plafond", () => {
    const b = new DailyBudget({ limitUsd: 1, now: () => 0 });
    const first = b.reserve(0.6);
    expect(first).not.toBeNull();
    expect(b.reserve(0.6)).toBeNull();
    first!(0.1);
    expect(b.spent()).toBeCloseTo(0.1);
    expect(b.reserve(0.6)).not.toBeNull();
  });

  it("requête à cheval sur minuit UTC : dépense imputée au nouveau jour", () => {
    const clock = { t: Date.UTC(2026, 10, 27, 23, 59) };
    const b = new DailyBudget({ limitUsd: 1, now: () => clock.t });
    const settle = b.reserve(0.5)!;
    clock.t = Date.UTC(2026, 10, 28, 0, 1);
    settle(0.2);
    expect(b.spent()).toBeCloseTo(0.2);
    expect(b.reserve(0.8)).not.toBeNull();
    expect(b.reserve(0.01)).toBeNull();
  });

  it("limite de débit : nombre de clés borné", () => {
    const l = new RateLimiter({ limit: 10, windowMs: 60_000, now: () => 0, maxKeys: 3 });
    for (const ip of ["a", "b", "c", "d", "e"]) l.hit(ip);
    expect(l.keys()).toHaveLength(3);
  });

  it("neutralité : texte en Unicode décomposé (NFD) repéré", () => {
    expect(findRankingTerms("le plus crédible")).toEqual(["plus crédible"]);
  });

  it("motifs interdits : \\b seulement aux extrémités (condition de la traduction Unicode)", () => {
    const words = JSON.parse(
      readFileSync(join(import.meta.dirname, "../../../../prompts/forbidden_words.json"), "utf-8"),
    ) as { patterns: string[] };
    for (const p of words.patterns) expect(p.slice(2, -2)).not.toContain("\\b");
  });

  it("section en cours : dernier titre ### {{cN}}", () => {
    const map = new Map([
      ["c1", "alice"],
      ["c2", "bruno"],
    ]);
    expect(currentSection("intro", map)).toBeNull();
    expect(currentSection("### {{c1}}\n\ntexte\n\n### {{c2}}\n\n", map)).toBe("bruno");
    expect(currentSection("### {{c9}}\n", map)).toBeNull();
  });

  it("journal console : une ligne JSON aux seuls champs autorisés", () => {
    const lines: string[] = [];
    const spy = vi.spyOn(console, "info").mockImplementation((l: string) => void lines.push(l));
    consoleLog({
      ts: "t",
      model: "m",
      tokens_in: 1,
      tokens_out: 1,
      cost_usd: 0,
      latency_ms: 1,
      status: 200,
      cache_hit: false,
      neutrality_flags: 0,
      unverified_citations: 0,
    });
    spy.mockRestore();
    expect(lines).toHaveLength(1);
    expect(Object.keys(JSON.parse(lines[0]!)).sort()).toEqual(
      [
        "event",
        "ts",
        "model",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "latency_ms",
        "status",
        "cache_hit",
        "neutrality_flags",
        "unverified_citations",
      ].sort(),
    );
  });
});
