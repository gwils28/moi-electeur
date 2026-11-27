import Anthropic from "@anthropic-ai/sdk";
import type {
  AskCitationEvent,
  AskEvent,
  AskMetaEvent,
  AskRequest,
  RetrieveResponse,
} from "@moi-electeur/schemas-ts";
import type { DailyBudget } from "./budget";
import { cacheKey, type CachedAnswer, type LruCache } from "./cache";
import { verifyCitation } from "./citations";
import type { AskLogRecord } from "./log";
import { findRankingTerms } from "./neutrality";
import { costUsd, UnknownModelError } from "./pricing";
import { buildRequest, type SystemPrompt } from "./prompt";
import { clientIp, type RateLimiter } from "./rate-limit";
import { RetrieveError, type Retriever } from "./retrieve";
import { encodeEvent } from "./sse";
import { parseAskRequest } from "./validate";

/** Extraits gardés par candidat (SPEC § 6.1). */
export const K = 4;
/**
 * Plafond de sortie, réflexion comprise : 1 400 à 4 800 tokens mesurés pour 12 candidats (M2c,
 * M2d). 4 096 tronquait une réponse d'Haiku dont la réflexion consommait environ 2 800 tokens.
 */
export const MAX_TOKENS = 8192;
/** Taille maximale du corps : 500 caractères de question, 3 tours d'historique, filtres. */
export const MAX_BODY_BYTES = 100_000;

/** Sous-ensemble du client Anthropic utilisé (injecté, simulé dans les tests). */
export interface ChatStream extends AsyncIterable<Anthropic.MessageStreamEvent> {
  finalMessage(): Promise<Anthropic.Message>;
}
export interface ChatClient {
  messages: {
    stream(params: Anthropic.MessageStreamParams, options?: { signal?: AbortSignal }): ChatStream;
  };
}

export type AskMode = NonNullable<AskRequest["mode"]>;

/** Réglages d'un mode : modèle, sortie, réflexion, et plafonds propres en plus des communs. */
export interface ModeConfig {
  model: string;
  maxTokens: number;
  effort: "low" | "medium" | "high";
  /** Réflexion du modèle ; adaptative dans les deux modes (désactivée : moins fidèle, M2d). */
  thinking: "adaptive" | "disabled";
  /** Plafond quotidien propre au mode, imputé en plus du plafond commun. */
  budget: DailyBudget | null;
  /** Limite de débit propre au mode, appliquée en plus de la limite commune. */
  limiter: RateLimiter | null;
}

export interface AskDeps {
  /** null si `ANTHROPIC_API_KEY` est absente : le chat est alors indisponible. */
  client: () => ChatClient | null;
  retrieve: Retriever;
  /** Limite de débit et plafond communs à tous les modes. */
  limiter: RateLimiter;
  budget: DailyBudget;
  cache: LruCache<CachedAnswer>;
  prompt: SystemPrompt;
  /** « approfondi » à null : non proposé (CHAT_MODEL_BOOST absent). */
  modes: { rapide: ModeConfig; approfondi: ModeConfig | null };
  log: (record: AskLogRecord) => void;
  /** Tirage de l'ordre des candidats, réel de [0, 1). */
  rng: () => number;
  now: () => number;
}

type ErrorCode =
  | "invalid_request"
  | "payload_too_large"
  | "method_not_allowed"
  | "rate_limited"
  | "budget_exhausted"
  | "mode_rate_limited"
  | "mode_budget_exhausted"
  | "mode_unavailable"
  | "chat_unavailable"
  | "not_indexed"
  | "retrieval_unavailable";

/** Messages d'erreur fixes : jamais d'écho de l'entrée. */
const MESSAGES: Record<ErrorCode, string> = {
  invalid_request: "Requête invalide.",
  payload_too_large: "Requête trop volumineuse.",
  method_not_allowed: "Méthode non autorisée.",
  rate_limited: "Trop de questions en peu de temps : réessayez dans quelques minutes.",
  budget_exhausted:
    "Le chat a atteint son plafond de dépense quotidien. Il sera de nouveau disponible demain.",
  mode_rate_limited:
    "Trop de questions en mode approfondi en peu de temps : le mode rapide reste disponible.",
  mode_budget_exhausted:
    "Le mode approfondi a atteint son plafond quotidien : le mode rapide reste disponible.",
  mode_unavailable: "Le mode approfondi n'est pas disponible : le mode rapide reste disponible.",
  chat_unavailable: "Le chat n'est pas disponible pour le moment.",
  not_indexed: "Cette élection n'est pas disponible dans l'explorateur.",
  retrieval_unavailable: "La recherche dans les programmes est indisponible pour le moment.",
};

const STREAM_HEADERS = {
  "content-type": "text/event-stream; charset=utf-8",
  "cache-control": "no-store, no-transform",
  "x-accel-buffering": "no",
};

/**
 * POST /api/ask (PLAN § 4.5). Chaîne : validation → limite de débit → plafond budgétaire →
 * /retrieve → cache (première question seulement) → Claude en streaming → relais SSE.
 *
 * Écart au plan : /retrieve passe avant le cache, car la clé contient la version du corpus que
 * seul le rag-service connaît (une réindexation invalide ainsi le cache sans redémarrage).
 */
