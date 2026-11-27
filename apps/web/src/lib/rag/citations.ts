import type { AskCitationEvent, Chunk } from "@moi-electeur/schemas-ts";

/** Espaces Unicode (dont insécables) et retours à la ligne repliés en une espace. */
export function normalizeSpaces(s: string): string {
  return s.replace(/\s+/gu, " ").trim();
}

/**
 * Post-validation d'une citation native (SPEC § 6.2) : vérifiée si `cited_text` est une
 * sous-chaîne, à espaces près, de l'extrait désigné par `document_index` (blocs `document` dans
 * l'ordre de `documents`) et, si `sectionCandidate` est donné (section `### {{cN}}` en cours),
 * si cet extrait appartient bien à ce candidat. Sinon « non vérifiée », sans métadonnée si
 * l'index est hors bornes.
 */
export function verifyCitation(
  citation: { document_index: number; cited_text: string },
  documents: readonly Chunk[],
  sectionCandidate: string | null = null,
): Omit<AskCitationEvent, "type" | "block"> {
  const doc = Number.isInteger(citation.document_index)
    ? documents[citation.document_index]
    : undefined;
  const cited = normalizeSpaces(citation.cited_text);
  return {
    verified:
      doc !== undefined &&
      cited.length > 0 &&
      normalizeSpaces(doc.text).includes(cited) &&
      (sectionCandidate === null || doc.candidate_id === sectionCandidate),
    cited_text: citation.cited_text,
    chunk_id: doc?.id ?? null,
    candidate_id: doc?.candidate_id ?? null,
    document_title: doc?.document_title ?? null,
    source_url: doc?.source_url ?? null,
    page_number: doc?.page_number ?? null,
    page_end: doc?.page_end ?? null,
  };
}
