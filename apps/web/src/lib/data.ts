import type {
  Candidate,
  ElectionConfig,
  Measure,
  PcaModel,
  Position,
  Statement,
} from "@moi-electeur/schemas-ts";
import { LOADED_STATUSES } from "@moi-electeur/engine";

/** Données d'une élection telles que servies au front (sortie de `pipeline build`). */
export interface ElectionData {
  readonly config: ElectionConfig;
  readonly statements: readonly Statement[];
  readonly positions: readonly Position[];
  readonly measures: readonly Measure[];
  readonly pca: PcaModel;
}

export interface RawElectionFiles {
  readonly config: ElectionConfig;
  readonly statements: { readonly statements: readonly Statement[] };
  readonly positions: { readonly positions: readonly Position[] };
  readonly measures: { readonly measures: readonly Measure[] };
  readonly pca: PcaModel;
}

/**
 * Assemble les fichiers en ne gardant que les positions et mesures validated / corrected
 * (CLAUDE.md). `pipeline build` filtre déjà : ce second filtre protège d'une sortie altérée.
 */
export function assembleElection(raw: RawElectionFiles): ElectionData {
  const loadable = (r: { review: { status: string } }) => LOADED_STATUSES.includes(r.review.status);
  return {
    config: raw.config,
    statements: raw.statements.statements,
    positions: raw.positions.positions.filter(loadable),
    measures: raw.measures.measures.filter(loadable),
    pca: raw.pca,
  };
}

/** Options du sélecteur d'élection (D33) : identifiant et nom de l'élection. */
export function electionOptions(
  elections: readonly ElectionData[],
): { readonly id: string; readonly label: string }[] {
  return elections.map((e) => ({ id: e.config.id, label: e.config.name }));
}

export function themeIds(config: ElectionConfig): string[] {
  return config.themes.map((t) => t.id);
}

export type { Candidate, Statement };
