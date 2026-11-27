/**
 * Journal du chat (SPEC § 6.3) : un enregistrement par requête, limité à ces champs. Jamais la
 * question, l'historique, les extraits, la réponse, l'IP ni un message d'erreur.
 */
export interface AskLogRecord {
  ts: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  latency_ms: number;
  status: number;
  cache_hit: boolean;
  /** Nombre de formulations de classement repérées (métrique de neutralité). */
  neutrality_flags: number;
  unverified_citations: number;
}

export function consoleLog(record: AskLogRecord): void {
  console.info(JSON.stringify({ event: "ask", ...record }));
}
