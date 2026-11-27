import { existsSync, readdirSync, readFileSync } from "node:fs";
import type { ElectionConfig } from "@moi-electeur/schemas-ts";
import { join } from "node:path";
import { assembleElection, type ElectionData } from "./data";

/** Élection demandée par défaut (`ELECTION_ID`) ; sinon la première élection réelle publiée (D33). */
export const PREFERRED_ELECTION = process.env.ELECTION_ID;

/** Lecture au build (composant serveur) des JSON produits par `pipeline build`. */
const elections = new Map<string, ElectionData>();

/** Données lues une fois par processus (pages rendues à chaque requête pour la CSP à nonce). */
export function loadElection(id: string): ElectionData {
  const cached = elections.get(id);
  if (cached) return cached;
  const data = readElection(id);
  elections.set(id, data);
  return data;
}

function readElection(id: string): ElectionData {
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

/**
 * Boussoles publiées par `pipeline build` (élections avec affirmations, positions revues et
 * ACP ; une élection « corpus seul » ou en cours de revue n'a que sa configuration).
 */
export function loadCompassElections(): ElectionData[] {
  const root = join(process.cwd(), "public", "data");
  if (!existsSync(root)) return [];
  return readdirSync(root)
    .sort()
    .filter((id) =>
      ["statements.json", "positions.json", "pca_model.json"].every((f) =>
        existsSync(join(root, id, f)),
      ),
    )
    .map((id) => loadElection(id));
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
