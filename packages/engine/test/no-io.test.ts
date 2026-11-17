import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import pkg from "../package.json" with { type: "json" };

// Garde-fou mécanique « zéro I/O » (CLAUDE.md, PLAN § 1), complète la règle ESLint.
const SRC = join(import.meta.dirname, "..", "src");
const FORBIDDEN = [
  /\bfetch\s*\(/,
  /\bXMLHttpRequest\b/,
  /\bWebSocket\b/,
  /\bEventSource\b/,
  /\bnavigator\./,
  /\b(local|session)Storage\b/,
  /\bindexedDB\b/,
  /\bconsole\./,
  /\bsendBeacon\b/,
  /\bimport\s*\(/,
  /\bfrom\s+["'](?!\.{1,2}\/)/,
  /\brequire\s*\(/,
  /\bglobalThis\b/,
  /\bself\b/,
  /\beval\s*\(/,
  /\bFunction\s*\(/,
  /\bimportScripts\b/,
  /\bpostMessage\b/,
  /\bnew\s+Image\b/,
];

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? sources(path) : path.endsWith(".ts") ? [path] : [];
  });
}

export function violations(code: string): string[] {
  return FORBIDDEN.filter((re) => re.test(code)).map(String);
}

describe("zéro I/O dans packages/engine", () => {
  it("aucune dépendance d'exécution", () => {
    const p = pkg as unknown as Record<string, object | undefined>;
    for (const field of ["dependencies", "peerDependencies", "optionalDependencies"]) {
      expect(Object.keys(p[field] ?? {})).toEqual([]);
    }
  });

  it.each(sources(SRC))("%s ne contient aucun identifiant d'I/O", (file) => {
    expect(violations(readFileSync(file, "utf-8"))).toEqual([]);
  });

  it("le détecteur repère bien les appels interdits", () => {
    expect(violations('fetch("https://x")')).not.toEqual([]);
    expect(violations('import { a } from "lodash";')).not.toEqual([]);
    expect(violations("localStorage.setItem('a', '1')")).not.toEqual([]);
    for (const code of [
      'globalThis["fe" + "tch"]("x")',
      "self.fetch",
      'eval("1")',
      'new Function("return 1")',
      'new Image().src = "x"',
    ]) {
      expect(violations(code)).not.toEqual([]);
    }
    expect(violations('import { a } from "./a";')).toEqual([]);
  });
});
