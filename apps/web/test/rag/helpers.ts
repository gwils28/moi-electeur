// Doublures de test de /api/ask : client Claude simulé (aucun appel réel) et /retrieve simulé.
import type Anthropic from "@anthropic-ai/sdk";
import type { AskEvent, Chunk, RetrieveResponse } from "@moi-electeur/schemas-ts";
import { createAskHandler, type AskDeps, type ChatClient } from "../../src/lib/rag/ask";
import { DailyBudget } from "../../src/lib/rag/budget";
import { LruCache, type CachedAnswer } from "../../src/lib/rag/cache";
import { RateLimiter } from "../../src/lib/rag/rate-limit";
import type { AskLogRecord } from "../../src/lib/rag/log";
import { RetrieveError } from "../../src/lib/rag/retrieve";

export const QUESTION = "Quelle est votre position secrète sur la retraite à 60 ans ?";
export const ELECTION = "test-2022";
export const CORPUS_VERSION = "0123456789abcdef";

export function chunk(candidate: string, n: number, text: string, page = n + 1): Chunk {
  return {
    id: `${candidate
      .padEnd(12, "0")
      .slice(0, 12)
      .replace(/[^0-9a-f]/g, "a")}-${String(n).padStart(4, "0")}`,
    election_id: ELECTION,
    candidate_id: candidate,
    document_title: "Programme",
    source_url: `https://example.org/${candidate}.pdf`,
    document_sha256: "0".repeat(64),
    page_number: page,
    page_end: page,
    section_title: null,
    theme: null,
    text,
    token_count: 10,
    corpus_version: CORPUS_VERSION,
  };
}

export const ALICE_TEXT = "Nous ramènerons l'âge légal de départ à la retraite à 60 ans.";
export const BRUNO_TEXT = "L'âge de départ sera porté à 65 ans,\nprogressivement.";

export function retrieveResponse(overrides: Partial<RetrieveResponse> = {}): RetrieveResponse {
  const rc = (c: Chunk) => ({ chunk: c, score: 0.03, semantic_rank: 1, lexical_rank: 1 });
  return {
    election_id: ELECTION,
    corpus_version: CORPUS_VERSION,
    model: "bge-m3",
    candidates: [
      { candidate_id: "alice", chunks: [rc(chunk("alice", 0, ALICE_TEXT, 4))] },
      { candidate_id: "bruno", chunks: [rc(chunk("bruno", 0, BRUNO_TEXT, 7))] },
      { candidate_id: "david", chunks: [] },
    ],
    ...overrides,
  };
}

export interface ScriptedBlock {
  text: string;
  /** Bloc de réflexion (thinking) au lieu d'un bloc de texte : `text` est alors la réflexion. */
  thinking?: boolean;
  citations?: Array<{ document_index: number; cited_text: string }>;
}

export interface Script {
  blocks: ScriptedBlock[];
  stop_reason?: Anthropic.StopReason;
  usage?: { input_tokens: number; output_tokens: number };
  /** Lève cette erreur après le premier bloc (coupure en cours de flux). */
  failAfterFirstBlock?: Error;
  /** Lève cette erreur avant `message_start` (erreur HTTP de l'API, rien de généré). */
  failAtStart?: Error;
}

/** Client Claude simulé : rejoue un script d'événements et garde les paramètres reçus. */
export class FakeClaude implements ChatClient {
  calls: Anthropic.MessageStreamParams[] = [];
  signals: (AbortSignal | undefined)[] = [];
  constructor(public script: Script) {}

