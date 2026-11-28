"use client";

import {
  candidateAnswers,
  decodeAnswers,
  encodeAnswers,
  type Answers,
  type ThemeWeights,
} from "@moi-electeur/engine";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { themeIds, type ElectionData } from "@/lib/data";
import { displayCandidates } from "@/lib/present";
import { loadLocal, saveLocal, sessionSeed } from "@/lib/session";
import { fr } from "@/i18n/fr";
import { PastElectionNote } from "./ElectionPicker";
import { Icon } from "./Icon";
import { Notice } from "./Notice";
import { Questionnaire } from "./Questionnaire";
import { Results } from "./Results";

type Step = "intro" | "questions" | "results";

/** Boussole : tout est calculé ici, dans le navigateur. Aucune réponse n'est envoyée au réseau. */
export function App({ data, picker }: { data: ElectionData; picker?: ReactNode }) {
  const { config, statements, positions } = data;
  const themes = useMemo(() => themeIds(config), [config]);
  const [step, setStep] = useState<Step>("intro");
  const [themeIndex, setThemeIndex] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [weights, setWeights] = useState<ThemeWeights>({});
  const [blind, setBlind] = useState(false);
  const [seed, setSeed] = useState<number | null>(null);
  const [keepLocal, setKeepLocal] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Au montage : graine de session, puis reprise éventuelle depuis #r=... ou la sauvegarde locale.
  useEffect(() => {
    setSeed(sessionSeed());
    const hash = new URLSearchParams(window.location.hash.slice(1)).get("r");
    const saved = loadLocal();
    const code = hash ?? saved;
    if (saved) setKeepLocal(true);
    if (!code) return;
    const r = decodeAnswers(code, statements, themes);
    if (r.ok) {
      setAnswers(r.value.answers);
      setWeights(r.value.weights);
      setStep("results");
    } else if (hash) {
      setNotice(fr.invalidCode);
    }
  }, [statements, themes]);

  const code = useMemo(
    () => encodeAnswers({ answers, weights }, statements, themes),
    [answers, weights, statements, themes],
  );
  useEffect(() => {
    if (keepLocal) saveLocal(code);
  }, [keepLocal, code]);

  const candAnswers = useMemo(
    () =>
      Object.fromEntries(
        config.candidates.map((c) => [c.id, candidateAnswers(positions, c.id, statements)]),
      ),
    [config, positions, statements],
  );
  const displays = useMemo(() => {
    if (seed === null) return [];
    return displayCandidates(config.candidates, seed, blind);
  }, [config, seed, blind]);

  const setAnswer = (id: string, value: number | null) =>
    setAnswers((a) => ({ ...a, [id]: value }));
  const setWeight = (t: string, w: number) => setWeights((x) => ({ ...x, [t]: w }));
  const shareUrl =
    typeof window === "undefined"
      ? ""
      : `${window.location.origin}${window.location.pathname}#r=${code}`;

  const mentions = (
    <div className="space-y-1 text-sm text-muted">
      {config.fictional && <p className="font-medium text-fg">{fr.fictional}</p>}
      <PastElectionNote config={config} />
      <p>{fr.privacy}</p>
    </div>
  );

  return (
    <main className="mx-auto max-w-6xl space-y-8 p-4 sm:p-6">
      {notice && (
        <Notice variant="info" role="status" className="mx-auto max-w-2xl">
          <p>{notice}</p>
        </Notice>
      )}

      {step === "intro" ? (
        <div className="card mx-auto max-w-2xl space-y-6 sm:p-8">
          <header className="space-y-3">
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{fr.compass.title}</h1>
            <p className="max-w-prose text-lg text-muted">{fr.compass.intro}</p>
          </header>
          <ul className="space-y-2">
            {fr.compass.facts.map((f) => (
              <li key={f} className="flex items-start gap-2">
                <span className="mt-1 text-muted">
                  <Icon name="check" />
                </span>
                {f}
              </li>
            ))}
          </ul>
          {picker}
          {mentions}
          <button type="button" className="btn btn-primary" onClick={() => setStep("questions")}>
            {fr.start}
            <Icon name="arrow-right" />
          </button>
        </div>
      ) : (
        <header className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{fr.compass.title}</h1>
          {picker}
          {mentions}
        </header>
      )}

      {step === "questions" && (
        <Questionnaire
          config={config}
          statements={statements}
          themeIndex={themeIndex}
          answers={answers}
          weights={weights}
          onAnswer={setAnswer}
          onWeight={setWeight}
          onNavigate={setThemeIndex}
          onFinish={() => setStep("results")}
        />
      )}

      {step === "results" && seed !== null && (
        <>
          <Results
            data={data}
            displays={displays}
            candidateAnswers={candAnswers}
            answers={answers}
            weights={weights}
            blind={blind}
            onBlind={setBlind}
            onAnswer={setAnswer}
            onWeight={setWeight}
          />
          <section aria-labelledby="share-title" className="card space-y-4">
            <div className="space-y-1">
              <h2 id="share-title" className="text-lg font-semibold">
                {fr.share}
              </h2>
              <p className="hint">{fr.shareHelp}</p>
            </div>
            <div className="relative flex flex-col gap-2 sm:flex-row sm:items-center">
              <input
                readOnly
                aria-label={fr.share}
                data-testid="share-url"
                className="field min-w-0 flex-1 text-sm"
                value={shareUrl}
              />
              <button
                type="button"
                className="btn btn-primary btn-sm self-start sm:self-auto"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(shareUrl);
                    setCopied(true);
                  } catch {
                    setCopied(false);
                  }
                }}
              >
                <Icon name={copied ? "check" : "copy"} />
                {copied ? fr.copied : fr.copyLink}
              </button>
              <span role="status" className="sr-only">
                {copied ? fr.copied : ""}
              </span>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="size-4"
                checked={keepLocal}
                onChange={(e) => {
                  setKeepLocal(e.target.checked);
                  if (!e.target.checked) saveLocal(null);
                }}
              />
              {fr.saveLocal}
            </label>
            <div className="flex flex-wrap justify-between gap-3 border-t border-line pt-4">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setStep("questions")}
              >
                {fr.editAnswers}
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => {
                  setAnswers({});
                  setWeights({});
                  setThemeIndex(0);
                  history.replaceState(null, "", window.location.pathname);
                  setStep("questions");
                }}
              >
                <Icon name="refresh" />
                {fr.restart}
              </button>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
