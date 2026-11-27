// Explorateur (M2d) : lecture du flux SSE, mise en page de la réponse, mode aveugle, historique.
import type { AskCitationEvent, AskEvent, AskMetaEvent, Candidate } from "@moi-electeur/schemas-ts";
import { describe, expect, it } from "vitest";
import {
  applyEvent,
  answerText,
  EMPTY_ANSWER,
  layoutAnswer,
  pushHistory,
  toTurn,
  type AnswerState,
  type Layout,
} from "../src/lib/explorer/answer";
import { askStream, AskHttpError } from "../src/lib/explorer/client";
import { readSse, SseParser } from "../src/lib/explorer/sse";
import { encodeEvent } from "../src/lib/rag/sse";
import { citationView, displayCandidate, nameMasker } from "../src/lib/present";

const SILENCE = "Aucune proposition recensée dans le programme officiel sur ce point.";

const meta: AskMetaEvent = {
  type: "meta",
  election_id: "fr-2022",
  corpus_version: "v1",
  prompt_version: "1",
  model: "claude-haiku-5-5",
  mode: "rapide",
  cached: false,
  candidates: [
    { token: "c1", candidate_id: "bruno", has_excerpts: true },
    { token: "c2", candidate_id: "alice", has_excerpts: true },
    { token: "c3", candidate_id: "david", has_excerpts: false },
  ],
};

function cite(over: Partial<AskCitationEvent> = {}): AskCitationEvent {
  return {
    type: "citation",
    block: 1,
    verified: true,
    cited_text: "porté à 65 ans",
    chunk_id: "b-1",
    candidate_id: "bruno",
    document_title: "Profession de foi",
    source_url: "https://example.org/bruno.pdf",
    page_number: 3,
    page_end: null,
    ...over,
  };
}

const STREAM: AskEvent[] = [
  meta,
  { type: "delta", block: 0, text: "### {{c1}}\n\n" },
  cite(),
  { type: "delta", block: 1, text: "Le programme prévoit un départ " },
  { type: "delta", block: 1, text: "à 65 ans." },
  { type: "delta", block: 2, text: "\n\n### {{c2}}\n\n" },
  cite({ block: 3, candidate_id: "alice", chunk_id: "a-1", verified: false, page_number: 7 }),
  { type: "delta", block: 3, text: "Le programme vise 60 ans, comme {{c1}} le rappelle." },
  { type: "delta", block: 4, text: `\n\n### {{c3}}\n\n${SILENCE}\n` },
  { type: "done", stop_reason: "end_turn", unverified_citations: 1, neutrality_flags: [] },
];

const fold = (events: AskEvent[]): AnswerState => events.reduce(applyEvent, EMPTY_ANSWER);
const LABELS: Record<string, string> = { alice: "Alice A.", bruno: "Bruno B.", david: "David D." };
const labelOf = (id: string) => LABELS[id] ?? id;
const flat = (l: Layout, i: number) =>
  l.sections[i]!.paragraphs.flatMap((p) => p.inlines)
    .map((x) => (x.kind === "text" ? x.text : `[${x.n}]`))
    .join("");

describe("SseParser / readSse", () => {
  it("reconstitue les événements découpés n'importe où, ignore commentaires et inconnus", () => {
    const raw =
      ": commentaire\n\n" + STREAM.map(encodeEvent).join("") + "event: autre\ndata: {}\n\n";
    const p = new SseParser();
    const out: AskEvent[] = [];
    for (let i = 0; i < raw.length; i += 7) out.push(...p.push(raw.slice(i, i + 7)));
    expect(out).toEqual(STREAM);
  });

  it("CRLF coupé entre deux morceaux : pas de fausse fin d'événement", () => {
    const raw = encodeEvent(STREAM[1]!).replaceAll("\n", "\r\n");
    const p = new SseParser();
    const cut = raw.indexOf("\r") + 1;
    const out = [...p.push(raw.slice(0, cut)), ...p.push(raw.slice(cut))];
    expect(out).toEqual([STREAM[1]]);
  });

  it("lit un ReadableStream d'octets (UTF-8 coupé au milieu d'un caractère)", async () => {
    const bytes = new TextEncoder().encode(STREAM.map(encodeEvent).join(""));
    const body = new ReadableStream<Uint8Array>({
      start(c) {
        for (let i = 0; i < bytes.length; i += 5) c.enqueue(bytes.slice(i, i + 5));
        c.close();
      },
    });
    const out: AskEvent[] = [];
    for await (const ev of readSse(body)) out.push(ev);
    expect(out).toEqual(STREAM);
  });
});

