import type {
  AskCitationEvent,
  AskDoneEvent,
  AskEvent,
  AskMetaEvent,
  AskTurn,
} from "@moi-electeur/schemas-ts";

/** Phrase imposée par le prompt quand le programme ne dit rien (prompts/rag_system.md). */
export const SILENCE = "Aucune proposition recensée dans le programme officiel sur ce point.";

/** Tours d'historique renvoyés au serveur (ask_request.schema.json). */
export const MAX_TURNS = 3;
const MAX_ANSWER_CHARS = 20_000;

export interface AnswerBlock {
  readonly index: number;
  readonly text: string;
  readonly citations: readonly AskCitationEvent[];
}

/** Réponse en cours ou terminée, reconstruite à partir des événements du flux. */
export interface AnswerState {
  readonly meta: AskMetaEvent | null;
  readonly blocks: readonly AnswerBlock[];
  readonly done: AskDoneEvent | null;
  readonly error: { readonly code: string; readonly message: string } | null;
}

export const EMPTY_ANSWER: AnswerState = { meta: null, blocks: [], done: null, error: null };

function withBlock(
  blocks: readonly AnswerBlock[],
  index: number,
  f: (b: AnswerBlock) => AnswerBlock,
): AnswerBlock[] {
  const found = blocks.some((b) => b.index === index);
  const all = found ? [...blocks] : [...blocks, { index, text: "", citations: [] }];
  return all.map((b) => (b.index === index ? f(b) : b)).sort((a, b) => a.index - b.index);
}

/** Applique un événement du flux (sans modifier l'état reçu). */
export function applyEvent(s: AnswerState, ev: AskEvent): AnswerState {
  switch (ev.type) {
    case "meta":
      return { ...s, meta: ev };
    case "delta":
      return {
        ...s,
        blocks: withBlock(s.blocks, ev.block, (b) => ({ ...b, text: b.text + ev.text })),
      };
    case "citation":
      return {
        ...s,
        blocks: withBlock(s.blocks, ev.block, (b) => ({ ...b, citations: [...b.citations, ev] })),
      };
    case "done":
      return { ...s, done: ev };
    case "error":
      return { ...s, error: { code: ev.code, message: ev.message } };
  }
}

/** Texte brut de la réponse, avec les jetons {{cN}} (forme renvoyée dans l'historique). */
export function answerText(s: AnswerState): string {
  return s.blocks.map((b) => b.text).join("");
}

/** Tour d'historique d'une réponse complète, sinon null (erreur, flux interrompu, vide). */
export function toTurn(question: string, s: AnswerState): AskTurn | null {
  const text = answerText(s);
  // Réponse complète seulement : une réponse tronquée ou refusée ne sert pas de contexte.
  if (!s.meta || s.done?.stop_reason !== "end_turn" || s.error || text.trim() === "") return null;
  return {
    question,
    answer: truncate(text, MAX_ANSWER_CHARS),
    candidates: s.meta.candidates.map((c) => c.candidate_id),
  };
}

/** Coupe à `max` caractères sans couper un jeton `{{cN}}` ni une paire de substitution. */
function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  let t = text.slice(0, max);
  if (/[\uD800-\uDBFF]$/.test(t)) t = t.slice(0, -1);
  return t.replace(/\{(\{(c\d*(\}?)?)?)?$/, "");
}

export function pushHistory(history: readonly AskTurn[], turn: AskTurn): AskTurn[] {
  return [...history, turn].slice(-MAX_TURNS);
}

export type Inline =
  | { readonly kind: "text"; readonly text: string }
  | { readonly kind: "cite"; readonly n: number; readonly citation: AskCitationEvent };

export interface Paragraph {
  readonly inlines: readonly Inline[];
  /** Phrase de silence du programme : affichage distinct. */
  readonly silence: boolean;
  /** Élément de liste à puces. */
  readonly list: boolean;
}

export interface Section {
  readonly token: string | null;
  readonly candidateId: string | null;
  readonly paragraphs: readonly Paragraph[];
}

export interface Layout {
  readonly preamble: readonly Paragraph[];
  readonly sections: readonly Section[];
  /** Citations dans l'ordre d'affichage : la n-ième porte le numéro n. */
  readonly citations: readonly AskCitationEvent[];
}

// Repère d'une citation dans le texte assemblé (caractère à usage privé, retiré du texte reçu).
const MARK = "\uE000";
const MARK_RE = /\uE000(\d+)\uE000/g;
const HEADING = /^[ \t]*#{1,6}[ \t]*\{\{(c\d+)\}\}[^\n]*$/gm;
const TOKEN = /\{\{(c\d+)\}\}/g;

/**
 * Mise en page d'une réponse : une section par candidat (`### {{cN}}`), **dans l'ordre de session
 * du navigateur** (`order`) et non dans celui du serveur, ce qui vaut aussi pour une réponse
 * rejouée depuis le cache ; jetons remplacés par le libellé affiché (nom ou alias) ; `mask`
 * appliqué au texte (mode aveugle) ; citations numérotées dans l'ordre d'affichage.
 */