export function createAskHandler(deps: AskDeps): (req: Request) => Promise<Response> {
  return async (req) => {
    const started = deps.now();
    let model = deps.modes.rapide.model;
    const record = (fields: Partial<AskLogRecord> & { status: number }) =>
      deps.log({
        ts: new Date(deps.now()).toISOString(),
        model,
        tokens_in: 0,
        tokens_out: 0,
        cost_usd: 0,
        latency_ms: deps.now() - started,
        cache_hit: false,
        neutrality_flags: 0,
        unverified_citations: 0,
        ...fields,
      });
    const fail = (status: number, code: ErrorCode, headers: Record<string, string> = {}) => {
      record({ status });
      return Response.json(
        { error: code, message: MESSAGES[code] },
        { status, headers: { "cache-control": "no-store", ...headers } },
      );
    };

    if (req.method !== "POST") return fail(405, "method_not_allowed", { allow: "POST" });

    const declared = Number(req.headers.get("content-length") ?? "0");
    if (declared > MAX_BODY_BYTES) return fail(413, "payload_too_large");
    const raw = await readCapped(req, MAX_BODY_BYTES);
    if (raw === null) return fail(413, "payload_too_large");
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      return fail(400, "invalid_request");
    }
    const body = parseAskRequest(parsed);
    if (!body) return fail(400, "invalid_request");

    const limit = deps.limiter.hit(clientIp(req));
    if (!limit.ok) return fail(429, "rate_limited", { "retry-after": String(limit.retryAfterS) });

    const mode: AskMode = body.mode ?? "rapide";
    const cfg = deps.modes[mode];
    if (!cfg || !hasPrice(cfg.model))
      return fail(503, mode === "rapide" ? "chat_unavailable" : "mode_unavailable");
    model = cfg.model;
    if (cfg.limiter) {
      const modeLimit = cfg.limiter.hit(clientIp(req));
      if (!modeLimit.ok)
        return fail(429, "mode_rate_limited", { "retry-after": String(modeLimit.retryAfterS) });
    }

    const client = deps.client();
    if (!client) return fail(503, "chat_unavailable");
    const candidateIds = body.candidate_ids ?? null;
    const theme = body.theme ?? null;
    let retrieved: RetrieveResponse;
    try {
      retrieved = await deps.retrieve({
        election_id: body.election_id,
        question: body.question,
        candidate_ids: candidateIds,
        theme,
        k: K,
      });
    } catch (e) {
      if (e instanceof RetrieveError && e.status === 404) return fail(404, "not_indexed");
      if (e instanceof RetrieveError && e.status === 422) return fail(400, "invalid_request");
      return fail(502, "retrieval_unavailable");
    }

    const history = body.history ?? [];
    const key =
      history.length === 0
        ? cacheKey({
            election_id: body.election_id,
            question: body.question,
            candidate_ids: candidateIds,
            theme,
            model,
            corpus_version: retrieved.corpus_version,
            prompt_version: deps.prompt.version,
          })
        : null;
    const hit = key ? deps.cache.get(key) : undefined;
    if (hit) {
      record({ status: 200, cache_hit: true });
      return replay(hit);
    }
    // Après le cache : une réponse déjà en cache ne coûte rien et reste servie budget épuisé.
    if (deps.budget.exhausted()) return fail(503, "budget_exhausted");
    if (cfg.budget?.exhausted()) return fail(503, "mode_budget_exhausted");

    const built = buildRequest({
      prompt: deps.prompt,
      model,
      maxTokens: cfg.maxTokens,
      effort: cfg.effort,
      thinking: cfg.thinking,
      question: body.question,
      history,
      retrieved,
      rng: deps.rng,
    });
    // Borne supérieure des tokens d'entrée : un token par octet UTF-8 (l'historique est fourni
    // par le client, il peut contenir des écritures non latines ou des émojis).
    const inputBytes = Buffer.byteLength(JSON.stringify(built.params), "utf-8");
    const maxCost = costUsd(model, {
      input_tokens: inputBytes,
      output_tokens: cfg.maxTokens,
    });
    const settleCommon = deps.budget.reserve(maxCost);
    if (!settleCommon) return fail(503, "budget_exhausted");
    const settleMode = cfg.budget ? cfg.budget.reserve(maxCost) : () => {};
    if (!settleMode) {
      settleCommon(0);
      return fail(503, "mode_budget_exhausted");
    }
    const settle = (actualUsd: number | null) => {
      settleCommon(actualUsd);
      settleMode(actualUsd);
    };

    const meta: AskMetaEvent = {
      type: "meta",
      election_id: retrieved.election_id,
      corpus_version: retrieved.corpus_version,
      prompt_version: deps.prompt.version,
      model,
      mode,
      cached: false,
      candidates: [...built.candidates],
    };

    const tokenToCandidate = new Map(built.candidates.map((c) => [c.token, c.candidate_id]));
    const abort = new AbortController();
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      async start(controller) {
        const events: AskEvent[] = [meta];
        const send = (ev: AskEvent) => {
          if (ev !== meta) events.push(ev);
          try {
            controller.enqueue(encoder.encode(encodeEvent(ev)));
          } catch {
            // client parti : le flux est déjà fermé
          }
        };
        send(meta);
        let text = "";
        let unverified = 0;
        let generating = false;
        try {
          const claude = client.messages.stream(built.params, { signal: abort.signal });
          for await (const ev of claude) {
            if (ev.type === "message_start") generating = true;
            if (ev.type !== "content_block_delta") continue;
            if (ev.delta.type === "text_delta") {
              text += ev.delta.text;
              send({ type: "delta", block: ev.index, text: ev.delta.text });
            } else if (ev.delta.type === "citations_delta") {
              const c = ev.delta.citation;
              if (!("document_index" in c)) continue;
              // Section en cours (### {{cN}}) : la citation doit venir d'un extrait de ce candidat.
              const section = currentSection(text, tokenToCandidate);
              const checked = verifyCitation(c, built.documents, section);
              if (!checked.verified) unverified++;
              const citation: AskCitationEvent = { type: "citation", block: ev.index, ...checked };
              send(citation);
            }
          }
          const final = await claude.finalMessage();
          const cost = costUsd(model, final.usage);
          settle(cost);
          const flags = findRankingTerms(text);
          send({
            type: "done",
            stop_reason: final.stop_reason,
            unverified_citations: unverified,
            neutrality_flags: flags,
          });
          if (key && final.stop_reason === "end_turn") deps.cache.set(key, { events: [...events] });
          record({
            status: 200,
            tokens_in:
              final.usage.input_tokens +
              (final.usage.cache_creation_input_tokens ?? 0) +
              (final.usage.cache_read_input_tokens ?? 0),
            tokens_out: final.usage.output_tokens,
            cost_usd: cost,
            neutrality_flags: flags.length,
            unverified_citations: unverified,
          });
        } catch (e) {
          // Erreur de l'API avant toute génération (statut HTTP, pas de `message_start`) : rien
          // n'est facturé. Sinon (coupure en cours, client parti, réseau) le coût réel est
          // inconnu et le coût maximal réservé reste imputé. Aucun message d'erreur n'est
          // journalisé ni transmis (il pourrait contenir la question ou des extraits).
          const unbilled = !generating && e instanceof Anthropic.APIError && e.status !== undefined;
          settle(unbilled ? 0 : null);
          const unavailable = isUnavailable(e);
          send({
            type: "error",
            code: unavailable ? "llm_unavailable" : "llm_error",
            message: unavailable
              ? "Le service de génération est momentanément indisponible."
              : "La génération de la réponse a échoué.",
          });
          record({ status: unavailable ? 503 : 500, cost_usd: unbilled ? 0 : maxCost });
        } finally {
          try {
            controller.close();
          } catch {
            // déjà fermé
          }
        }
      },
      cancel() {
        abort.abort();
      },
    });
    req.signal?.addEventListener("abort", () => abort.abort(), { once: true });
    return new Response(stream, { status: 200, headers: STREAM_HEADERS });
  };
}

