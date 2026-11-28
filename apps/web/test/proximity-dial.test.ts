import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  ARC_LEN,
  dialDash,
  ProximityDial,
  type ProximityDialProps,
} from "../src/components/ProximityDial";

const render = (p: ProximityDialProps) => renderToStaticMarkup(createElement(ProximityDial, p));
const svgOf = (html: string) => /<svg[\s\S]*<\/svg>/.exec(html)![0];
const valueArc = (html: string) => /<circle data-part="value"[^>]*>/.exec(html)?.[0] ?? null;

describe("ProximityDial (spec de design 6.2)", () => {
  it("score 50 : arc de valeur à 108.38 sur 289.03", () => {
    const arc = valueArc(render({ score: 50, coverage: 0.5, low: false }));
    expect(arc).not.toBeNull();
    expect(arc).toMatch(/stroke-dasharray="108\.38/);
    expect(arc).toContain('stroke="var(--dial)"');
    expect(dialDash(0.5, ARC_LEN)).toBe("108.38 289.03");
    expect(dialDash(1, ARC_LEN)).toBe("216.77 289.03");
  });

  it("score null : piste seule, aucun arc de valeur", () => {
    const html = render({ score: null, coverage: null, low: false });
    expect(valueArc(html)).toBeNull();
    expect(html).not.toContain('data-part="coverage"');
  });

  it("couverture faible : arc hachuré par un motif", () => {
    const html = render({ score: 70, coverage: 0.3, low: true });
    const arc = valueArc(html)!;
    const id = /stroke="url\(#(hatch-[A-Za-z0-9_-]+)\)"/.exec(arc)?.[1];
    expect(id).toBeTruthy();
    expect(html).toContain(`<pattern id="${id}"`);
  });

  it("SVG décoratif sans texte ; score en HTML avec un espace normal", () => {
    const html = render({ score: 54.4, coverage: 0.8, low: false });
    const svg = svgOf(html);
    expect(svg).toContain('aria-hidden="true"');
    expect(svg).not.toContain("<text");
    // Texte lu (balises et commentaires de React retirés) : « 54 % » avec un espace normal,
    // même si le signe « % » a son propre élément pour la taille.
    const text = html
      .replace(svg, "")
      .replace(/<!--.*?-->/g, "")
      .replace(/<[^>]+>/g, "");
    expect(text).toContain("54 %");
    expect(html).toContain("Proximité : ");
  });

  it("encoche « Et si » seulement si le score a bougé", () => {
    expect(render({ score: 60, coverage: 1, low: false, previous: 50 })).toContain(
      'data-part="previous"',
    );
    expect(render({ score: 60, coverage: 1, low: false, previous: 60 })).not.toContain(
      'data-part="previous"',
    );
  });

  it("aucune couleur codée en dur (variables de thème seulement)", () => {
    const html = render({ score: 80, coverage: 0.9, low: true, previous: 40 });
    expect(html).not.toMatch(/#[0-9a-f]{3,6}\b(?!-)/i);
  });
});
