"use client";

import type { AskRequest, AskTurn } from "@moi-electeur/schemas-ts";
import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { fr } from "@/i18n/fr";
import {
  applyEvent,
  EMPTY_ANSWER,
  pushHistory,
  toTurn,
  type AnswerState,
} from "@/lib/explorer/answer";
import { askStream, AskHttpError } from "@/lib/explorer/client";
import type { ExplorerElection } from "@/lib/load";
import { displayCandidates, nameMasker } from "@/lib/present";
import { sessionSeed } from "@/lib/session";
import { AnswerView } from "./AnswerView";

type Mode = NonNullable<AskRequest["mode"]>;

export interface Turn {
  readonly id: number;
  readonly question: string;
  readonly mode: Mode;
  readonly state: AnswerState;
  readonly failure: { readonly code: string; readonly message: string } | null;
  readonly stopped: boolean;
  readonly streaming: boolean;
}

const MODE_ERRORS = new Set(["mode_unavailable", "mode_rate_limited", "mode_budget_exhausted"]);

/**
 * Explorateur RAG (PLAN § 4.6). La conversation et ses 3 derniers tours vivent dans l'état React
 * de l'onglet : rien en localStorage, rien d'autre que la question n'est envoyé au serveur.
 */
export function Explorer({ elections }: { elections: readonly ExplorerElection[] }) {
  const [electionId, setElectionId] = useState(elections[0]?.id ?? "");
  const election = elections.find((e) => e.id === electionId) ?? elections[0];
  const [seed, setSeed] = useState<number | null>(null);
  const [blind, setBlind] = useState(false);
  const [mode, setMode] = useState<Mode>("rapide");
  const [excluded, setExcluded] = useState<ReadonlySet<string>>(new Set());
  const [theme, setTheme] = useState<string>("");
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<readonly Turn[]>([]);
  const [history, setHistory] = useState<readonly AskTurn[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const nextId = useRef(1);

  useEffect(() => setSeed(sessionSeed()), []);
  useEffect(() => () => abortRef.current?.abort(), []);

  const displays = useMemo(
    () => (election && seed !== null ? displayCandidates(election.candidates, seed, blind) : []),
    [election, seed, blind],
  );
  const labelOf = useMemo(() => {
    const labels = new Map(displays.map((d) => [d.id, d.label]));
    return (id: string) => labels.get(id) ?? fr.explorer.unknownSource;
  }, [displays]);
  const mask = useMemo(
    () => (blind && election ? nameMasker(election.candidates, labelOf) : undefined),
    [blind, election, labelOf],
  );

  const streaming = turns.some((t) => t.streaming);
  const included = displays.filter((d) => !excluded.has(d.id));
  const canSend =
    !streaming && question.trim().length > 0 && included.length > 0 && election !== undefined;

  const resetConversation = () => {
    abortRef.current?.abort();
    setTurns([]);
    setHistory([]);
  };

  const update = (id: number, f: (t: Turn) => Turn) =>
    setTurns((all) => all.map((t) => (t.id === id ? f(t) : t)));

  async function send(q: string, sendMode: Mode) {
    if (!election) return;
    const id = nextId.current++;
    const controller = new AbortController();
    abortRef.current = controller;
    setTurns((all) => [
      ...all,
      {
        id,
        question: q,
        mode: sendMode,
        state: EMPTY_ANSWER,
        failure: null,
        stopped: false,
        streaming: true,
      },
    ]);
    const body: AskRequest = {
      election_id: election.id,
      question: q,
      mode: sendMode,
      ...(excluded.size > 0 ? { candidate_ids: included.map((d) => d.id) } : {}),
      ...(theme ? { theme } : {}),
      ...(history.length > 0 ? { history: [...history] } : {}),
    };
    let state = EMPTY_ANSWER;
    try {
      for await (const ev of askStream(body, { signal: controller.signal })) {
        state = applyEvent(state, ev);
        const snapshot = state;
        update(id, (t) => ({ ...t, state: snapshot }));
      }
      // Conversation remise à zéro (nouvelle conversation, autre élection) pendant le flux.
      if (controller.signal.aborted) {
        update(id, (t) => ({ ...t, streaming: false, stopped: true }));
        return;
      }
      const turn = toTurn(q, state);
      if (turn) setHistory((h) => pushHistory(h, turn));
      // Flux terminé sans `done` ni `error` (coupure réseau ou proxy) : signalé.
      const failure =
        !state.done && !state.error
          ? { code: "incomplete", message: fr.explorer.incomplete }
          : null;
      update(id, (t) => ({ ...t, streaming: false, failure }));
    } catch (e) {
      if (controller.signal.aborted) {
        update(id, (t) => ({ ...t, streaming: false, stopped: true }));
      } else {
        const failure =
          e instanceof AskHttpError && e.message
            ? { code: e.code, message: e.message }
            : { code: "network", message: fr.explorer.networkError };
        update(id, (t) => ({ ...t, streaming: false, failure }));
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!canSend) return;
    const q = question.trim();
    setQuestion("");
    void send(q, mode);
  };
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      e.currentTarget.form?.requestSubmit();
    }
  };

  if (!election) {
    return (
      <main className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
        <h1 className="text-3xl font-bold">{fr.explorer.title}</h1>
        <p>{fr.explorer.noElection}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-4 sm:p-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">{fr.explorer.title}</h1>
        <p>{fr.explorer.intro}</p>
        <p className="rounded border-l-4 p-2 text-sm" data-testid="disclaimer">
          {fr.explorer.disclaimer}
        </p>
        <p className="text-sm">{fr.explorer.privacy}</p>
      </header>

      <section aria-labelledby="settings-title" className="space-y-4 rounded border p-4">
        <h2 id="settings-title" className="sr-only">
          {fr.explorer.mode}
        </h2>
        {elections.length > 1 && (
          <label className="flex flex-col gap-1">
            <span className="font-medium">{fr.explorer.election}</span>
            <select
              className="rounded border bg-[var(--bg)] px-2 py-1"
              value={election.id}
              onChange={(e) => {
                resetConversation();
                setExcluded(new Set());
                setTheme("");
                setElectionId(e.target.value);
              }}
            >
              {elections.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.label}
                </option>
              ))}
            </select>
          </label>
        )}
        {elections.length === 1 && <p className="font-medium">{election.label}</p>}

        <fieldset className="space-y-1">
          <legend className="font-medium">{fr.explorer.mode}</legend>
          {(
            [
              ["rapide", fr.explorer.modeFast, fr.explorer.modeFastHelp],
              ["approfondi", fr.explorer.modeDeep, fr.explorer.modeDeepHelp],
            ] as const
          ).map(([value, label, help]) => (
            <label key={value} className="flex items-start gap-2">
              <input
                type="radio"
                name="mode"
                value={value}
                className="mt-1"
                checked={mode === value}
                onChange={() => setMode(value)}
              />
              <span>
                <span className="font-medium">{label}</span>
                <span className="block text-sm">{help}</span>
              </span>
            </label>
          ))}
        </fieldset>

        <fieldset>
          <legend className="font-medium">{fr.explorer.candidates}</legend>
          <div className="my-1 flex gap-2 text-sm">
            <button
              type="button"
              className="rounded border px-2"
              onClick={() => setExcluded(new Set())}
            >
              {fr.explorer.allCandidates}
            </button>
            <button
              type="button"
              className="rounded border px-2"
              onClick={() => setExcluded(new Set(displays.map((d) => d.id)))}
            >
              {fr.explorer.noCandidates}
            </button>
          </div>
          <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2 md:grid-cols-3">
            {displays.map((d) => (
              <label key={d.id} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={!excluded.has(d.id)}
                  onChange={(e) =>
                    setExcluded((x) => {
                      const next = new Set(x);
                      if (e.target.checked) next.delete(d.id);
                      else next.add(d.id);
                      return next;
                    })
                  }
                />
                {d.label}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1">
            <span className="font-medium">{fr.explorer.theme}</span>
            <select
              className="rounded border bg-[var(--bg)] px-2 py-1"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
            >
              <option value="">{fr.explorer.allThemes}</option>
              {election.themes.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={blind} onChange={(e) => setBlind(e.target.checked)} />
            {fr.blind}
          </label>
        </div>
        {blind && <p className="text-sm">{fr.explorer.blindNote}</p>}
      </section>

      <section aria-labelledby="conversation-title" className="space-y-6">
        <h2 id="conversation-title" className="sr-only">
          {fr.explorer.answer}
        </h2>
        {turns.map((t, i) => (
          <article key={t.id} className="space-y-3" data-testid="turn">
            <div className="rounded bg-[color-mix(in_srgb,var(--fg)_8%,transparent)] p-3">
              <h3 className="text-sm font-semibold">{fr.explorer.you}</h3>
              <p className="whitespace-pre-wrap">{t.question}</p>
            </div>
            <div aria-live="polite" aria-busy={t.streaming}>
              {t.streaming && (
                <p role="status" className="text-sm italic">
                  {fr.explorer.streaming}
                </p>
              )}
              <AnswerView
                turnId={t.id}
                state={t.state}
                streaming={t.streaming}
                displays={displays}
                labelOf={labelOf}
                mask={mask}
                blind={blind}
              />
              {t.stopped && <p className="text-sm italic">{fr.explorer.stopped}</p>}
              {(t.failure ?? t.state.error) && (
                <div role="alert" className="space-y-2 rounded border-2 p-3">
                  <p>{(t.failure ?? t.state.error)!.message}</p>
                  {t.failure && MODE_ERRORS.has(t.failure.code) && i === turns.length - 1 && (
                    <button
                      type="button"
                      className="rounded border px-2 py-1"
                      disabled={streaming}
                      onClick={() => {
                        setMode("rapide");
                        void send(t.question, "rapide");
                      }}
                    >
                      {fr.explorer.switchToFast}
                    </button>
                  )}
                </div>
              )}
            </div>
          </article>
        ))}
      </section>

      <form onSubmit={onSubmit} className="space-y-2">
        <label htmlFor="question" className="font-medium">
          {fr.explorer.question}
        </label>
        <textarea
          id="question"
          aria-describedby="question-help"
          className="block min-h-24 w-full rounded border bg-[var(--bg)] p-2 text-[var(--fg)]"
          maxLength={500}
          placeholder={fr.explorer.placeholder}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <p id="question-help" className="text-sm">
          {fr.explorer.questionHelp}
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            disabled={!canSend}
            className="rounded border-2 px-4 py-2 font-semibold disabled:opacity-50"
          >
            {fr.explorer.send}
          </button>
          {streaming && (
            <button
              type="button"
              className="rounded border px-3 py-2"
              onClick={() => abortRef.current?.abort()}
            >
              {fr.explorer.stop}
            </button>
          )}
          {turns.length > 0 && !streaming && (
            <button type="button" className="rounded border px-3 py-2" onClick={resetConversation}>
              {fr.explorer.newConversation}
            </button>
          )}
        </div>
        {history.length > 0 && <p className="text-sm">{fr.explorer.historyNote(history.length)}</p>}
      </form>
    </main>
  );
}
