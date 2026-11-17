import { describe, expect, it } from "vitest";
import { BLIND_COLOR, displayCandidate, displayCandidates } from "../src/lib/present";

const cand = {
  id: "c1",
  name: "Amandine Vérac",
  party: "Mouvement des Communs (fictif)",
  color: "#b2182b",
  photo: null,
  program_url: "https://example.org",
  blind_alias: "Candidat·e A",
};

describe("displayCandidate", () => {
  it("mode normal : nom, parti, couleur", () => {
    const d = displayCandidate(cand, 0, false);
    expect(d).toMatchObject({ label: "Amandine Vérac", party: cand.party, color: "#b2182b" });
  });

  it("mode aveugle : rien qui révèle l'identité", () => {
    const d = displayCandidate(cand, 0, true);
    const text = JSON.stringify(d);
    for (const word of ["Amandine", "Vérac", "Communs", "#b2182b"])
      expect(text).not.toContain(word);
    expect(d).toMatchObject({ label: "Candidat·e A", party: null, color: BLIND_COLOR });
  });

  it("la forme dépend du rang de session, pas du mode", () => {
    expect(displayCandidate(cand, 2, true).shape).toBe(displayCandidate(cand, 2, false).shape);
    expect(displayCandidate(cand, 0, true).shape).not.toBe(displayCandidate(cand, 1, true).shape);
  });

  it("alias attribué par rang et citations masquées en mode aveugle", () => {
    const d = displayCandidate(cand, 3, true, "Candidat·e D");
    expect(d.label).toBe("Candidat·e D");
    expect(d.hideQuotes).toBe(true);
    expect(displayCandidate(cand, 3, false).hideQuotes).toBe(false);
  });
});

describe("displayCandidates", () => {
  const cands = ["A", "B", "C", "D"].map((l, i) => ({
    ...cand,
    id: `c${i}`,
    blind_alias: `Candidat·e ${l}`,
  }));
  it("alias et formes attribués par rang de session", () => {
    const owners = new Set<string>();
    for (let seed = 0; seed < 20; seed++) {
      const d = displayCandidates(cands, seed, true);
      expect(d.map((x) => x.label)).toEqual(cands.map((c) => c.blind_alias));
      expect(d[0]!.shape).toBe("circle");
      owners.add(d[0]!.id);
    }
    expect(owners.size).toBeGreaterThan(1);
  });
});