describe("askStream", () => {
  it("POST JSON vers /api/ask et relaie les événements", async () => {
    const calls: { url: string; init: RequestInit }[] = [];
    const fetchImpl = async (url: string | URL | Request, init?: RequestInit) => {
      calls.push({ url: String(url), init: init! });
      return new Response(STREAM.map(encodeEvent).join(""), {
        headers: { "content-type": "text/event-stream" },
      });
    };
    const out: AskEvent[] = [];
    for await (const ev of askStream(
      { election_id: "fr-2022", question: "Retraites ?", mode: "rapide" },
      { fetchImpl },
    ))
      out.push(ev);
    expect(out).toEqual(STREAM);
    expect(calls[0]!.url).toBe("/api/ask");
    expect(calls[0]!.init.method).toBe("POST");
    expect(JSON.parse(String(calls[0]!.init.body))).toEqual({
      election_id: "fr-2022",
      question: "Retraites ?",
      mode: "rapide",
    });
  });

  it("réponse d'erreur JSON : AskHttpError avec code, message et statut", async () => {
    const fetchImpl = async () =>
      Response.json(
        { error: "mode_budget_exhausted", message: "Plafond atteint." },
        { status: 503 },
      );
    const run = async () => {
      for await (const _ of askStream({ election_id: "x", question: "q" }, { fetchImpl })) {
        /* vide */
      }
    };
    await expect(run()).rejects.toMatchObject({
      status: 503,
      code: "mode_budget_exhausted",
      message: "Plafond atteint.",
    });
    await expect(run()).rejects.toBeInstanceOf(AskHttpError);
  });

  it("erreur sans corps JSON : code générique", async () => {
    const fetchImpl = async () => new Response("<html>", { status: 502 });
    const it = askStream({ election_id: "x", question: "q" }, { fetchImpl });
    await expect(it.next()).rejects.toMatchObject({ status: 502, code: "network" });
  });
});

describe("applyEvent / answerText", () => {
  it("accumule le texte par bloc, garde les citations de chaque bloc", () => {
    const s = fold(STREAM);
    expect(s.meta).toEqual(meta);
    expect(s.done?.unverified_citations).toBe(1);
    expect(answerText(s)).toBe(
      "### {{c1}}\n\nLe programme prévoit un départ à 65 ans.\n\n### {{c2}}\n\n" +
        `Le programme vise 60 ans, comme {{c1}} le rappelle.\n\n### {{c3}}\n\n${SILENCE}\n`,
    );
    expect(s.blocks.find((b) => b.index === 1)!.citations).toHaveLength(1);
  });

  it("événement error : conservé, le texte déjà reçu reste", () => {
    const s = fold([
      ...STREAM.slice(0, 4),
      { type: "error", code: "llm_error", message: "La génération a échoué." },
    ]);
    expect(s.error).toEqual({ code: "llm_error", message: "La génération a échoué." });
    expect(answerText(s)).toContain("départ");
  });

  it("n'altère pas l'état précédent (immuable)", () => {
    const s1 = fold(STREAM.slice(0, 3));
    const before = JSON.stringify(s1);
    applyEvent(s1, STREAM[3]!);
    expect(JSON.stringify(s1)).toBe(before);
  });
});

