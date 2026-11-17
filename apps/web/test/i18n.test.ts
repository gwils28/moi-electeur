import { describe, expect, it } from "vitest";
import { fr } from "../src/i18n/fr";

function strings(v: unknown): string[] {
  if (typeof v === "string") return [v];
  if (typeof v === "function") return [String((v as (...a: number[]) => string)(1, 2))];
  if (v && typeof v === "object") return Object.values(v).flatMap(strings);
  return [];
}

describe("chaînes UI", () => {
  it("toutes les chaînes (y compris imbriquées et paramétrées) sont non vides", () => {
    const all = strings(fr);
    expect(all.length).toBeGreaterThan(40);
    for (const s of all) expect(s.trim().length).toBeGreaterThan(0);
  });
});
