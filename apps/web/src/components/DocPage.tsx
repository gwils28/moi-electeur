import { readDoc, renderMarkdown, type DocName } from "@/lib/markdown";

/** Page tirée d'un document du dépôt (méthodologie, déclaration d'accessibilité). */
export function DocPage({ name }: { name: DocName }) {
  return (
    <main className="mx-auto max-w-3xl p-4 sm:p-6">
      <article
        className="doc"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(readDoc(name)) }}
      />
    </main>
  );
}
