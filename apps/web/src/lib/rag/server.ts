import Anthropic from "@anthropic-ai/sdk";
import { createAskHandler, type ChatClient } from "./ask";
import { DailyBudget } from "./budget";
import { LruCache, type CachedAnswer } from "./cache";
import { consoleLog } from "./log";
import { loadSystemPrompt } from "./prompt";
import { RateLimiter } from "./rate-limit";
import { createRetriever } from "./retrieve";
import { secureRandom } from "./rng";

/** Modèle du chat (SPEC § 2) ; tout modèle doit figurer dans la table de tarifs (pricing.ts). */
export const DEFAULT_CHAT_MODEL = "claude-haiku-5-5";

function budgetFromEnv(): number {
  const v = Number(process.env.DAILY_BUDGET_USD ?? "1");
  // Valeur absente ou illisible : 0, donc chat coupé (choix conservateur).
  return Number.isFinite(v) && v >= 0 ? v : 0;
}

let client: ChatClient | null | undefined;

/**
 * Câblage de production, état partagé par le processus (compteurs et cache en mémoire). La clé
 * API n'est lue que côté serveur ; sans clé, le chat répond « indisponible ».
 */
export const askHandler = createAskHandler({
  client: () => {
    if (client === undefined) {
      client = process.env.ANTHROPIC_API_KEY
        ? new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY, timeout: 60_000, maxRetries: 2 })
        : null;
    }
    return client;
  },
  retrieve: createRetriever(process.env.RAG_URL ?? "http://127.0.0.1:8000"),
  limiter: new RateLimiter({ limit: 10, windowMs: 10 * 60_000 }),
  budget: new DailyBudget({ limitUsd: budgetFromEnv() }),
  cache: new LruCache<CachedAnswer>({ max: 500, ttlMs: 24 * 3600_000 }),
  prompt: loadSystemPrompt(),
  model: process.env.CHAT_MODEL ?? DEFAULT_CHAT_MODEL,
  log: consoleLog,
  // Tirage cryptographique : l'ordre des candidats n'est pas prévisible.
  rng: secureRandom,
  now: Date.now,
});
