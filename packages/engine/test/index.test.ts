import { describe, expect, it } from "vitest";
import { ENGINE_VERSION } from "../src/index";

describe("squelette du moteur", () => {
  it("expose une version semver", () => {
    expect(ENGINE_VERSION).toMatch(/^\d+\.\d+\.\d+$/);
  });
});
