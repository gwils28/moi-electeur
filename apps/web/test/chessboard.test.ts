import { describe, expect, it } from "vitest";
import {
  LABEL_GAP,
  layoutLabels,
  PROXIMITY_EDGE_SCORE,
  proximityLayout,
  wrapLabel,
} from "../src/lib/chessboard";

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

describe("proximityLayout (PLAN D60) : distance proportionnelle à 100 - score, bord à 25 %", () => {
  const user = { x: 2, y: -1 };

  it("distance au centre proportionnelle à 100 - score (bord du cercle, 10, = score 25)", () => {
    const [a] = proximityLayout(user, [{ id: "a", x: 6, y: -1, score: 70 }]);
    expect(PROXIMITY_EDGE_SCORE).toBe(25);
    expect(Math.hypot(a!.x!, a!.y!)).toBeCloseTo(4, 10);
  });

  it("direction conservée : candidat à droite et au-dessus de l'utilisateur", () => {
    const [a] = proximityLayout(user, [{ id: "a", x: 5, y: 3, score: 50 }]);
    const angle = Math.atan2(a!.y!, a!.x!);
    expect(angle).toBeCloseTo(Math.atan2(4, 3), 10);
    expect(Math.hypot(a!.x!, a!.y!)).toBeCloseTo(20 / 3, 10);
  });

  it("score 100 : au centre ; score hors bornes : borné", () => {
    const r = proximityLayout(user, [
      { id: "a", x: 5, y: 3, score: 100 },
      { id: "b", x: 5, y: 3, score: -20 },
      { id: "c", x: 5, y: 3, score: 130 },
    ]);
    expect(Math.hypot(r[0]!.x!, r[0]!.y!)).toBeCloseTo(0, 10);
    expect(Math.hypot(r[1]!.x!, r[1]!.y!)).toBeCloseTo(10, 10);
    expect(Math.hypot(r[2]!.x!, r[2]!.y!)).toBeCloseTo(0, 10);
  });

  it("score non calculable : non placé", () => {
    expect(proximityLayout(user, [{ id: "a", x: 5, y: 3, score: null }])).toEqual([
      { id: "a", x: null, y: null },
    ]);
  });

  it("position confondue avec l'utilisateur ou inconnue : direction répartie, distance exacte", () => {
    const r = proximityLayout(user, [
      { id: "a", x: 2, y: -1, score: 60 },
      { id: "b", x: null, y: null, score: 60 },
    ]);
    for (const p of r) expect(Math.hypot(p.x!, p.y!)).toBeCloseTo(16 / 3, 10);
    expect(Math.hypot(r[0]!.x! - r[1]!.x!, r[0]!.y! - r[1]!.y!)).toBeGreaterThan(1);
  });
});
