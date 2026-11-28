"use client";

import { useState } from "react";
import { electionOptions, type ElectionData } from "@/lib/data";
import { App } from "./App";
import { ElectionPicker } from "./ElectionPicker";

/** Boussole de l'élection choisie ; changer d'élection repart d'un questionnaire vierge. */
export function CompassHome({
  elections,
  defaultId,
}: {
  elections: readonly ElectionData[];
  defaultId: string;
}) {
  const [id, setId] = useState(defaultId);
  const data = elections.find((e) => e.config.id === id) ?? elections[0]!;
  const options = electionOptions(elections);
  return (
    <App
      key={data.config.id}
      data={data}
      picker={<ElectionPicker options={options} value={data.config.id} onChange={setId} />}
    />
  );
}
