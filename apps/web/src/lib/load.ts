import { readFileSync } from "node:fs";
import { join } from "node:path";
import { assembleElection, type ElectionData } from "./data";

export const DEFAULT_ELECTION = process.env.ELECTION_ID ?? "demo-fictive";

/** Lecture au build (composant serveur) des JSON produits par `pipeline build`. */
export function loadElection(id: string = DEFAULT_ELECTION): ElectionData {
  const dir = join(process.cwd(), "public", "data", id);
  const read = (f: string) => JSON.parse(readFileSync(join(dir, f), "utf-8"));
  return assembleElection({
    config: read("election_config.json"),
    statements: read("statements.json"),
    positions: read("positions.json"),
    measures: read("measures.json"),
    pca: read("pca_model.json"),
  });
}
