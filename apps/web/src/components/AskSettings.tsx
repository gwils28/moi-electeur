"use client";

import type { AskRequest } from "@moi-electeur/schemas-ts";
import { useId } from "react";
import { fr } from "@/i18n/fr";
import type { ExplorerElection } from "@/lib/load";
import type { CandidateDisplay } from "@/lib/present";

type Mode = NonNullable<AskRequest["mode"]>;

const MODES = [
  ["rapide", fr.explorer.modeFast, fr.explorer.modeFastHelp],
  ["approfondi", fr.explorer.modeDeep, fr.explorer.modeDeepHelp],
] as const;

/**
 * Réglages de l'interrogatoire (I-b) : type de réponse en segments, thème, mode aveugle et
 * candidats inclus en puces. Les `label` des puces ne contiennent que le nom du candidat
 * (l'e2e compare leur texte aux titres des sections de réponse).
 */
export function AskSettings({
  elections,
  election,
  onElectionChange,
  mode,
  onModeChange,
  displays,
  excluded,
  onExcludedChange,
  theme,
  onThemeChange,
  blind,
  onBlindChange,
}: {
  elections: readonly ExplorerElection[];
  election: ExplorerElection;
  onElectionChange: (id: string) => void;
  mode: Mode;
  onModeChange: (m: Mode) => void;
  displays: readonly CandidateDisplay[];
  excluded: ReadonlySet<string>;
  onExcludedChange: (next: ReadonlySet<string>) => void;
  theme: string;
  onThemeChange: (t: string) => void;
  blind: boolean;
  onBlindChange: (b: boolean) => void;
}) {
  const uid = useId();
  const helpId = (m: Mode) => `${uid}-help-${m}`;
  const included = displays.filter((d) => !excluded.has(d.id)).length;

  return (
    <section aria-labelledby={`${uid}-title`} className="panel space-y-5">
      <h2 id={`${uid}-title`} className="text-lg font-semibold">
        {fr.explorer.settings}
      </h2>

      <div className="grid gap-5 md:grid-cols-2">
        {elections.length > 1 && (
          <div className="md:col-span-2">
            <label htmlFor={`${uid}-election`} className="label">
              {fr.explorer.election}
            </label>
            <select
              id={`${uid}-election`}
              className="field"
              value={election.id}
              onChange={(e) => onElectionChange(e.target.value)}
            >
              {elections.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.label}
                </option>
              ))}
            </select>
          </div>
        )}

        <fieldset className="min-w-0">
          <legend className="label">{fr.explorer.mode}</legend>
          <div className="segmented">
            {MODES.map(([value, label]) => (
              <label key={value}>
                <input
                  type="radio"
                  name={`${uid}-mode`}
                  value={value}
                  checked={mode === value}
                  aria-describedby={helpId(value)}
                  onChange={() => onModeChange(value)}
                />
                {label}
              </label>
            ))}
          </div>
          {MODES.map(([value, , help]) => (
            <p key={value} id={helpId(value)} className="hint mt-2" hidden={mode !== value}>
              {help}
            </p>
          ))}
        </fieldset>

        <div className="flex min-w-0 flex-col gap-4">
          <div>
            <label htmlFor={`${uid}-theme`} className="label">
              {fr.explorer.theme}
            </label>
            <select
              id={`${uid}-theme`}
              className="field"
              value={theme}
              onChange={(e) => onThemeChange(e.target.value)}
            >
              <option value="">{fr.explorer.allThemes}</option>
              {election.themes.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="inline-flex min-h-11 items-center gap-2 text-sm font-medium">
              <input
                type="checkbox"
                className="h-4 w-4"
                checked={blind}
                onChange={(e) => onBlindChange(e.target.checked)}
              />
              {fr.blind}
            </label>
            {blind && <p className="hint">{fr.explorer.blindNote}</p>}
          </div>
        </div>

        <fieldset className="min-w-0 md:col-span-2">
          <legend className="label">{fr.explorer.candidates}</legend>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => onExcludedChange(new Set())}
            >
              {fr.explorer.allCandidates}
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => onExcludedChange(new Set(displays.map((d) => d.id)))}
            >
              {fr.explorer.noCandidates}
            </button>
            <span className="hint tabular-nums">
              {fr.explorer.includedCount(included, displays.length)}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {displays.map((d) => (
              <label key={d.id} className="chip">
                <input
                  type="checkbox"
                  checked={!excluded.has(d.id)}
                  onChange={(e) => {
                    const next = new Set(excluded);
                    if (e.target.checked) next.delete(d.id);
                    else next.add(d.id);
                    onExcludedChange(next);
                  }}
                />
                {d.label}
              </label>
            ))}
          </div>
        </fieldset>
      </div>
    </section>
  );
}
