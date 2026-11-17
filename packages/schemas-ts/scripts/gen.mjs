// Génère src/generated/schemas.ts depuis schemas/*.schema.json.
// --check : échoue si le fichier commité diffère de la génération (dérive).
import { readFileSync, writeFileSync, mkdirSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { compile } from "json-schema-to-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const schemasDir = join(here, "..", "..", "..", "schemas");
const out = join(here, "..", "src", "generated", "schemas.ts");

const files = readdirSync(schemasDir)
  .filter((f) => f.endsWith(".schema.json"))
  .sort();
// Schéma racine synthétique : un seul fichier de sortie, types partagés non dupliqués.
const root = {
  title: "AllSchemas",
  type: "object",
  additionalProperties: false,
  properties: Object.fromEntries(files.map((f) => [f.replace(".schema.json", ""), { $ref: f }])),
};

const banner =
  "/* Fichier généré par packages/schemas-ts/scripts/gen.mjs depuis schemas/. Ne pas éditer. */";
let ts = await compile(root, "AllSchemas", {
  cwd: schemasDir,
  bannerComment: banner,
  additionalProperties: false,
  strictIndexSignatures: true,
  // Bornes de taille contrôlées à la validation, pas par des tuples TS illisibles.
  ignoreMinAndMaxItems: true,
  format: true,
  style: { printWidth: 100, trailingComma: "all" },
});

if (process.argv.includes("--check")) {
  let current = "";
  try {
    current = readFileSync(out, "utf-8");
  } catch {
    // absent : dérive
  }
  if (current !== ts) {
    console.error("Types TS désynchronisés des schémas : lancer `pnpm gen:types`.");
    process.exit(1);
  }
  console.log("Types TS à jour.");
} else {
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, ts);
  console.log(`Écrit ${out}`);
}
