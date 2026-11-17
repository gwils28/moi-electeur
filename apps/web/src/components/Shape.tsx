import type { Shape } from "@/lib/present";

/** Marqueur de forme (information portée par la forme ET la couleur, pour le daltonisme). */
export function ShapeMark({
  shape,
  x,
  y,
  size = 7,
  color,
}: {
  shape: Shape;
  x: number;
  y: number;
  size?: number;
  color: string;
}) {
  const s = size;
  const common = { fill: color, stroke: "var(--fg)", strokeWidth: 1 };
  switch (shape) {
    case "circle":
      return <circle cx={x} cy={y} r={s} {...common} />;
    case "square":
      return <rect x={x - s} y={y - s} width={2 * s} height={2 * s} {...common} />;
    case "triangle":
      return (
        <polygon
          points={`${x},${y - s * 1.2} ${x - s * 1.1},${y + s} ${x + s * 1.1},${y + s}`}
          {...common}
        />
      );
    case "diamond":
      return (
        <polygon
          points={`${x},${y - s * 1.3} ${x + s * 1.3},${y} ${x},${y + s * 1.3} ${x - s * 1.3},${y}`}
          {...common}
        />
      );
    case "cross":
      return (
        <path
          d={`M${x - s},${y - s / 3}h${(2 * s) / 3}v${-(2 * s) / 3}h${(2 * s) / 3}v${(2 * s) / 3}h${(2 * s) / 3}v${(2 * s) / 3}h${-(2 * s) / 3}v${(2 * s) / 3}h${-(2 * s) / 3}v${-(2 * s) / 3}h${-(2 * s) / 3}z`}
          {...common}
        />
      );
    case "star": {
      const pts = Array.from({ length: 10 }, (_, i) => {
        const r = i % 2 === 0 ? s * 1.3 : s * 0.55;
        const a = (Math.PI / 5) * i - Math.PI / 2;
        return `${x + r * Math.cos(a)},${y + r * Math.sin(a)}`;
      }).join(" ");
      return <polygon points={pts} {...common} />;
    }
  }
}
