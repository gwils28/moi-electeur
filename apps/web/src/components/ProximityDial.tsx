import { useId } from "react";
// Import relatif : le composant est rendu tel quel par vitest (sans alias `@/`).
import { fr } from "../i18n/fr";

/**
 * Mini-cadran de proximité (spec de design, section 6.2) : une jauge par candidat, identique pour
 * tous, sans aiguille ni couleur de candidat. L'angle ne code que le score (0 à 100). Le SVG est
 * décoratif ; le score est écrit en HTML au centre (il suit la police et le zoom texte).
 */
export interface ProximityDialProps {
  /** 0..100, null = non calculable. */
  score: number | null;
  /** 0..1 */
  coverage: number | null;
  /** Couverture faible : arc hachuré (forme, pas couleur). */
  low: boolean;
  /** Score avant la dernière modification « Et si ». */
  previous?: number | null;
  /** Exemple de légende : petit format, sans texte central. */
  example?: boolean;
}

const C = 60;
const R_ARC = 46;
const R_COV = 33;
const OPEN = 0.75; // 270 degrés utiles, ouverture de 90 degrés en bas
const START = 135; // degrés, repère SVG (y vers le bas), sens horaire
export const ARC_LEN = 2 * Math.PI * R_ARC; // 289,03
export const COV_LEN = 2 * Math.PI * R_COV; // 207,35

const f = (v: number) => v.toFixed(2);
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const polar = (r: number, deg: number) => {
  const t = (deg * Math.PI) / 180;
  return { x: C + r * Math.cos(t), y: C + r * Math.sin(t) };
};

/** `stroke-dasharray` d'un arc de 270 degrés rempli à `fraction` (0..1). */
export function dialDash(fraction: number, circumference: number): string {
  return `${f(OPEN * circumference * clamp(fraction, 0, 1))} ${f(circumference)}`;
}

/** Repères aux quarts de l'échelle (0, 25, 50, 75, 100 %), rappel des quatre repères du logo. */
const TICKS = [0, 0.25, 0.5, 0.75, 1].map((q) => {
  const deg = START + 360 * OPEN * q;
  return { a: polar(53, deg), b: polar(57, deg) };
});

export function ProximityDial({ score, coverage, low, previous, example }: ProximityDialProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const hatch = `hatch-${uid}`;
  const rotate = `rotate(${START} ${C} ${C})`;
  const showPrev =
    score !== null && previous != null && Math.abs(score - previous) > 0.05 && !example;
  const prevDeg = START + 360 * OPEN * clamp((previous ?? 0) / 100, 0, 1);
  const p1 = polar(39, prevDeg);
  const p2 = polar(53, prevDeg);

  const svg = (
    <svg
      viewBox="0 0 120 120"
      aria-hidden="true"
      focusable="false"
      className={example ? "size-10 shrink-0" : "size-20 sm:size-24"}
    >
      {low && score !== null && (
        <defs>
          <pattern
            id={hatch}
            width="4"
            height="4"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="2" height="4" fill="var(--fg)" />
          </pattern>
        </defs>
      )}
      <circle
        cx={C}
        cy={C}
        r={R_ARC}
        fill="none"
        stroke="var(--track)"
        strokeWidth={10}
        strokeDasharray={dialDash(1, ARC_LEN)}
        transform={rotate}
      />
      {score !== null && (
        <circle
          data-part="value"
          className="dial-value"
          cx={C}
          cy={C}
          r={R_ARC}
          fill="none"
          stroke={low ? `url(#${hatch})` : "var(--fg)"}
          strokeWidth={10}
          strokeLinecap="butt"
          strokeDasharray={dialDash(score / 100, ARC_LEN)}
          transform={rotate}
        />
      )}
      <circle
        cx={C}
        cy={C}
        r={R_COV}
        fill="none"
        stroke="var(--track)"
        strokeWidth={3}
        strokeDasharray={dialDash(1, COV_LEN)}
        transform={rotate}
      />
      {coverage !== null && (
        <circle
          data-part="coverage"
          className="dial-value"
          cx={C}
          cy={C}
          r={R_COV}
          fill="none"
          stroke="var(--muted)"
          strokeWidth={3}
          strokeDasharray={dialDash(coverage, COV_LEN)}
          transform={rotate}
        />
      )}
      {TICKS.map((t, i) => (
        <line
          key={i}
          x1={f(t.a.x)}
          y1={f(t.a.y)}
          x2={f(t.b.x)}
          y2={f(t.b.y)}
          stroke="var(--muted)"
          strokeWidth={1.5}
        />
      ))}
      {showPrev && (
        <line
          data-part="previous"
          x1={f(p1.x)}
          y1={f(p1.y)}
          x2={f(p2.x)}
          y2={f(p2.y)}
          stroke="var(--fg)"
          strokeWidth={1.5}
          strokeDasharray="2 2"
        />
      )}
    </svg>
  );

  if (example) return svg;
  return (
    <div className="relative shrink-0">
      {svg}
      <span className="absolute inset-0 grid place-items-center leading-none">
        {score === null ? (
          <span aria-hidden="true" className="text-lg font-bold">
            -
          </span>
        ) : (
          <span className="text-base font-bold tracking-tight tabular-nums sm:text-lg">
            <span className="sr-only">{fr.proximity} : </span>
            {Math.round(score)}{" "}
            {/* Signe réduit pour rester dans l'anneau intérieur ; « NN % » reste lu d'un tenant. */}
            <span className="text-[0.625rem] font-semibold sm:text-xs">%</span>
          </span>
        )}
      </span>
    </div>
  );
}
