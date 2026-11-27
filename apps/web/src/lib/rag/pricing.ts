/**
 * Tarifs des modèles du chat, en dollars par million de tokens (SPEC § 10). Table versionnée :
 * la mettre à jour (et `PRICING_VERSION`) à chaque changement de tarif publié par Anthropic.
 * Un modèle absent de la table est refusé : sans tarif, le plafond budgétaire est invérifiable.
 */
export const PRICING_VERSION = "2026-11";

export interface ModelPrice {
  /** Entrée et sortie, $ / M tokens. */
  readonly input: number;
  readonly output: number;
  /** Au-delà de ce nombre de tokens d'entrée (cache compris), tarif long contexte. */
  readonly longContextThreshold?: number;
  readonly longInput?: number;
  readonly longOutput?: number;
  /** Lecture du cache en $ / M tokens, quand le tarif publié n'est pas 0,1 x l'entrée. */
  readonly cacheRead?: number;
}

/** Écriture en cache : 1,25 × l'entrée ; lecture : 0,1 × l'entrée (cache de 5 minutes). */
const CACHE_WRITE = 1.25;
const CACHE_READ = 0.1;

export const PRICES: Readonly<Record<string, ModelPrice>> = {
  "claude-haiku-5-5": {
    input: 0.1,
    output: 0.5,
    longContextThreshold: 100_000,
    longInput: 0.5,
    longOutput: 2.5,
  },
  "claude-sonnet-5-5": { input: 2, output: 10, cacheRead: 0.1 },
};

export class UnknownModelError extends Error {
  constructor() {
    super("modèle sans tarif connu");
    this.name = "UnknownModelError";
  }
}

export interface TokenUsage {
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly cache_creation_input_tokens?: number | null;
  readonly cache_read_input_tokens?: number | null;
}

export function priceOf(model: string): ModelPrice {
  const price = PRICES[model];
  if (!price) throw new UnknownModelError();
  return price;
}

export function costUsd(model: string, usage: TokenUsage): number {
  const p = priceOf(model);
  const write = usage.cache_creation_input_tokens ?? 0;
  const read = usage.cache_read_input_tokens ?? 0;
  const totalIn = usage.input_tokens + write + read;
  const long = p.longContextThreshold !== undefined && totalIn > p.longContextThreshold;
  const input = long ? p.longInput! : p.input;
  const output = long ? p.longOutput! : p.output;
  return (
    (usage.input_tokens * input +
      write * input * CACHE_WRITE +
      read * (p.cacheRead ?? input * CACHE_READ) +
      usage.output_tokens * output) /
    1_000_000
  );
}
