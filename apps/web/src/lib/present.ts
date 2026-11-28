import { shuffleCandidates } from "@moi-electeur/engine";
import type { AskCitationEvent, Candidate } from "@moi-electeur/schemas-ts";
import { fr } from "../i18n/fr";

/**
 * Seul point d'accès à l'identité d'un candidat pour l'affichage (mode aveugle, SPEC § 5.5).
 * Les composants n'accèdent jamais directement à `name`, `party`, `color` ou `photo`
 * (règle ESLint dans apps/web/src/components). Aucune couleur ni forme n'est associée à un
 * candidat : nom (ou alias) seulement, pour la neutralité (PLAN D58).
 */
export interface CandidateDisplay {
  readonly id: string;
  readonly label: string;
  readonly party: string | null;
  readonly documentLabel: string;
  /** Mode aveugle : les citations peuvent contenir un nom ou un slogan, elles sont masquées. */
  readonly hideQuotes: boolean;
}

/**
 * `alias` est l'alias attribué au rang de session (voir `displayCandidates`) : il n'est pas lié
 * à l'ordre (public) du fichier de configuration, sinon le mode aveugle serait réversible d'une
 * session à l'autre. `_rank` est conservé pour la stabilité de l'interface.
 */
export function displayCandidate(
  candidate: Candidate,
  _rank: number,
  blind: boolean,
  alias: string = candidate.blind_alias,
): CandidateDisplay {
  if (blind) {
    return {
      id: candidate.id,
      label: alias,
      party: null,
      documentLabel: "Programme",
      hideQuotes: true,
    };
  }
  return {
    id: candidate.id,
    label: candidate.name,
    party: candidate.party,
    documentLabel: `Programme de ${candidate.name}`,
    hideQuotes: false,
  };
}

/**
 * Candidats dans l'ordre aléatoire de session. L'alias suit le rang tiré au sort,
 * pas l'ordre du fichier de configuration.
 */
export function displayCandidates(
  candidates: readonly Candidate[],
  seed: number,
  blind: boolean,
): CandidateDisplay[] {
  const aliases = candidates.map((c) => c.blind_alias);
  return shuffleCandidates(candidates, seed).map((c, rank) =>
    displayCandidate(c, rank, blind, aliases[rank]),
  );
}

/** Citation telle qu'affichée (SPEC § 6.2) : source, page, lien et extrait selon le mode. */
export interface CitationView {
  readonly source: string;
  readonly page: string | null;
  readonly href: string | null;
  /** Extrait cité ; null en mode aveugle (il pourrait contenir un nom ou un slogan). */
  readonly quote: string | null;
  readonly verified: boolean;
}

function safeHref(url: string | null, page: number | null): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    if (u.protocol !== "https:" && u.protocol !== "http:") return null;
    if (page !== null && u.hash === "") u.hash = `page=${page}`;
    return u.toString();
  } catch {
    return null;
  }
}

/**
 * Mode aveugle : ni titre du document, ni lien (le nom de domaine révèle souvent le candidat),
 * ni extrait ; seule la page reste.
 */
export function citationView(
  c: AskCitationEvent,
  display: CandidateDisplay | undefined,
  blind: boolean,
): CitationView {
  const page =
    c.page_number === null
      ? null
      : c.page_end !== null && c.page_end !== c.page_number
        ? `p. ${c.page_number}-${c.page_end}`
        : `p. ${c.page_number}`;
  if (blind || !display || display.hideQuotes) {
    // Candidat inconnu hors mode aveugle : extrait affiché, mais ni titre ni lien non attribués.
    const hidden = blind || display?.hideQuotes === true;
    return {
      source: display?.documentLabel ?? fr.explorer.unknownSource,
      page,
      href: null,
      quote: hidden ? null : c.cited_text,
      verified: c.verified,
    };
  }
  return {
    source: c.document_title ?? display.documentLabel,
    page,
    href: safeHref(c.source_url, c.page_number),
    quote: c.cited_text,
    verified: c.verified,
  };
}

const LETTER = "[\\p{L}\\p{N}_]";

/**
 * Mode aveugle : remplace dans un texte généré le nom complet et le nom de famille de chaque
 * candidat par son libellé affiché (le modèle ne reçoit que des jetons, mais un extrait peut
 * contenir un nom qu'il reprend). Insensible à la casse, mots entiers seulement.
 */
export function nameMasker(
  candidates: readonly Candidate[],
  labelOf: (candidateId: string) => string,
): (text: string) => string {
  const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const variants: { re: RegExp; id: string; len: number }[] = [];
  for (const c of candidates) {
    const words = c.name.trim().split(/\s+/);
    const forms = new Set([c.name.trim(), words.slice(1).join(" ")].filter((f) => f.length >= 3));
    for (const f of forms) {
      const pattern = escape(f.normalize("NFC")).replace(/\s+/g, "\\s+");
      variants.push({
        re: new RegExp(`(?<!${LETTER})${pattern}(?!${LETTER})`, "giu"),
        id: c.id,
        len: f.length,
      });
    }
  }
  // Formes longues d'abord : « Anne Le Gall » avant « Le Gall ».
  variants.sort((a, b) => b.len - a.len);
  return (text) => variants.reduce((t, v) => t.replace(v.re, labelOf(v.id)), text.normalize("NFC"));
}
