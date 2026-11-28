"use client";

import type { ElectionConfig } from "@moi-electeur/schemas-ts";
import { scaleLinear } from "d3-scale";
import { layoutLabels, wrapLabel } from "@/lib/chessboard";
import type { CandidateDisplay } from "@/lib/present";
import { fr } from "@/i18n/fr";

export interface PlottedCandidate {
  display: CandidateDisplay;
  x: number | null;
  y: number | null;
}

interface Props {
  config: ElectionConfig;
  candidates: readonly PlottedCandidate[];
  user: { x: number | null; y: number | null };
  previousUser: { x: number | null; y: number | null } | null;
  axisLabels: { x: [string, string]; y: [string, string] };
  showQuadrants: boolean;
  onSelect: (id: string) => void;
}

// viewBox 560 x 480 : cadre carré de 336, marges latérales pour les libellés de l'axe x (deux ou
// trois lignes) et marges hautes et basses pour les libellés de quadrants et de l'axe y.
const W = 560;
const MX = 112;
const MY = 72;
const PLOT = W - 2 * MX;
const H = PLOT + 2 * MY;
const LINE = 12;
/** Halo sous les textes : lisibles même au-dessus d'un point ou d'un cercle. */
const HALO = {
  paintOrder: "stroke",
  stroke: "var(--surface)",
  strokeWidth: 3,
  strokeLinejoin: "round",
} as const;

/** Échiquier 2D (SPEC § 5.4). Une alternative accessible (tableau) est toujours affichée à côté. */
export function Chessboard(p: Props) {
  const sx = scaleLinear()
    .domain([-10, 10])
    .range([MX, W - MX]);
  const sy = scaleLinear()
    .domain([-10, 10])
    .range([H - MY, MY]);
  const ux = p.user.x ?? 0;
  const uy = p.user.y ?? 0;
  const hasUser = p.user.x !== null && p.user.y !== null;
  const q = p.config.quadrants;
  const plotted = p.candidates.flatMap((c) =>
    c.x === null || c.y === null ? [] : [{ c, x: c.x, y: c.y }],
  );
  const labels = layoutLabels(
    plotted.map(({ c, x, y }) => ({
      id: c.display.id,
      px: sx(x),
      py: sy(y),
      side: x > 4 ? ("left" as const) : ("right" as const),
    })),
  );
  const xLines = (text: string) => wrapLabel(text, 17);
  const block = (lines: string[], x: number, anchor: "start" | "end") => (
    <text x={x} y={sy(0) - ((lines.length - 1) * LINE) / 2 + 3} textAnchor={anchor} {...HALO}>
      {lines.map((l, i) => (
        <tspan key={i} x={x} dy={i === 0 ? 0 : LINE}>
          {l}
        </tspan>
      ))}
    </text>
  );

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="mx-auto w-full max-w-[560px]"
      role="group"
      aria-label={fr.chessboardLabel}
    >
      <rect
        x={MX}
        y={MY}
        width={PLOT}
        height={PLOT}
        fill="var(--surface)"
        stroke="var(--line-strong)"
      />
      <line x1={sx(0)} x2={sx(0)} y1={MY} y2={H - MY} stroke="var(--line-strong)" opacity={0.6} />
      <line x1={MX} x2={W - MX} y1={sy(0)} y2={sy(0)} stroke="var(--line-strong)" opacity={0.6} />
      {p.showQuadrants && (
        <g fontSize={10} fontStyle="italic" fill="var(--muted)">
          <text x={MX} y={MY - 10} {...HALO}>
            {q.tl}
          </text>
          <text x={W - MX} y={MY - 10} textAnchor="end" {...HALO}>
            {q.tr}
          </text>
          <text x={MX} y={H - MY + 18} {...HALO}>
            {q.bl}
          </text>
          <text x={W - MX} y={H - MY + 18} textAnchor="end" {...HALO}>
            {q.br}
          </text>
        </g>
      )}
      <g fontSize={10} fill="currentColor">
        {block(xLines(p.axisLabels.x[0]), MX - 8, "end")}
        {block(xLines(p.axisLabels.x[1]), W - MX + 8, "start")}
        <text x={sx(0)} y={MY - 34} textAnchor="middle" {...HALO}>
          ↑ {p.axisLabels.y[1]}
        </text>
        <text x={sx(0)} y={H - MY + 42} textAnchor="middle" {...HALO}>
          ↓ {p.axisLabels.y[0]}
        </text>
      </g>

      {hasUser &&
        [2.5, 5, 7.5].map((r) => (
          <ellipse
            key={r}
            className="moved"
            cx={sx(ux)}
            cy={sy(uy)}
            rx={sx(r) - sx(0)}
            ry={sy(0) - sy(r)}
            fill="none"
            stroke="var(--muted)"
            strokeDasharray="3 4"
            opacity={0.6}
          />
        ))}

      {plotted.map(({ c, x, y }, i) => {
        const l = labels[i]!;
        const cx = sx(x);
        const cy = sy(y);
        return (
          <g
            key={c.display.id}
            role="button"
            tabIndex={0}
            aria-label={c.display.label}
            className="group cursor-pointer outline-none"
            onClick={() => p.onSelect(c.display.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                p.onSelect(c.display.id);
              }
            }}
          >
            <circle cx={cx} cy={cy} r={14} fill="transparent" />
            <circle
              cx={cx}
              cy={cy}
              r={16}
              fill="none"
              stroke="var(--accent)"
              strokeWidth={3}
              className="opacity-0 group-focus-visible:opacity-100"
            />
            {l.leader && (
              <line
                x1={l.leader.x1}
                y1={l.leader.y1}
                x2={l.leader.x2}
                y2={l.leader.y2}
                stroke="var(--muted)"
                strokeWidth={0.75}
              />
            )}
            {/* Même point neutre pour tous (PLAN D58) : le nom, toujours affiché, identifie. */}
            <circle
              cx={cx}
              cy={cy}
              r={5.5}
              fill="var(--surface)"
              stroke="var(--fg)"
              strokeWidth={2}
            />
            <text
              x={l.x}
              y={l.y}
              textAnchor={l.anchor}
              fontSize={11}
              fill="currentColor"
              className="group-hover:underline"
              {...HALO}
            >
              {c.display.label}
            </text>
          </g>
        );
      })}

      {hasUser && p.previousUser && p.previousUser.x !== null && p.previousUser.y !== null && (
        <line
          data-testid="whatif-trace"
          x1={sx(p.previousUser.x)}
          y1={sy(p.previousUser.y)}
          x2={sx(ux)}
          y2={sy(uy)}
          stroke="currentColor"
          strokeWidth={2}
          strokeDasharray="5 3"
          markerEnd="url(#arrow)"
        />
      )}
      <defs>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto"
        >
          <path d="M0,0L10,5L0,10z" fill="currentColor" />
        </marker>
      </defs>
      {hasUser && (
        <g
          className="moved"
          style={{ transform: `translate(${sx(ux)}px, ${sy(uy)}px)` }}
          data-testid="user-point"
        >
          <circle r={9} fill="var(--surface)" stroke="currentColor" strokeWidth={3} />
          <circle r={3} fill="currentColor" />
          <text x={12} y={-10} fontSize={12} fontWeight={700} fill="currentColor" {...HALO}>
            {fr.you}
          </text>
        </g>
      )}
    </svg>
  );
}
