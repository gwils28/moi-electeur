import words from "../../../../../prompts/forbidden_words.json";

/**
 * Garde-fou de neutralité en sortie (PLAN § 4.5) : formulations qui classent un candidat,
 * repérées dans la réponse complète. Signalées dans l'événement `done`, jamais réécrites.
 *
 * Même liste que le contrôle CI (scripts/check-forbidden-words.py). Les motifs sont écrits pour
 * Python, dont `\b` et `\w` reconnaissent les lettres accentuées ; en JavaScript ils sont ASCII,
 * d'où leur traduction en classes Unicode.
 */
const WORD = "[\\p{L}\\p{N}_]";

function toUnicode(pattern: string): string {
  // La traduction ne vaut que pour un \b en tête ou en fin de motif (contrainte du fichier).
  if (/.\\b./.test(pattern)) throw new Error("\\b hors des extrémités d'un motif interdit");
  return pattern
    .replace(/^\\b/, `(?<!${WORD})`)
    .replace(/\\b$/, `(?!${WORD})`)
    .replaceAll("\\w", WORD);
}

const PATTERN = new RegExp((words.patterns as string[]).map(toUnicode).join("|"), "giu");

export function findRankingTerms(text: string): string[] {
  const found = new Set<string>();
  // NFC : une réponse en Unicode décomposé (« e » + accent combinant) échapperait aux motifs.
  for (const m of text.normalize("NFC").matchAll(PATTERN))
    found.add(m[0].toLowerCase().replace(/\s+/gu, " "));
  return [...found];
}
