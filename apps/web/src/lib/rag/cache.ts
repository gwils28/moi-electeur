import { createHash } from "node:crypto";
import type { AskEvent } from "@moi-electeur/schemas-ts";

/**
 * Cache des réponses en mémoire uniquement (SPEC § 6.2 bis) : LRU, TTL, jamais écrit sur disque.
 * Vidé au redémarrage ; une réindexation change la version du corpus, donc la clé.
 */
export class LruCache<V> {
  private readonly max: number;
  private readonly ttlMs: number;
  private readonly now: () => number;
  private readonly entries = new Map<string, { value: V; expires: number }>();

  constructor(opts: { max: number; ttlMs: number; now?: () => number }) {
    this.max = opts.max;
    this.ttlMs = opts.ttlMs;
    this.now = opts.now ?? Date.now;
  }

  get(key: string): V | undefined {
    const entry = this.entries.get(key);
    if (!entry) return undefined;
    this.entries.delete(key);
    if (entry.expires <= this.now()) return undefined;
    this.entries.set(key, entry); // devient la plus récente
    return entry.value;
  }

  set(key: string, value: V): void {
    this.entries.delete(key);
    this.entries.set(key, { value, expires: this.now() + this.ttlMs });
    while (this.entries.size > this.max) {
      this.entries.delete(this.entries.keys().next().value!);
    }
  }

  size(): number {
    return this.entries.size;
  }
}

/** Réponse conservée : uniquement les événements du flux, sans IP ni horodatage. */
export interface CachedAnswer {
  readonly events: readonly AskEvent[];
}

export interface CacheKeyParts {
  election_id: string;
  question: string;
  candidate_ids: readonly string[] | null;
  theme: string | null;
  model: string;
  corpus_version: string;
  prompt_version: string;
}

/** Normalisation : Unicode NFC, minuscules, espaces repliés. */
export function normalizeQuestion(q: string): string {
  return q.normalize("NFC").toLowerCase().replace(/\s+/gu, " ").trim();
}

export function cacheKey(p: CacheKeyParts): string {
  const material = JSON.stringify([
    normalizeQuestion(p.question),
    p.election_id,
    p.candidate_ids ? [...p.candidate_ids].sort() : null,
    p.theme,
    p.model,
    p.corpus_version,
    p.prompt_version,
  ]);
  return createHash("sha256").update(material).digest("hex");
}