export function layoutAnswer(
  s: AnswerState,
  opts: {
    order: readonly string[];
    labelOf: (candidateId: string) => string;
    mask?: (text: string) => string;
    streaming: boolean;
  },
): Layout {
  const tokenToId = new Map((s.meta?.candidates ?? []).map((c) => [c.token, c.candidate_id]));
  const pool: AskCitationEvent[] = [];
  let text = "";
  for (const b of s.blocks) {
    // Repères placés avant les blancs de fin du bloc : un titre `### {{cN}}` au début du bloc
    // suivant reste en tête de ligne.
    const body = b.text.replaceAll(MARK, "");
    const trimmed = body.trimEnd();
    const marks = b.citations.map((c) => `${MARK}${pool.push(c) - 1}${MARK}`).join("");
    text += trimmed + marks + body.slice(trimmed.length);
  }
  if (opts.streaming) {
    // Dernière ligne encore incomplète qui commence un titre : affichée une fois terminée.
    const cut = text.lastIndexOf("\n") + 1;
    if (text.slice(cut).trimStart().startsWith("#")) text = text.slice(0, cut);
  }

  const label = (token: string) => {
    const id = tokenToId.get(token);
    return id ? opts.labelOf(id) : "[candidat]";
  };
  const render = (raw: string) => {
    const t = raw.replace(TOKEN, (_, tok: string) => label(tok));
    return opts.mask ? opts.mask(t) : t;
  };

  const parts: { token: string | null; body: string }[] = [];
  let last = 0;
  let token: string | null = null;
  for (const m of text.matchAll(HEADING)) {
    // Repères tombés sur une ligne de titre : rattachés à la fin de la partie précédente.
    const marks = m[0].match(MARK_RE)?.join("") ?? "";
    parts.push({ token, body: text.slice(last, m.index).trimEnd() + marks });
    token = m[1]!;
    last = m.index + m[0].length;
  }
  parts.push({ token, body: text.slice(last) });

  const toParagraphs = (body: string): Paragraph[] => {
    const out: { inlines: Inline[]; silence: boolean; list: boolean }[] = [];
    for (const chunk of body.split(/\n[ \t]*\n/)) {
      const lines = chunk.split("\n").filter((l) => l.trim() !== "");
      if (lines.length === 0) continue;
      const isList = lines.every((l) => /^\s*[-*•]\s+/.test(l));
      const items = isList
        ? lines.map((l) => l.replace(/^\s*[-*•]\s+/, ""))
        : [lines.map((l) => l.trim()).join(" ")];
      for (const item of items) {
        const inlines: Inline[] = [];
        let pos = 0;
        for (const m of item.matchAll(MARK_RE)) {
          const before = item.slice(pos, m.index);
          if (before) inlines.push({ kind: "text", text: before });
          inlines.push({ kind: "cite", n: 0, citation: pool[Number(m[1])]! });
          pos = m.index + m[0].length;
        }
        if (pos < item.length) inlines.push({ kind: "text", text: item.slice(pos) });
        const plain = inlines
          .map((x) => (x.kind === "text" ? x.text : ""))
          .join("")
          .replace(/\*\*|__/g, "")
          .trim();
        // Paragraphe réduit à des citations : rattachées au paragraphe précédent.
        if (plain === "" && out.length > 0) {
          out.at(-1)!.inlines.push(...inlines.filter((x) => x.kind === "cite"));
          continue;
        }
        if (plain === "") {
          // Repères seuls en tête de partie : gardés (aucune citation perdue).
          const cites = inlines.filter((x) => x.kind === "cite");
          if (cites.length > 0) out.push({ inlines: cites, silence: false, list: false });
          continue;
        }
        const rendered = inlines.map((x) =>
          x.kind === "text"
            ? { kind: "text" as const, text: render(x.text.replace(/\*\*|__/g, "")) }
            : x,
        );
        // Espaces de bord retirés, une fois les repères de citation séparés.
        const first = rendered[0];
        if (first?.kind === "text") rendered[0] = { kind: "text", text: first.text.trimStart() };
        let lastText = -1;
        rendered.forEach((x, k) => {
          if (x.kind === "text") lastText = k;
        });
        if (lastText !== -1) {
          const lt = rendered[lastText] as { kind: "text"; text: string };
          rendered[lastText] = { kind: "text", text: lt.text.trimEnd() };
        }
        out.push({ inlines: rendered, silence: plain === SILENCE, list: isList });
      }
    }
    return out;
  };

  const [head, ...rest] = parts;
  const rank = new Map(opts.order.map((id, i) => [id, i]));
  const sections = rest
    .map((p, i) => {
      const candidateId = p.token ? (tokenToId.get(p.token) ?? null) : null;
      return { token: p.token, candidateId, paragraphs: toParagraphs(p.body), i };
    })
    .sort((a, b) => {
      const ra = a.candidateId !== null ? (rank.get(a.candidateId) ?? Infinity) : Infinity;
      const rb = b.candidateId !== null ? (rank.get(b.candidateId) ?? Infinity) : Infinity;
      return ra === rb ? a.i - b.i : ra - rb;
    })
    .map(({ token, candidateId, paragraphs }) => ({ token, candidateId, paragraphs }));
  const preamble = toParagraphs(head!.body);

  // Numérotation dans l'ordre d'affichage.
  const citations: AskCitationEvent[] = [];
  const number = (ps: Paragraph[]): Paragraph[] =>
    ps.map((p) => ({
      ...p,
      inlines: p.inlines.map((x) =>
        x.kind === "cite" ? { ...x, n: citations.push(x.citation) } : x,
      ),
    }));
  const numberedPreamble = number(preamble);
  const numberedSections = sections.map((sec) => ({
    ...sec,
    paragraphs: number([...sec.paragraphs]),
  }));
  return { preamble: numberedPreamble, sections: numberedSections, citations };
}