  messages = {
    stream: (params: Anthropic.MessageStreamParams, options?: { signal?: AbortSignal }) => {
      this.calls.push(params);
      this.signals.push(options?.signal);
      const script = this.script;
      const usage = script.usage ?? { input_tokens: 10_000, output_tokens: 1_000 };
      const content = script.blocks.map((b) =>
        b.thinking
          ? { type: "thinking" as const, thinking: b.text, signature: "sig" }
          : {
              type: "text" as const,
              text: b.text,
              citations: (b.citations ?? []).map((c) =>
                charLocation(c.document_index, c.cited_text),
              ),
            },
      );
      const message = {
        id: "msg_test",
        type: "message",
        role: "assistant",
        model: params.model,
        content,
        stop_reason: script.stop_reason ?? "end_turn",
        stop_sequence: null,
        stop_details: null,
        usage: fullUsage(usage),
      } as unknown as Anthropic.Message;
      async function* events(): AsyncGenerator<Anthropic.MessageStreamEvent> {
        if (script.failAtStart) throw script.failAtStart;
        yield { type: "message_start", message: { ...message, content: [] } } as never;
        for (const [index, block] of script.blocks.entries()) {
          if (index === 1 && script.failAfterFirstBlock) throw script.failAfterFirstBlock;
          if (block.thinking) {
            yield {
              type: "content_block_start",
              index,
              content_block: { type: "thinking", thinking: "", signature: "" },
            } as never;
            yield {
              type: "content_block_delta",
              index,
              delta: { type: "thinking_delta", thinking: block.text },
            } as never;
            yield {
              type: "content_block_delta",
              index,
              delta: { type: "signature_delta", signature: "sig" },
            } as never;
            yield { type: "content_block_stop", index } as never;
            continue;
          }
          yield {
            type: "content_block_start",
            index,
            content_block: { type: "text", text: "", citations: null },
          } as never;
          for (const c of block.citations ?? []) {
            yield {
              type: "content_block_delta",
              index,
              delta: {
                type: "citations_delta",
                citation: charLocation(c.document_index, c.cited_text),
              },
            } as never;
          }
          // Texte découpé en deux deltas pour vérifier le relais incrémental.
          const half = Math.ceil(block.text.length / 2);
          for (const part of [block.text.slice(0, half), block.text.slice(half)]) {
            if (part)
              yield {
                type: "content_block_delta",
                index,
                delta: { type: "text_delta", text: part },
              } as never;
          }
          yield { type: "content_block_stop", index } as never;
        }
        yield {
          type: "message_delta",
          delta: { stop_reason: message.stop_reason, stop_sequence: null },
          usage: { output_tokens: usage.output_tokens },
        } as never;
        yield { type: "message_stop" } as never;
      }
      const iterator = events();
      let consumed: Promise<void> | null = null;
      return {
        [Symbol.asyncIterator]: () => iterator,
        finalMessage: async () => {
          if (!consumed)
            consumed = (async () => {
              for await (const _ of iterator) {
                /* vide */
              }
            })();
          await consumed;
          return message;
        },
      };
    },
  };
}

function charLocation(document_index: number, cited_text: string) {
  return {
    type: "char_location" as const,
    cited_text,
    document_index,
    document_title: null,
    start_char_index: 0,
    end_char_index: cited_text.length,
    file_id: null,
  };
}

function fullUsage(u: { input_tokens: number; output_tokens: number }) {
  return {
    ...u,
    cache_creation: null,
    cache_creation_input_tokens: 0,
    cache_read_input_tokens: 0,
    inference_geo: null,
    output_tokens_details: null,
    server_tool_use: null,
    service_tier: "standard",
    speed: "standard",
  };
}

export const DEFAULT_SCRIPT: Script = {
  blocks: [
    { text: "### {{c1}}\n\n" },
    {
      text: "Le programme prévoit un départ à 60 ans.",
      citations: [{ document_index: 0, cited_text: "départ à la retraite à 60 ans" }],
    },
    {
      text: "\n\n### {{c2}}\n\nAucune proposition recensée dans le programme officiel sur ce point.\n",
    },
  ],
};

export interface Harness {
  handler: (req: Request) => Promise<Response>;
  claude: FakeClaude;
  logs: AskLogRecord[];
  retrieveCalls: unknown[];
  clock: { t: number };
  budget: DailyBudget;
  cache: LruCache<CachedAnswer>;
  limiter: RateLimiter;
  /** Plafond et limite propres au mode approfondi (null s'il n'est pas configuré). */
  boostBudget: DailyBudget | null;
  boostLimiter: RateLimiter | null;
}

