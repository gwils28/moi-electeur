import Anthropic from "@anthropic-ai/sdk";
import { createAskHandler, MAX_TOKENS, type ChatClient, type ModeConfig } from "./ask";
import { DailyBudget } from "./budget";
import { LruCache, type CachedAnswer } from "./cache";
import { consoleLog } from "./log";
import { loadSystemPrompt } from "./prompt";
import { RateLimiter } from "./rate-limit";
import { createRetriever } from "./retrieve";
import { secureRandom } from "./rng";

/** Modèle du chat (SPEC § 2) ; tout modèle doit figurer dans la table de tarifs (pricing.ts). */
export const DEFAULT_CHAT_MODEL = "claude-haiku-5-5";

function usdFromEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  const v = Number(raw);
  // Valeur illisible : 0, donc chat (ou mode) coupé (choix conservateur).
  return Number.isFinite(v) && v >= 0 ? v : 0;
}

const DAILY_BUDGET_USD = usdFromEnv("DAILY_BUDGET_USD", 1);

/**
 * Mode approfondi (CHAT_MODEL_BOOST, ex. claude-sonnet-5-5) : proposé seulement si la variable est
 * renseignée. Environ 20 fois le coût du mode rapide, d'où un plafond quotidien propre
 * (DAILY_BUDGET_BOOST_USD, défaut : la moitié du plafond commun) et une limite de 3 questions
 * par 10 minutes, en plus des plafonds communs : le mode rapide n'est jamais privé de budget.
 */
function boostMode(): ModeConfig | null {
  const model = process.env.CHAT_MODEL_BOOST;
  if (!model) return null;
  return {
    model,
    maxTokens: 8192,
    effort: "medium",
    thinking: true,
    budget: new DailyBudget({
      limitUsd: Math.min(
        usdFromEnv("DAILY_BUDGET_BOOST_USD", DAILY_BUDGET_USD / 2),
        DAILY_BUDGET_USD,
      ),
    }),
    limiter: new RateLimiter({ limit: 3, windowMs: 10 * 60_000 }),
  };
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
  budget: new DailyBudget({ limitUsd: DAILY_BUDGET_USD }),
  cache: new LruCache<CachedAnswer>({ max: 500, ttlMs: 24 * 3600_000 }),
  prompt: loadSystemPrompt(),
  modes: {
    rapide: {
      model: process.env.CHAT_MODEL || DEFAULT_CHAT_MODEL,
      maxTokens: MAX_TOKENS,
      effort: "low",
      thinking: false,
      budget: null,
      limiter: null,
    },
    approfondi: boostMode(),
  },
  log: consoleLog,
  // Tirage cryptographique : l'ordre des candidats n'est pas prévisible.
  rng: secureRandom,
  now: Date.now,
});
