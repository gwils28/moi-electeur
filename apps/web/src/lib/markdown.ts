import { readFileSync } from "node:fs";
import { join } from "node:path";
import { Marked } from "marked";

/** Documents du dépôt publiés comme pages (`docs/<nom>.md`, source unique, PLAN D47). */
export type DocName = "methodologie" | "accessibilite";

const DOCS_DIR = join(process.cwd(), "..", "..", "docs");

const escapeHtml = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// HTML brut du document rendu en texte : seules les constructions Markdown produisent du HTML.
const marked = new Marked({
  gfm: true,
  renderer: {
    html({ text }) {
      return escapeHtml(text);
    },
  },
});

export function renderMarkdown(source: string): string {
  return marked.parse(source, { async: false });
}

const cache = new Map<DocName, string>();

/** Texte du document, lu une fois par processus. */
export function readDoc(name: DocName): string {
  let text = cache.get(name);
  if (text === undefined) {
    text = readFileSync(join(DOCS_DIR, `${name}.md`), "utf-8");
    cache.set(name, text);
  }
  return text;
}