export const BOOST_MODEL = "claude-sonnet-5-5";

export function harness(
  opts: {
    script?: Script;
    retrieve?: (body: unknown) => Promise<RetrieveResponse>;
    budgetUsd?: number;
    noClient?: boolean;
    model?: string;
    rng?: () => number;
    /** Mode approfondi : false = non configuré ; défaut : Sonnet, 0,5 $ par jour, 3 par 10 min. */
    boost?: false | { model?: string; budgetUsd?: number; limit?: number };
  } = {},
): Harness {
  const clock = { t: Date.UTC(2026, 10, 27, 12, 0, 0) };
  const now = () => clock.t;
  const claude = new FakeClaude(opts.script ?? DEFAULT_SCRIPT);
  const logs: AskLogRecord[] = [];
  const retrieveCalls: unknown[] = [];
  const budget = new DailyBudget({ limitUsd: opts.budgetUsd ?? 1, now });
  const cache = new LruCache<CachedAnswer>({ max: 500, ttlMs: 24 * 3600_000, now });
  const limiter = new RateLimiter({ limit: 10, windowMs: 10 * 60_000, now });
  const boostOpts = opts.boost === false ? null : (opts.boost ?? {});
  const boostBudget = boostOpts
    ? new DailyBudget({ limitUsd: boostOpts.budgetUsd ?? 0.5, now })
    : null;
  const boostLimiter = boostOpts
    ? new RateLimiter({ limit: boostOpts.limit ?? 3, windowMs: 10 * 60_000, now })
    : null;
  let seed = 0.123;
  const deps: AskDeps = {
    client: () => (opts.noClient ? null : claude),
    retrieve: async (body) => {
      retrieveCalls.push(body);
      return (opts.retrieve ?? (async () => retrieveResponse()))(body);
    },
    limiter,
    budget,
    cache,
    prompt: { version: "1", text: "Consignes de test." },
    modes: {
      rapide: {
        model: opts.model ?? "claude-haiku-5-5",
        maxTokens: 4096,
        effort: "low",
        thinking: false,
        budget: null,
        limiter: null,
      },
      approfondi: boostOpts
        ? {
            model: boostOpts.model ?? BOOST_MODEL,
            maxTokens: 8192,
            effort: "medium",
            thinking: true,
            budget: boostBudget,
            limiter: boostLimiter,
          }
        : null,
    },
    log: (r) => logs.push(r),
    rng:
      opts.rng ??
      (() => {
        seed = (seed * 9301 + 0.49297) % 1;
        return seed;
      }),
    now,
  };
  return {
    handler: createAskHandler(deps),
    claude,
    logs,
    retrieveCalls,
    clock,
    budget,
    cache,
    limiter,
    boostBudget,
    boostLimiter,
  };
}

export function ask(body: unknown, ip = "203.0.113.7", signal?: AbortSignal): Request {
  return new Request("http://localhost/api/ask", {
    method: "POST",
    ...(signal ? { signal } : {}),
    headers: { "content-type": "application/json", "x-forwarded-for": ip },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

/** Lit un flux SSE complet et renvoie les événements décodés (vérifie `event:` = `data.type`). */
export async function readEvents(res: Response): Promise<AskEvent[]> {
  const raw = await res.text();
  const events: AskEvent[] = [];
  for (const frame of raw.split("\n\n").filter(Boolean)) {
    const lines = frame.split("\n");
    const name = lines.find((l) => l.startsWith("event: "))?.slice(7);
    const data = lines.find((l) => l.startsWith("data: "))?.slice(6);
    const ev = JSON.parse(data!) as AskEvent;
    if (ev.type !== name) throw new Error(`événement ${name} != ${ev.type}`);
    events.push(ev);
  }
  return events;
}

export const notIndexed = async (): Promise<RetrieveResponse> => {
  throw new RetrieveError(404);
};