function hasPrice(model: string): boolean {
  try {
    costUsd(model, { input_tokens: 0, output_tokens: 0 });
    return true;
  } catch (e) {
    if (e instanceof UnknownModelError) return false;
    throw e;
  }
}

function isUnavailable(e: unknown): boolean {
  if (e instanceof Anthropic.APIConnectionError) return true; // réseau, délai dépassé
  const status = (e as { status?: unknown } | null)?.status;
  return typeof status === "number" && (status === 429 || status === 529 || status >= 500);
}

const SECTION = /^###\s*\{\{(c\d+)\}\}/gm;

/** Candidat de la dernière section `### {{cN}}` ouverte dans le texte déjà reçu, sinon null. */
export function currentSection(
  text: string,
  tokenToCandidate: ReadonlyMap<string, string>,
): string | null {
  let token: string | undefined;
  for (const m of text.matchAll(SECTION)) token = m[1];
  return token === undefined ? null : (tokenToCandidate.get(token) ?? null);
}

/** Lit le corps en s'arrêtant au-delà de `max` octets (null) : jamais tout en mémoire. */
async function readCapped(req: Request, max: number): Promise<string | null> {
  if (!req.body) return "";
  const reader = req.body.getReader();
  const parts: Uint8Array[] = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > max) {
      await reader.cancel();
      return null;
    }
    parts.push(value);
  }
  return Buffer.concat(parts).toString("utf-8");
}

/** Réponse du cache re-streamée (SPEC § 6.2 bis) : mêmes événements, `cached: true`. */
function replay(hit: CachedAnswer): Response {
  const encoder = new TextEncoder();
  const body = hit.events
    .map((ev) => encodeEvent(ev.type === "meta" ? { ...ev, cached: true } : ev))
    .join("");
  return new Response(encoder.encode(body), { status: 200, headers: STREAM_HEADERS });
}
