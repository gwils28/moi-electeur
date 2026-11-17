"use client";

import type { ElectionConfig } from "@moi-electeur/schemas-ts";
import { scaleLinear } from "d3-scale";
import type { CandidateDisplay } from "@/lib/present";
import { fr } from "@/i18n/fr";
import { ShapeMark } from "./Shape";

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

const SIZE = 440;
const M = 56;

/** Échiquier 2D (SPEC § 5.4). Une alternative accessible (tableau) est toujours affichée à côté. */
export function Chessboard(p: Props) {
  const sx = scaleLinear()
    .domain([-10, 10])
    .range([M, SIZE - M]);
  const sy = scaleLinear()
    .domain([-10, 10])
    .range([SIZE - M, M]);
  const ux = p.user.x ?? 0;
  const uy = p.user.y ?? 0;
  const hasUser = p.user.x !== null && p.user.y !== null;
  const q = p.config.quadrants;

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="w-full max-w-[560px]"
      role="group"
      aria-label={fr.chessboardLabel}
    >
      <rect
        x={M}
        y={M}
        width={SIZE - 2 * M}
        height={SIZE - 2 * M}
        fill="none"
        stroke="currentColor"
        opacity={0.4}
      />
      <line x1={sx(0)} x2={sx(0)} y1={M} y2={SIZE - M} stroke="currentColor" opacity={0.4} />
      <line x1={M} x2={SIZE - M} y1={sy(0)} y2={sy(0)} stroke="currentColor" opacity={0.4} />
      {p.showQuadrants && (
        <g fontSize={10} opacity={0.75} fill="currentColor">
          <text x={M + 4} y={M + 14}>
            {q.tl}
          </text>
          <text x={SIZE - M - 4} y={M + 14} textAnchor="end">
            {q.tr}
          </text>
          <text x={M + 4} y={SIZE - M - 6}>
            {q.bl}
          </text>
          <text x={SIZE - M - 4} y={SIZE - M - 6} textAnchor="end">
            {q.br}
          </text>
        </g>
      )}
      <g fontSize={10} fill="currentColor">
        <text x={M} y={SIZE - M + 16}>
          ← {p.axisLabels.x[0]}
        </text>
        <text x={SIZE - M} y={SIZE - M + 30} textAnchor="end">
          {p.axisLabels.x[1]} →
        </text>
        <text x={sx(0)} y={M - 10} textAnchor="middle">
          ↑ {p.axisLabels.y[1]}
        </text>
        <text x={sx(0)} y={SIZE - M + 46} textAnchor="middle">
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
            stroke="currentColor"
            strokeDasharray="3 4"
            opacity={0.35}
          />
        ))}

      {p.candidates.map((c) =>
        c.x === null || c.y === null ? null : (
          <g
            key={c.display.id}
            role="button"
            tabIndex={0}
            aria-label={c.display.label}
            className="cursor-pointer focus:outline-2"
            onClick={() => p.onSelect(c.display.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                p.onSelect(c.display.id);
              }
            }}
          >
            <ShapeMark shape={c.display.shape} x={sx(c.x)} y={sy(c.y)} color={c.display.color} />
            <text
              x={c.x > 4 ? sx(c.x) - 10 : sx(c.x) + 10}
              y={sy(c.y) + 4}
              textAnchor={c.x > 4 ? "end" : "start"}
              fontSize={11}
              fill="currentColor"
            >
              {c.display.label}
            </text>
          </g>
        ),
      )}

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
          <circle r={9} fill="var(--bg)" stroke="currentColor" strokeWidth={3} />
          <circle r={3} fill="currentColor" />
          <text x={12} y={-10} fontSize={12} fontWeight={700} fill="currentColor">
            {fr.you}
          </text>
        </g>
      )}
    </svg>
  );
}
