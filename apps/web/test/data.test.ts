import { describe, expect, it } from "vitest";
import { assembleElection, type RawElectionFiles } from "../src/lib/data";

const review = (status: string) => ({ status, reviewer: "t", date: "2026-11-17" });
const pos = (statement_id: string, status: string) => ({
  candidate_id: "c1",
  statement_id,
  value: 1,
  confidence: "high" as const,
  evidence: [],
  proposed_by: "t",
  review: review(status) as never,
});

describe("assembleElection", () => {
  it("ne charge que les positions et mesures validated / corrected", () => {
    const raw = {
      config: {} as never,
      statements: { statements: [] },
      positions: {
        positions: [
          pos("s01", "validated"),
          pos("s02", "corrected"),
          pos("s03", "rejected"),
          pos("s04", "pending"),
        ],
      },
      measures: {
        measures: [{ review: review("validated") }, { review: review("rejected") }] as never,
      },
      pca: {} as never,
    } satisfies RawElectionFiles;
    const data = assembleElection(raw);
    expect(data.positions.map((p) => p.statement_id)).toEqual(["s01", "s02"]);
    expect(data.measures).toHaveLength(1);
  });
});