describe("layoutAnswer", () => {
  it("une section par candidat, dans l'ordre de session (et non celui du serveur)", () => {
    const l = layoutAnswer(fold(STREAM), {
      order: ["david", "alice", "bruno"],
      labelOf,
      streaming: false,
    });
    expect(l.sections.map((s) => s.candidateId)).toEqual(["david", "alice", "bruno"]);
    expect(l.preamble).toEqual([]);
  });

  it("jetons {{cN}} de la prose remplacés par le libellé affiché, jamais laissés bruts", () => {
    const l = layoutAnswer(fold(STREAM), {
      order: ["bruno", "alice", "david"],
      labelOf,
      streaming: false,
    });
    expect(flat(l, 1)).toContain("comme Bruno B. le rappelle");
    expect(JSON.stringify(l)).not.toContain("{{c");
  });

  it("titre au jeton non numéroté ({{cN}}, défaut du modèle) retiré, jamais affiché", () => {
    const glitch: AskEvent[] = [
      ...STREAM.slice(0, 5),
      { type: "delta", block: 2, text: "\n\n### {{cN}}\n\n" },
      ...STREAM.slice(5),
    ];
    const l = layoutAnswer(fold(glitch), {
      order: ["bruno", "alice", "david"],
      labelOf,
      streaming: false,
    });
    expect(flat(l, 0)).toBe("Le programme prévoit un départ à 65 ans.[1]");
    expect(JSON.stringify(l)).not.toContain("{{");
  });

  it("citations numérotées dans l'ordre d'affichage, attachées au texte de leur bloc", () => {
    const l = layoutAnswer(fold(STREAM), {
      order: ["alice", "bruno", "david"],
      labelOf,
      streaming: false,
    });
    expect(flat(l, 0)).toBe("Le programme vise 60 ans, comme Bruno B. le rappelle.[1]");
    expect(flat(l, 1)).toBe("Le programme prévoit un départ à 65 ans.[2]");
    expect(l.citations.map((c) => c.chunk_id)).toEqual(["a-1", "b-1"]);
  });

  it("phrase de silence repérée (affichage distinct)", () => {
    const l = layoutAnswer(fold(STREAM), {
      order: ["bruno", "alice", "david"],
      labelOf,
      streaming: false,
    });
    const david = l.sections.find((s) => s.candidateId === "david")!;
    expect(david.paragraphs).toHaveLength(1);
    expect(david.paragraphs[0]!.silence).toBe(true);
    expect(l.sections[0]!.paragraphs[0]!.silence).toBe(false);
  });

  it("en cours de flux : un titre de section incomplet n'est pas affiché", () => {
    const partial = fold([...STREAM.slice(0, 5), { type: "delta", block: 2, text: "\n\n### {{c" }]);
    const l = layoutAnswer(partial, {
      order: ["bruno", "alice", "david"],
      labelOf,
      streaming: true,
    });
    expect(JSON.stringify(l)).not.toContain("#");
    expect(l.sections).toHaveLength(1);
  });

  it("titre de section juste après un bloc cité qui finit par un saut de ligne (relecture)", () => {
    const s = fold([
      meta,
      { type: "delta", block: 0, text: "### {{c1}}\n\n" },
      { type: "delta", block: 1, text: "Texte a.\n" },
      cite({ block: 1 }),
      { type: "delta", block: 2, text: "### {{c2}}\n\nTexte b." },
      cite({ block: 2, candidate_id: "alice", chunk_id: "a-1" }),
    ]);
    const l = layoutAnswer(s, { order: ["bruno", "alice"], labelOf, streaming: false });
    expect(l.sections.map((x) => x.candidateId)).toEqual(["bruno", "alice"]);
    expect(flat(l, 0)).toBe("Texte a.[1]");
    expect(flat(l, 1)).toBe("Texte b.[2]");
  });

  it("citation d'un bloc qui finit par un titre : conservée (aucune citation perdue)", () => {
    const s = fold([
      meta,
      { type: "delta", block: 0, text: "Préambule. ### {{c1}}" },
      { type: "delta", block: 1, text: "Intro.\n### {{c1}}" },
      cite({ block: 1 }),
      { type: "delta", block: 2, text: "\n\nTexte." },
    ]);
    const l = layoutAnswer(s, { order: ["bruno"], labelOf, streaming: false });
    expect(l.citations).toHaveLength(1);
  });

  it("listes à puces : un paragraphe par élément", () => {
    const s = fold([
      meta,
      { type: "delta", block: 0, text: "### {{c1}}\n\n- premier point\n- second point\n" },
    ]);
    const l = layoutAnswer(s, { order: ["bruno"], labelOf, streaming: false });
    expect(l.sections[0]!.paragraphs.map((p) => p.list)).toEqual([true, true]);
    expect(flat(l, 0)).toBe("premier pointsecond point");
  });

  it("masquage appliqué au texte (mode aveugle)", () => {
    const s = fold([
      meta,
      { type: "delta", block: 0, text: "### {{c1}}\n\nBruno Martin propose." },
    ]);
    const l = layoutAnswer(s, {
      order: ["bruno"],
      labelOf,
      mask: (t) => t.replace("Bruno Martin", "Candidat·e B"),
      streaming: false,
    });
    expect(flat(l, 0)).toBe("Candidat·e B propose.");
  });
});

