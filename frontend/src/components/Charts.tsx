// Графики на SVG: объём по неделям и динамика силы

import { formatDay } from "../lib/dates";
import { formatNumber } from "../lib/format";

const WIDTH = 640;
const HEIGHT = 200;
const PAD_LEFT = 56;
const PAD_BOTTOM = 26;
const PAD_TOP = 12;

function niceMax(value: number): number {
  if (value <= 0) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 2.5, 5, 10].find((candidate) => candidate * power >= value) ?? 10;
  return step * power;
}

function Gridlines({ max, min = 0 }: { max: number; min?: number }) {
  const plotHeight = HEIGHT - PAD_BOTTOM - PAD_TOP;

  return (
    <g className="chart-grid">
      {[0, 0.5, 1].map((part) => {
        const y = PAD_TOP + plotHeight * (1 - part);
        return (
          <g key={part}>
            <line x1={PAD_LEFT} x2={WIDTH} y1={y} y2={y} />
            <text x={PAD_LEFT - 6} y={y + 4} textAnchor="end">
              {formatNumber(Math.round((min + (max - min) * part) * 10) / 10)}
            </text>
          </g>
        );
      })}
    </g>
  );
}

export function BarChart({
  items,
}: {
  items: { label: string; value: number; title: string }[];
}) {
  const max = niceMax(Math.max(...items.map((item) => item.value), 0));
  const plotWidth = WIDTH - PAD_LEFT;
  const plotHeight = HEIGHT - PAD_BOTTOM - PAD_TOP;
  const slot = plotWidth / Math.max(items.length, 1);
  const barWidth = Math.min(28, slot * 0.6);

  return (
    <svg className="chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img">
      <Gridlines max={max} />
      {items.map((item, index) => {
        const height = (item.value / max) * plotHeight;
        const x = PAD_LEFT + slot * index + (slot - barWidth) / 2;
        const showLabel = items.length <= 12 || index % 2 === items.length % 2;

        return (
          <g key={item.label}>
            <rect
              className={`chart-bar ${index === items.length - 1 ? "current" : ""}`}
              x={x}
              y={PAD_TOP + plotHeight - height}
              width={barWidth}
              height={Math.max(height, item.value > 0 ? 2 : 0)}
              rx={3}
            >
              <title>{item.title}</title>
            </rect>
            {showLabel && (
              <text
                className="chart-label"
                x={x + barWidth / 2}
                y={HEIGHT - 8}
                textAnchor="middle"
              >
                {item.label}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

export function TrendChart({
  points,
  unit,
  fromZero = true,
  highlightBest = true,
}: {
  points: { date: string; value: number }[];
  unit: string;
  // false — шкала по диапазону значений (для веса тела: 78–82 кг)
  fromZero?: boolean;
  highlightBest?: boolean;
}) {
  if (points.length === 0) return null;

  const values = points.map((point) => point.value);
  const top = Math.max(...values);
  const bottom = Math.min(...values);
  // Для веса тела шкала по диапазону с запасом, иначе — от нуля
  const min = fromZero ? 0 : Math.floor(bottom - Math.max(1, (top - bottom) * 0.3));
  const max = fromZero ? niceMax(top) : Math.ceil(top + Math.max(1, (top - bottom) * 0.3));
  const plotWidth = WIDTH - PAD_LEFT - 12;
  const plotHeight = HEIGHT - PAD_BOTTOM - PAD_TOP;

  const coords = points.map((point, index) => ({
    ...point,
    x: PAD_LEFT + (points.length === 1 ? plotWidth / 2 : (plotWidth * index) / (points.length - 1)),
    y: PAD_TOP + plotHeight * (1 - (point.value - min) / (max - min)),
  }));

  const best = highlightBest ? Math.max(...values) : Number.NaN;

  return (
    <svg className="chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img">
      <Gridlines max={max} min={min} />
      <polyline
        className="chart-line"
        points={coords.map((point) => `${point.x},${point.y}`).join(" ")}
      />
      {coords.map((point) => (
        <circle
          key={point.date}
          className={`chart-dot ${point.value === best ? "best" : ""}`}
          cx={point.x}
          cy={point.y}
          r={point.value === best ? 5 : 3.5}
        >
          <title>{`${formatDay(point.date)}: ${formatNumber(point.value)} ${unit}`}</title>
        </circle>
      ))}
      <text className="chart-label" x={PAD_LEFT} y={HEIGHT - 8}>
        {formatDay(points[0].date)}
      </text>
      {points.length > 1 && (
        <text className="chart-label" x={WIDTH - 12} y={HEIGHT - 8} textAnchor="end">
          {formatDay(points[points.length - 1].date)}
        </text>
      )}
    </svg>
  );
}
