import type { AskEvent, AskRequest } from "@moi-electeur/schemas-ts";
import { readSse } from "./sse";

/** Refus de /api/ask avant le flux (400, 429, 503...) : code et message fixes du serveur. */
export class AskHttpError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "AskHttpError";
  }
}

type FetchLike = (url: string, init: RequestInit) => Promise<Response>;

/**
 * Pose une question à /api/ask et relaie les événements du flux. La question part au serveur
 * (seule donnée envoyée, jamais journalisée) ; l'historique est conservé par l'appelant, en mémoire.
 */
export async function* askStream(
  body: AskRequest,
  opts: { signal?: AbortSignal; fetchImpl?: FetchLike } = {},
): AsyncGenerator<AskEvent> {
  const fetchImpl = opts.fetchImpl ?? ((url, init) => fetch(url, init));
  const res = await fetchImpl("/api/ask", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    ...(opts.signal ? { signal: opts.signal } : {}),
  });
  if (!res.ok || !res.body) {
    let code = "network";
    let message = "";
    try {
      const err = (await res.json()) as { error?: unknown; message?: unknown };
      if (typeof err.error === "string") code = err.error;
      if (typeof err.message === "string") message = err.message;
    } catch {
      // corps non JSON (proxy, page d'erreur) : code générique
    }
    throw new AskHttpError(res.status, code, message);
  }
  yield* readSse(res.body);
}