describe("historique client", () => {
  it("tour : question, texte avec jetons, candidats dans l'ordre des jetons", () => {
    const turn = toTurn("Retraites ?", fold(STREAM))!;
    expect(turn.question).toBe("Retraites ?");
    expect(turn.answer).toContain("### {{c1}}");
    expect(turn.candidates).toEqual(["bruno", "alice", "david"]);
  });

  it("pas de tour pour une réponse en erreur, incomplète ou vide", () => {
    expect(toTurn("q", fold(STREAM.slice(0, 4)))).toBeNull();
    expect(
      toTurn(
        "q",
        fold([...STREAM.slice(0, 4), { type: "error", code: "llm_error", message: "x" }]),
      ),
    ).toBeNull();
    expect(toTurn("q", fold([meta, STREAM.at(-1)!]))).toBeNull();
  });

  it("pas de tour pour une réponse arrêtée par max_tokens ou refusée", () => {
    const cut: AskEvent = {
      type: "done",
      stop_reason: "max_tokens",
      unverified_citations: 0,
      neutrality_flags: [],
    };
    expect(toTurn("q", fold([...STREAM.slice(0, -1), cut]))).toBeNull();
  });

  it("troncature : jamais un jeton {{cN}} coupé en deux", () => {
    const long = fold([
      meta,
      { type: "delta", block: 0, text: "x".repeat(19_995) + "{{c12}} suite" },
      STREAM.at(-1)!,
    ]);
    expect(toTurn("q", long)!.answer).toBe("x".repeat(19_995));
  });

  it("réponse tronquée à 20 000 caractères (limite du schéma)", () => {
    const long = fold([
      meta,
      { type: "delta", block: 0, text: "x".repeat(25_000) },
      STREAM.at(-1)!,
    ]);
    expect(toTurn("q", long)!.answer).toHaveLength(20_000);
  });

  it("trois tours au plus, les plus récents", () => {
    const t = (q: string) => ({ question: q, answer: "a", candidates: ["x"] });
    let h = pushHistory([], t("1"));
    for (const q of ["2", "3", "4"]) h = pushHistory(h, t(q));
    expect(h.map((x) => x.question)).toEqual(["2", "3", "4"]);
  });
});

const candidate = (over: Partial<Candidate> = {}): Candidate => ({
  id: "bruno",
  name: "Bruno Martin-Durand",
  party: "Parti B",
  color: "#123456",
  photo: null,
  program_url: "https://example.org/b",
  blind_alias: "Candidat·e B",
  ...over,
});

describe("citationView", () => {
  it("mode normal : titre, page, lien vers la page du PDF, extrait", () => {
    const v = citationView(cite({ page_end: 4 }), displayCandidate(candidate(), 0, false), false);
    expect(v).toEqual({
      source: "Profession de foi",
      page: "p. 3-4",
      href: "https://example.org/bruno.pdf#page=3",
      quote: "porté à 65 ans",
      verified: true,
    });
  });

  it("mode aveugle : ni titre, ni lien, ni extrait (ils pourraient révéler le candidat)", () => {
    const v = citationView(cite(), displayCandidate(candidate(), 0, true), true);
    expect(v).toEqual({
      source: "Programme",
      page: "p. 3",
      href: null,
      quote: null,
      verified: true,
    });
  });

  it("mode aveugle, citation sans candidat connu : extrait masqué aussi (relecture)", () => {
    const v = citationView(cite({ candidate_id: null }), undefined, true);
    expect(v.quote).toBeNull();
    expect(v.href).toBeNull();
  });

  it("lien non http(s) refusé ; citation sans métadonnée", () => {
    const d = displayCandidate(candidate(), 0, false);
    expect(citationView(cite({ source_url: "javascript:alert(1)" }), d, false).href).toBeNull();
    const none = citationView(
      cite({
        verified: false,
        chunk_id: null,
        candidate_id: null,
        document_title: null,
        source_url: null,
        page_number: null,
      }),
      undefined,
      false,
    );
    expect(none).toMatchObject({ page: null, href: null, verified: false });
    expect(none.source.length).toBeGreaterThan(0);
  });
});

describe("nameMasker (mode aveugle)", () => {
  const cands = [
    candidate(),
    candidate({ id: "anne", name: "Anne Le Gall", blind_alias: "Candidat·e A" }),
  ];
  const mask = nameMasker(cands, (id) => (id === "anne" ? "Candidat·e A" : "Candidat·e B"));

  it("nom complet et nom de famille remplacés, casse et accents compris", () => {
    expect(mask("Bruno Martin-Durand et Anne Le Gall")).toBe("Candidat·e B et Candidat·e A");
    expect(mask("selon martin-durand, comme LE GALL")).toBe(
      "selon Candidat·e B, comme Candidat·e A",
    );
  });

  it("ne remplace pas un mot qui contient le nom", () => {
    expect(mask("Le Gallois et Martin-Durandes")).toBe("Le Gallois et Martin-Durandes");
  });
});
