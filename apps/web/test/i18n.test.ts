import { describe, expect, it } from "vitest";
import { fr } from "../src/i18n/fr";

describe("chaînes UI", () => {
  it("toutes les chaînes sont non vides", () => {
    for (const value of Object.values(fr)) expect(value.length).toBeGreaterThan(0);
  });
});
