import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { decodeAnswers, encodeAnswers } from "../src/code";
import { STATEMENTS, THEMES, answersArb, weightsArb } from "./helpers";

// Code de réponses pour le fragment d'URL #r=... (jamais envoyé au serveur).
const themes = [...THEMES];

describe("encodeAnswers / decodeAnswers", () => {
  it("aller-retour exact", () => {
    fc.assert(
      fc.property(answersArb(), weightsArb, (answers, weights) => {
        const code = encodeAnswers({ answers, weights }, STATEMENTS, themes);
        expect(decodeAnswers(code, STATEMENTS, themes)).toEqual({
          ok: true,
          value: { answers, weights },
        });
      }),
    );
  });

  it("code compact et sûr pour une URL", () => {
    fc.assert(
      fc.property(answersArb(), weightsArb, (answers, weights) => {
        const code = encodeAnswers({ answers, weights }, STATEMENTS, themes);
        expect(code).toMatch(/^[A-Za-z0-9._~-]+$/);
        expect(code.length).toBeLessThanOrEqual(STATEMENTS.length + themes.length + 3);
      }),
    );
  });

  it("thème sans poids explicite encodé à 1", () => {
    const code = encodeAnswers({ answers: {}, weights: {} }, STATEMENTS, themes);
    const r = decodeAnswers(code, STATEMENTS, themes);
    expect(r.ok && r.value.weights).toEqual({ eco: 1, soc: 1, eur: 1 });
  });

  it("erreurs typées, jamais d'exception", () => {
    const good = encodeAnswers({ answers: {}, weights: {} }, STATEMENTS, themes);
    expect(decodeAnswers("", STATEMENTS, themes)).toEqual({ ok: false, error: "empty" });
    expect(decodeAnswers("9" + good.slice(1), STATEMENTS, themes)).toEqual({
      ok: false,
      error: "version",
    });
    expect(decodeAnswers(good.slice(0, -2), STATEMENTS, themes)).toEqual({
      ok: false,
      error: "length",
    });
    expect(decodeAnswers(good.replace(/.$/, "z"), STATEMENTS, themes)).toEqual({
      ok: false,
      error: "char",
    });
    fc.assert(
      fc.property(fc.string(), (s) => {
        expect(() => decodeAnswers(s, STATEMENTS, themes)).not.toThrow();
      }),
    );
  });

  it("poids hors {1, 2, 3} refusé à l'encodage", () => {
    expect(() => encodeAnswers({ answers: {}, weights: { eco: 4 } }, STATEMENTS, themes)).toThrow(
      RangeError,
    );
  });
});
