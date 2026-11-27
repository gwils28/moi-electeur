import { existsSync, readdirSync, readFileSync } from "node:fs";
import type { ElectionConfig } from "@moi-electeur/schemas-ts";
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

/** Élection proposée dans l'explorateur : celles qui ont un corpus de documents officiels. */
export interface ExplorerElection {
  readonly id: string;
  readonly label: string;
  readonly themes: ElectionConfig["themes"];
  readonly candidates: ElectionConfig["candidates"];
}

/**
 * Configurations publiées par `pipeline build` (y compris les élections « corpus seul », D13)
 * dont le corpus n'est pas vide. L'indexation réelle est vérifiée par /api/ask (404 sinon).
 */
export function loadExplorerElections(): ExplorerElection[] {
  const root = join(process.cwd(), "public", "data");
  if (!existsSync(root)) return [];
  const out: ExplorerElection[] = [];
  for (const id of readdirSync(root).sort()) {
    const file = join(root, id, "election_config.json");
    if (!existsSync(file)) continue;
    const config = JSON.parse(readFileSync(file, "utf-8")) as ElectionConfig;
    if (config.corpus.length === 0) continue;
    out.push({
      id: config.id,
      label: config.name,
      themes: config.themes,
      candidates: config.candidates,
    });
  }
  return out;
}
