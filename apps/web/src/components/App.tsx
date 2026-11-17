"use client";

import {
  candidateAnswers,
  decodeAnswers,
  encodeAnswers,
  type Answers,
  type ThemeWeights,
} from "@moi-electeur/engine";
import { useEffect, useMemo, useState } from "react";
import { themeIds, type ElectionData } from "@/lib/data";
import { displayCandidates } from "@/lib/present";
import { loadLocal, saveLocal, sessionSeed } from "@/lib/session";
import { fr } from "@/i18n/fr";
import { Questionnaire } from "./Questionnaire";
import { Results } from "./Results";

type Step = "intro" | "questions" | "results";

/** Boussole : tout est calculé ici, dans le navigateur. Aucune réponse n'est envoyée au réseau. */
export function App({ data }: { data: ElectionData }) {
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

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
      <header>
        <h1 className="text-3xl font-bold">{fr.appName}</h1>
        <p>{fr.tagline}</p>
        {config.fictional && <p className="mt-1 text-sm font-medium">{fr.fictional}</p>}
        <p className="text-sm">{fr.privacy}</p>
      </header>
      {notice && (
        <p role="status" className="rounded border p-2">
          {notice}
        </p>
      )}

      {step === "intro" && (
        <button
          type="button"
          className="rounded border-2 px-4 py-2 font-semibold"
          onClick={() => setStep("questions")}
        >
          {fr.start}
        </button>
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
          <section aria-labelledby="share-title" className="space-y-2 rounded border p-4">
            <h2 id="share-title" className="text-lg font-semibold">
              {fr.share}
            </h2>
            <p className="text-sm">{fr.shareHelp}</p>
            <input
              readOnly
              aria-label={fr.share}
              data-testid="share-url"
              className="w-full rounded border bg-[var(--bg)] px-2 py-1 text-sm text-[var(--fg)]"
              value={shareUrl}
            />
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                className="rounded border px-2 py-1"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(shareUrl);
                    setCopied(true);
                  } catch {
                    setCopied(false);
                  }
                }}
              >
                {copied ? fr.copied : fr.copyLink}
              </button>
              <label className="flex items-center gap-1 text-sm">
                <input
                  type="checkbox"
                  checked={keepLocal}
                  onChange={(e) => {
                    setKeepLocal(e.target.checked);
                    if (!e.target.checked) saveLocal(null);
                  }}
                />
                {fr.saveLocal}
              </label>
              <button
                type="button"
                className="rounded border px-2 py-1"
                onClick={() => setStep("questions")}
              >
                {fr.editAnswers}
              </button>
              <button
                type="button"
                className="rounded border px-2 py-1"
                onClick={() => {
                  setAnswers({});
                  setWeights({});
                  setThemeIndex(0);
                  history.replaceState(null, "", window.location.pathname);
                  setStep("questions");
                }}
              >
                {fr.restart}
              </button>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
