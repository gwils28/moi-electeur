import { readFileSync } from "node:fs";
import { join } from "node:path";
import type Anthropic from "@anthropic-ai/sdk";
import type { AskCandidate, AskTurn, Chunk, RetrieveResponse } from "@moi-electeur/schemas-ts";

export interface SystemPrompt {
  readonly version: string;
  readonly text: string;
}

/** Dossier des prompts : `PROMPTS_DIR`, sinon `prompts/` à la racine du dépôt (cwd = apps/web). */
export function promptsDir(): string {
  return process.env.PROMPTS_DIR ?? join(process.cwd(), "..", "..", "prompts");
}

/** prompts/rag_system.md : en-tête `---\nversion: N\n---` obligatoire (version dans la clé de cache). */
export function loadSystemPrompt(path: string = join(promptsDir(), "rag_system.md")): SystemPrompt {
  // Fichier lu à l'exécution (copié dans l'image), hors du traçage du bundle.
  const raw = readFileSync(/*turbopackIgnore: true*/ path, "utf-8");
  const m = /^---\n(?:.*\n)*?version:\s*(\S+)\s*\n(?:.*\n)*?---\n/.exec(raw);
  if (!m) throw new Error(`${path} : en-tête « version: » manquant`);
  return { version: m[1]!, text: raw.slice(m[0].length).trim() };
}

/** Mélange de Fisher-Yates ; `rng` renvoie un réel de [0, 1). */
export function shuffle<T>(items: readonly T[], rng: () => number): T[] {
  const out = [...items];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.min(i, Math.floor(rng() * (i + 1)));
    [out[i], out[j]] = [out[j]!, out[i]!];
  }
  return out;
}

export const SILENCE = "Aucune proposition recensée dans le programme officiel sur ce point.";
const OUT_OF_SELECTION = "[candidat hors sélection]";

export interface BuiltRequest {
  readonly params: Anthropic.MessageStreamParams;
  /** Extraits dans l'ordre des blocs `document` (`document_index` des citations). */
  readonly documents: readonly Chunk[];
  readonly candidates: readonly AskCandidate[];
}

function pages(c: Chunk): string {
  return c.page_end > c.page_number ? `p. ${c.page_number}-${c.page_end}` : `p. ${c.page_number}`;
}

/** Jetons d'une réponse précédente réécrits selon le tirage courant. */
function remapTurn(turn: AskTurn, tokenOf: ReadonlyMap<string, string>): string {
  return turn.answer.replace(/\{\{c(\d+)\}\}/g, (_m, n: string) => {
    const id = turn.candidates[Number(n) - 1];
    const token = id === undefined ? undefined : tokenOf.get(id);
    return token ? `{{${token}}}` : OUT_OF_SELECTION;
  });
}

/**
 * Requête Claude (SPEC § 6.2) : ordre des candidats tiré au sort par requête, candidats désignés
 * par des jetons {{cN}} (jamais par leur identifiant ni leur nom), un bloc `document` par extrait
 * avec citations natives, historique en texte seul (les extraits ne sont fournis qu'au dernier tour).
 */
export function buildRequest(opts: {
  prompt: SystemPrompt;
  model: string;
  maxTokens: number;
  question: string;
  history: readonly AskTurn[];
  retrieved: RetrieveResponse;
  rng: () => number;
}): BuiltRequest {
  const ordered = shuffle(opts.retrieved.candidates, opts.rng);
  const candidates: AskCandidate[] = ordered.map((c, i) => ({
    token: `c${i + 1}`,
    candidate_id: c.candidate_id,
    has_excerpts: c.chunks.length > 0,
  }));
  const tokenOf = new Map(candidates.map((c) => [c.candidate_id, c.token]));

  const documents: Chunk[] = [];
  const docBlocks: Anthropic.DocumentBlockParam[] = [];
  for (const c of ordered) {
    for (const r of c.chunks) {
      documents.push(r.chunk);
      docBlocks.push({
        type: "document",
        source: { type: "text", media_type: "text/plain", data: r.chunk.text },
        title: `{{${tokenOf.get(c.candidate_id)}}} · ${r.chunk.document_title} · ${pages(r.chunk)}`,
        citations: { enabled: true },
      });
    }
  }

  const order = candidates.map((c) => `{{${c.token}}}`).join(", ");
  const silent = candidates.filter((c) => !c.has_excerpts).map((c) => `{{${c.token}}}`);
  const instructions = [
    `Candidats à traiter, dans cet ordre : ${order}.`,
    silent.length > 0
      ? `Aucun extrait n'est fourni pour ${silent.join(", ")} : leur section contient uniquement « ${SILENCE} »`
      : null,
    "",
    "Question :",
    opts.question,
  ].filter((l) => l !== null);

  const messages: Anthropic.MessageParam[] = [];
  for (const turn of opts.history) {
    messages.push({ role: "user", content: turn.question });
    messages.push({ role: "assistant", content: remapTurn(turn, tokenOf) });
  }
  messages.push({
    role: "user",
    content: [...docBlocks, { type: "text", text: instructions.join("\n") }],
  });

  return {
    params: {
      model: opts.model,
      max_tokens: opts.maxTokens,
      system: opts.prompt.text,
      output_config: { effort: "low" },
      messages,
    },
    documents,
    candidates,
  };
}
