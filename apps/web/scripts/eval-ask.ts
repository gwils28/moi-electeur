/**
 * Banc d'essai du chat (PLAN D38, M4b) : pose les questions du jeu d'évaluation à `ask()`, le
 * même code que /api/ask, sans limiteur ni cache, et enregistre les événements SSE de chaque
 * réponse dans un JSONL (reprise : une réponse déjà enregistrée n'est pas redemandée).
 *
 *   pnpm --filter @moi-electeur/web exec tsx scripts/eval-ask.ts \
 *     --questions ../../eval/sets/questions-2022.jsonl --out ../../eval/runs/<date>/ask.jsonl \
 *     --modes rapide,approfondi --max-usd 15 [--perms 3 --only q01-nucleaire,...] [--dry-run]
 *
 * Coût plafonné par `--max-usd` (plafond de `ask()` lui-même : une requête qui pourrait le
 * dépasser est refusée avant l'appel). Clé API : `ANTHROPIC_API_KEY`, ou `.env` à la racine du
 * dépôt (jamais affichée). Service de recherche : `RAG_URL` (défaut http://127.0.0.1:8010).
 */
import { appendFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import type { AskEvent } from "@moi-electeur/schemas-ts";
import { readSse } from "../src/lib/explorer/sse";
import { createAskHandler, MAX_TOKENS, type AskMode } from "../src/lib/rag/ask";
import { DailyBudget } from "../src/lib/rag/budget";
import { LruCache, type CachedAnswer } from "../src/lib/rag/cache";
import type { AskLogRecord } from "../src/lib/rag/log";
import { loadSystemPrompt } from "../src/lib/rag/prompt";
import { RateLimiter } from "../src/lib/rag/rate-limit";
import { createRetriever } from "../src/lib/rag/retrieve";

const ROOT = resolve(import.meta.dirname, "..", "..", "..");
const MODELS: Record<AskMode, string> = {
  rapide: "claude-haiku-5-5",
  approfondi: "claude-sonnet-5-5",
};

interface Args {
  questions: string;
  out: string;
  election: string;
  modes: AskMode[];
  perms: number;
  only: Set<string> | null;
  maxUsd: number;
  dryRun: boolean;
  k: number | undefined;
}

function parseArgs(argv: string[]): Args {
  const get = (name: string) => {
    const i = argv.indexOf(`--${name}`);
    return i >= 0 ? argv[i + 1] : undefined;
  };
  const modes = (get("modes") ?? "rapide").split(",") as AskMode[];
  for (const m of modes) if (!(m in MODELS)) throw new Error(`mode inconnu : ${m}`);
  const only = get("only");
  return {
    questions: resolve(get("questions") ?? join(ROOT, "eval", "sets", "questions-2022.jsonl")),
    out: resolve(get("out") ?? "ask.jsonl"),
    election: get("election") ?? "fr-presidentielle-2022",
    modes,
    perms: Number(get("perms") ?? "1"),
    only: only ? new Set(only.split(",")) : null,
    maxUsd: Number(get("max-usd") ?? "5"),
    dryRun: argv.includes("--dry-run"),
    k: get("k") ? Number(get("k")) : undefined,
  };
}

/** Clé lue dans l'environnement ou dans `.env` à la racine ; jamais affichée. */
function apiKey(): string | null {
  if (process.env.ANTHROPIC_API_KEY) return process.env.ANTHROPIC_API_KEY;
  const path = join(ROOT, ".env");
  if (!existsSync(path)) return null;
  for (const line of readFileSync(path, "utf-8").split("\n")) {
    const [key, ...rest] = line.trim().split("=");
    if (key?.trim() === "ANTHROPIC_API_KEY") {
      const value = rest
        .join("=")
        .trim()
        .replace(/^["']|["']$/g, "");
      if (value) return value;
    }
  }
  return null;
}

/** Générateur déterministe (mulberry32) : même ordre des candidats d'un lancement à l'autre. */
function seededRng(text: string): () => number {
  let h = 2166136261;
  for (const ch of text) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  let a = h >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface RunRecord {
  question_id: string;
  mode: AskMode;
  perm: number;
  status: number;
  error: unknown;
  events: AskEvent[];
  log: AskLogRecord | null;
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const questions = readFileSync(args.questions, "utf-8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l) as { id: string; question: string })
    .filter((q) => !args.only || args.only.has(q.id));
  const done = new Set<string>();
  if (existsSync(args.out)) {
    for (const line of readFileSync(args.out, "utf-8")
      .split("\n")
      .filter((l) => l.trim())) {
      const r = JSON.parse(line) as RunRecord;
      if (r.status === 200) done.add(`${r.question_id}|${r.mode}|${r.perm}`);
    }
  }
  const todo = questions.flatMap((q) =>
    args.modes.flatMap((mode) =>
      Array.from({ length: args.perms }, (_, perm) => ({ q, mode, perm })),
    ),
  );
  const pending = todo.filter((t) => !done.has(`${t.q.id}|${t.mode}|${t.perm}`));
  console.log(`${todo.length} réponses prévues, ${pending.length} à demander.`);
  if (args.dryRun || pending.length === 0) return;

  const key = apiKey();
  if (!key) throw new Error("ANTHROPIC_API_KEY absente (environnement ou .env à la racine)");
  const client = new Anthropic({ apiKey: key, timeout: 120_000, maxRetries: 3 });
  const budget = new DailyBudget({ limitUsd: args.maxUsd });
  const retrieve = createRetriever(process.env.RAG_URL ?? "http://127.0.0.1:8010");
  const prompt = loadSystemPrompt();
  mkdirSync(dirname(args.out), { recursive: true });

  for (const [n, { q, mode, perm }] of pending.entries()) {
    let log: AskLogRecord | null = null;
    const handler = createAskHandler({
      client: () => client,
      retrieve,
      limiter: new RateLimiter({ limit: 1_000_000, windowMs: 60_000 }),
      budget,
      // Cache neuf à chaque requête : sa clé ignore l'ordre des candidats (permutations).
      cache: new LruCache<CachedAnswer>({ max: 1, ttlMs: 1 }),
      prompt,
      modes: {
        rapide: {
          model: MODELS.rapide,
          maxTokens: MAX_TOKENS,
          effort: "low",
          thinking: "adaptive",
          budget: null,
          limiter: null,
        },
        approfondi: {
          model: MODELS.approfondi,
          maxTokens: MAX_TOKENS,
          effort: "medium",
          thinking: "adaptive",
          budget: null,
          limiter: null,
        },
      },
      log: (r) => {
        log = r;
      },
      rng: seededRng(`${q.id}|${perm}`),
      ...(args.k === undefined ? {} : { k: args.k }),
      now: Date.now,
    });
    const res = await handler(
      new Request("http://eval.local/api/ask", {
        method: "POST",
        headers: { "content-type": "application/json", "x-forwarded-for": "127.0.0.1" },
        body: JSON.stringify({ election_id: args.election, question: q.question, mode }),
      }),
    );
    const events: AskEvent[] = [];
    let error: unknown = null;
    if (res.ok && res.body) {
      for await (const e of readSse(res.body)) events.push(e);
    } else {
      error = await res.json().catch(() => null);
    }
    const record: RunRecord = {
      question_id: q.id,
      mode,
      perm,
      status: res.status,
      error,
      events,
      log,
    };
    appendFileSync(args.out, JSON.stringify(record) + "\n");
    const cost = (log as AskLogRecord | null)?.cost_usd ?? 0;
    console.log(
      `[${n + 1}/${pending.length}] ${q.id} ${mode} #${perm} : ${res.status}, ` +
        `${cost.toFixed(4)} $, cumul ${budget.spent().toFixed(3)} $`,
    );
    if (res.status === 503 && budget.exhausted()) {
      console.log("Plafond atteint : arrêt.");
      break;
    }
  }
  console.log(`Dépense totale : ${budget.spent().toFixed(3)} $`);
}

await main();
