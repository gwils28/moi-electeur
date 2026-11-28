import { describe, expect, it } from "vitest";
import { LABEL_GAP, layoutLabels, wrapLabel } from "../src/lib/chessboard";

describe("layoutLabels", () => {
  it("étiquettes isolées : à côté du marqueur, sans trait de rappel", () => {
    const [a, b] = layoutLabels([
      { id: "a", px: 100, py: 100, side: "right" },
      { id: "b", px: 300, py: 200, side: "left" },
    ]);
    expect(a).toMatchObject({ id: "a", x: 112, y: 104, anchor: "start", leader: null });
    expect(b).toMatchObject({ id: "b", x: 288, y: 204, anchor: "end", leader: null });
  });

  it("points proches du même côté : écart vertical minimal et trait de rappel", () => {
    const out = layoutLabels([
      { id: "b", px: 100, py: 102, side: "right" },
      { id: "a", px: 110, py: 100, side: "right" },
      { id: "c", px: 105, py: 101, side: "right" },
    ]);
    // Ordre de sortie = ordre d'entrée.
    expect(out.map((l) => l.id)).toEqual(["b", "a", "c"]);
    const ys = [...out].sort((p, q) => p.y - q.y).map((l) => l.y);
    for (let i = 1; i < ys.length; i++)
      expect(ys[i]! - ys[i - 1]!).toBeGreaterThanOrEqual(LABEL_GAP);
    const a = out.find((l) => l.id === "a")!;
    expect(a.leader).toBeNull();
    const b = out.find((l) => l.id === "b")!;
    expect(b.leader).toMatchObject({ x1: 100, y1: 102 });
  });

  it("côtés indépendants : pas de décalage entre gauche et droite", () => {
    const out = layoutLabels([
      { id: "l", px: 200, py: 100, side: "left" },
      { id: "r", px: 210, py: 100, side: "right" },
    ]);
    expect(out.every((l) => l.y === 104 && l.leader === null)).toBe(true);
  });
});

describe("wrapLabel", () => {
  it("coupe aux mots et garde « / » avec le mot précédent", () => {
    expect(wrapLabel("Interventionnisme / Redistribution", 17)).toEqual([
      "Interventionnisme /",
      "Redistribution",
    ]);
    expect(wrapLabel("Libéralisme / Baisse de la fiscalité", 17)).toEqual([
      "Libéralisme /",
      "Baisse de la",
      "fiscalité",
    ]);
    expect(wrapLabel("Composante 1 +", 17)).toEqual(["Composante 1 +"]);
  });
});
