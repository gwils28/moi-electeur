import { describe, expect, it } from "vitest";
import { readDoc, renderMarkdown } from "../src/lib/markdown";

describe("documents publiés (méthodologie, accessibilité)", () => {
  it("rend titres, listes, tableaux et liens", () => {
    const html = renderMarkdown(
      "# Titre\n\n- a\n- b\n\n| x | y |\n|---|---|\n| 1 | 2 |\n\n<https://ex.org>",
    );
    expect(html).toContain("<h1>Titre</h1>");
    expect(html).toContain("<li>a</li>");
    expect(html).toContain("<table>");
    expect(html).toContain('href="https://ex.org"');
  });

  it("refuse le HTML brut du document (rendu en texte)", () => {
    expect(renderMarkdown("<script>alert(1)</script>")).not.toContain("<script>");
  });

  it("lit les documents du dépôt", () => {
    expect(readDoc("methodologie")).toContain("# Méthodologie");
    expect(readDoc("accessibilite")).toContain("RGAA");
  });
});
