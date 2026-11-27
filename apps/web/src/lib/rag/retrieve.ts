import type { RetrieveRequest, RetrieveResponse } from "@moi-electeur/schemas-ts";

/** Erreur du rag-service : `status` HTTP renvoyé, ou 0 si le service est injoignable. */
export class RetrieveError extends Error {
  constructor(readonly status: number) {
    super(`rag-service : ${status || "injoignable"}`);
    this.name = "RetrieveError";
  }
}

export type Retriever = (body: RetrieveRequest) => Promise<RetrieveResponse>;

/** Appel de POST /retrieve (services/rag, réseau interne). Aucun contenu n'est journalisé. */
export function createRetriever(
  ragUrl: string,
  fetchImpl: typeof fetch = fetch,
  timeoutMs = 30_000,
): Retriever {
  const url = `${ragUrl.replace(/\/+$/, "")}/retrieve`;
  return async (body) => {
    let res: Response;
    try {
      res = await fetchImpl(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(timeoutMs),
      });
    } catch {
      throw new RetrieveError(0);
    }
    if (!res.ok) throw new RetrieveError(res.status);
    const data = (await res.json()) as RetrieveResponse;
    if (!data || !Array.isArray(data.candidates) || typeof data.corpus_version !== "string") {
      throw new RetrieveError(502);
    }
    return data;
  };
}
