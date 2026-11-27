import type { AskRequest } from "@moi-electeur/schemas-ts";
import { Ajv2020 } from "ajv/dist/2020.js";
import schema from "../../../../../schemas/ask_request.schema.json";

const ajv = new Ajv2020({ allErrors: false, strict: true, allowUnionTypes: true });
const validateSchema = ajv.compile<AskRequest>(schema);

const TOKEN = /\{\{c(\d+)\}\}/g;

/**
 * Validation du corps de /api/ask contre schemas/ask_request.schema.json (source unique), plus
 * une règle hors schéma : chaque jeton {{cN}} d'une réponse d'historique désigne un candidat de
 * sa liste. Le motif d'erreur ne reprend jamais la valeur reçue.
 */
export function parseAskRequest(body: unknown): AskRequest | null {
  if (!validateSchema(body)) return null;
  for (const turn of body.history ?? []) {
    for (const m of turn.answer.matchAll(TOKEN)) {
      const n = Number(m[1]);
      if (n < 1 || n > turn.candidates.length) return null;
    }
  }
  return body;
}
