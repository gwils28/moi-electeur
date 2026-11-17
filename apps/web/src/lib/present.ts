import { shuffleCandidates } from "@moi-electeur/engine";
import type { Candidate } from "@moi-electeur/schemas-ts";

/**
 * Seul point d'accès à l'identité d'un candidat pour l'affichage (mode aveugle, SPEC § 5.5).
 * Les composants n'accèdent jamais directement à `name`, `party`, `color` ou `photo`
 * (règle ESLint dans apps/web/src/components).
 */
export interface CandidateDisplay {
  readonly id: string;
  readonly label: string;
  readonly party: string | null;
  readonly color: string;
  readonly shape: Shape;
  readonly documentLabel: string;
  /** Mode aveugle : les citations peuvent contenir un nom ou un slogan, elles sont masquées. */
  readonly hideQuotes: boolean;
}

export const SHAPES = ["circle", "square", "triangle", "diamond", "cross", "star"] as const;
export type Shape = (typeof SHAPES)[number];

/** Palette neutre du mode aveugle : gris de luminosités distinctes, non connotés. */
export const BLIND_COLOR = "#5f6368";

/**
 * `rank` est le rang dans l'ordre aléatoire de session et `alias` l'alias attribué à ce rang :
 * ni la forme ni l'alias ne sont liés à l'ordre (public) du fichier de configuration, sinon
 * le mode aveugle serait réversible d'une session à l'autre.
 */
export function displayCandidate(
  candidate: Candidate,
  rank: number,
  blind: boolean,
  alias: string = candidate.blind_alias,
): CandidateDisplay {
  const shape = SHAPES[rank % SHAPES.length]!;
  if (blind) {
    return {
      id: candidate.id,
      label: alias,
      party: null,
      color: BLIND_COLOR,
      shape,
      documentLabel: "Programme",
      hideQuotes: true,
    };
  }
  return {
    id: candidate.id,
    label: candidate.name,
    party: candidate.party,
    color: candidate.color,
    shape,
    documentLabel: `Programme de ${candidate.name}`,
    hideQuotes: false,
  };
}

/**
 * Candidats dans l'ordre aléatoire de session. Forme et alias suivent le rang tiré au sort,
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
