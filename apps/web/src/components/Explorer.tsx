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
import { AskSettings } from "./AskSettings";
import { Icon } from "./Icon";
import { Notice } from "./Notice";

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
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Le formulaire change de place au premier tour et à la remise à zéro : on y rend le focus
  // (sans défiler, pour ne pas sauter la réponse en cours).
  const refocus = useRef(false);
  const hasTurns = turns.length > 0;
  useEffect(() => {
    if (!refocus.current) return;
    refocus.current = false;
    textareaRef.current?.focus({ preventScroll: true });
  }, [hasTurns]);

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
    refocus.current = turns.length === 0;
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
      <main className="mx-auto max-w-4xl space-y-4 px-4 py-8 sm:px-6">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{fr.explorer.title}</h1>
        <p>{fr.explorer.noElection}</p>
      </main>
    );
  }

  // Un seul formulaire rendu à la fois : en tête tant qu'il n'y a pas de tour, sous la
  // conversation ensuite (I-a).
  const composer = (
    <form onSubmit={onSubmit} className="card space-y-3">
      <label htmlFor="question" className="label text-base">
        {fr.explorer.question}
      </label>
      <textarea
        ref={textareaRef}
        id="question"
        aria-describedby="question-help"
        rows={3}
        className="field block min-h-24 text-base"
        maxLength={500}
        placeholder={fr.explorer.placeholder}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={onKeyDown}
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p id="question-help" className="hint min-w-0 flex-1 basis-60">
          {fr.explorer.questionHelp}
        </p>
        <div className="flex flex-wrap gap-2">
          {turns.length > 0 && !streaming && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                refocus.current = true;
                resetConversation();
              }}
            >
              <Icon name="refresh" />
              {fr.explorer.newConversation}
            </button>
          )}
          {streaming && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => abortRef.current?.abort()}
            >
              <Icon name="x" />
              {fr.explorer.stop}
            </button>
          )}
          <button type="submit" disabled={!canSend} className="btn btn-primary">
            <Icon name="send" />
            {fr.explorer.send}
          </button>
        </div>
      </div>
      {history.length > 0 && <p className="hint">{fr.explorer.historyNote(history.length)}</p>}
    </form>
  );

  return (
    <main className="mx-auto max-w-4xl space-y-8 px-4 py-8 sm:px-6">
      <header className="space-y-4">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-4xl">
            {fr.explorer.title}
          </h1>
          {elections.length === 1 && <p className="badge">{election.label}</p>}
          <p className="max-w-prose text-lg text-muted">{fr.explorer.intro}</p>
        </div>
        <Notice variant="warn" data-testid="disclaimer">
          <p>{fr.explorer.disclaimer}</p>
        </Notice>
        <p className="flex max-w-prose items-start gap-2 text-sm text-muted">
          <span className="mt-0.5">
            <Icon name="info" size={16} />
          </span>
          {fr.explorer.privacy}
        </p>
      </header>

      {turns.length === 0 && composer}

      <AskSettings
        elections={elections}
        election={election}
        onElectionChange={(id) => {
          resetConversation();
          setExcluded(new Set());
          setTheme("");
          setElectionId(id);
        }}
        mode={mode}
        onModeChange={setMode}
        displays={displays}
        excluded={excluded}
        onExcludedChange={setExcluded}
        theme={theme}
        onThemeChange={setTheme}
        blind={blind}
        onBlindChange={setBlind}
      />

      <section aria-labelledby="conversation-title" className="space-y-8">
        <h2 id="conversation-title" className="sr-only">
          {fr.explorer.answer}
        </h2>
        {turns.map((t, i) => {
          const failure = t.failure ?? t.state.error;
          return (
            <article key={t.id} className="space-y-4" data-testid="turn">
              <div className="panel ml-auto max-w-prose space-y-1">
                <h3 className="eyebrow">{fr.explorer.you}</h3>
                <p className="break-words whitespace-pre-wrap">{t.question}</p>
              </div>
              <div aria-live="polite" aria-busy={t.streaming} className="space-y-4">
                {t.streaming && (
                  <p role="status" className="flex items-center gap-2 text-sm text-muted">
                    <span aria-hidden="true" className="inline-flex gap-1">
                      {["", "[animation-delay:200ms]", "[animation-delay:400ms]"].map((delay) => (
                        <span
                          key={delay}
                          className={`typing-dot inline-block h-1.5 w-1.5 rounded-full bg-current ${delay}`}
                        />
                      ))}
                    </span>
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
                {t.stopped && <p className="hint">{fr.explorer.stopped}</p>}
                {failure && (
                  <Notice variant="error" role="alert">
                    <p>{failure.message}</p>
                    {t.failure && MODE_ERRORS.has(t.failure.code) && i === turns.length - 1 && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm mt-1"
                        disabled={streaming}
                        onClick={() => {
                          setMode("rapide");
                          void send(t.question, "rapide");
                        }}
                      >
                        {fr.explorer.switchToFast}
                      </button>
                    )}
                  </Notice>
                )}
              </div>
            </article>
          );
        })}
      </section>

      {turns.length > 0 && composer}
    </main>
  );
}
