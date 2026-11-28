import { describe, expect, it } from "vitest";
import { orderByAdjusted } from "../src/lib/results";

const row = (id: string, adjusted: number | null) => ({
  id,
  prox: adjusted === null ? null : { adjusted },
});

describe("orderByAdjusted (PLAN D59)", () => {
  it("score ajusté décroissant", () => {
    const r = orderByAdjusted([row("a", 40), row("b", 70), row("c", 55)]);
    expect(r.map((x) => x.id)).toEqual(["b", "c", "a"]);
  });

  it("égalités : ordre de session conservé (tri stable)", () => {
    const r = orderByAdjusted([row("x", 50), row("y", 60), row("z", 50), row("w", 50)]);
    expect(r.map((x) => x.id)).toEqual(["y", "x", "z", "w"]);
  });

  it("score non calculable (aucune affirmation commune) en dernier, ordre de session", () => {
    const r = orderByAdjusted([row("n1", null), row("a", 10), row("n2", null)]);
    expect(r.map((x) => x.id)).toEqual(["a", "n1", "n2"]);
  });

  it("ne modifie pas le tableau d'origine", () => {
    const input = [row("a", 1), row("b", 2)];
    orderByAdjusted(input);
    expect(input.map((x) => x.id)).toEqual(["a", "b"]);
  });
});
