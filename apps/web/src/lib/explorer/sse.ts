import type { AskEvent } from "@moi-electeur/schemas-ts";

const TYPES = new Set(["meta", "delta", "citation", "done", "error"]);

/**
 * Lecteur SSE incrémental pour le flux de /api/ask : accepte des morceaux de texte coupés
 * n'importe où et renvoie les événements complets. Commentaires et types inconnus ignorés.
 */
export class SseParser {
  private buffer = "";
  /** `\r` en fin de morceau : peut-être la première moitié d'un `\r\n`. */
  private pendingCr = false;

  push(chunk: string): AskEvent[] {
    let text = (this.pendingCr ? "\r" : "") + chunk;
    this.pendingCr = text.endsWith("\r");
    if (this.pendingCr) text = text.slice(0, -1);
    this.buffer += text.replace(/\r\n?/g, "\n");
    const out: AskEvent[] = [];
    let end: number;
    while ((end = this.buffer.indexOf("\n\n")) !== -1) {
      const raw = this.buffer.slice(0, end);
      this.buffer = this.buffer.slice(end + 2);
      const ev = parseEvent(raw);
      if (ev) out.push(ev);
    }
    return out;
  }
}

function parseEvent(raw: string): AskEvent | null {
  let type = "message";
  const data: string[] = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith(":")) continue;
    const i = line.indexOf(":");
    const field = i === -1 ? line : line.slice(0, i);
    const value = i === -1 ? "" : line.slice(i + 1).replace(/^ /, "");
    if (field === "event") type = value;
    else if (field === "data") data.push(value);
  }
  if (!TYPES.has(type) || data.length === 0) return null;
  try {
    const ev = JSON.parse(data.join("\n")) as AskEvent;
    return ev.type === type ? ev : null;
  } catch {
    return null;
  }
}

/** Événements d'un corps de réponse SSE (UTF-8 décodé en flux). */
export async function* readSse(body: ReadableStream<Uint8Array>): AsyncGenerator<AskEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  const parser = new SseParser();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      yield* parser.push(decoder.decode(value, { stream: true }));
    }
    yield* parser.push(decoder.decode() + "\n\n");
  } finally {
    reader.releaseLock();
  }
}
