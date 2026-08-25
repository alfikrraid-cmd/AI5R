import { useMemo, useState } from "react";
import { Badge } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

// MWO-LTSA-ASSET360-CONSOLIDATION-001 -- dependency-free SVG trend chart.
// No charting library exists anywhere in this dashboard (AnalyticsWorkspace's
// own ActivityTrendTable.jsx is a plain HTML table, not a chart) -- adding
// one mid-mission would be a build/dependency change well beyond "prefer
// additive/minimal", so this draws a plain <svg> line/point chart instead.
// Real data points only, connected by straight segments between REAL
// points -- never interpolated/fabricated for a gap, and a null
// temperature is never plotted as (and never confused with) zero.

const RANGE_OPTIONS = [
  { key: "1M", label: "1M", days: 30 },
  { key: "3M", label: "3M", days: 90 },
  { key: "6M", label: "6M", days: 182 },
  { key: "1Y", label: "1Y", days: 365 },
];

// One representative field per group -- DE/NDE pair, exactly the shape
// mapConditionMonitoringReadingRecord already produces. Mechanical Seal is
// the default (this session's own golden-record example: "Tampilkan trend
// temperatur mechanical seal selama 1 tahun").
const FIELD_OPTIONS = [
  { key: "mechseal", label: "Mechanical Seal", deKey: "mechsealTempDe", ndeKey: "mechsealTempNde" },
  { key: "flushing", label: "Flushing", deKey: "flushingTempDe", ndeKey: "flushingTempNde" },
  { key: "quench", label: "Quench", deKey: "quenchTempDe", ndeKey: "quenchTempNde" },
  { key: "coolingWater", label: "Cooling Water", deKey: "coolingWaterInTempDe", ndeKey: "coolingWaterInTempNde" },
];

const WIDTH = 640;
const HEIGHT = 200;
const PAD = { top: 16, right: 16, bottom: 28, left: 40 };

function parseDate(value) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function withinRange(date, rangeDays) {
  if (rangeDays === null) return true;
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - rangeDays);
  return date >= cutoff;
}

function buildSeries(readings, field, rangeDays) {
  const points = readings
    .map((reading) => ({ date: parseDate(reading.readingDate), de: reading[field.deKey], nde: reading[field.ndeKey] }))
    .filter((point) => point.date !== null && withinRange(point.date, rangeDays))
    .sort((a, b) => a.date - b.date);

  return {
    de: points.filter((point) => point.de !== null && point.de !== undefined),
    nde: points.filter((point) => point.nde !== null && point.nde !== undefined),
  };
}

function scalePoints(points, { minDate, maxDate, minTemp, maxTemp }) {
  const dateSpan = maxDate - minDate || 1;
  const tempSpan = maxTemp - minTemp || 1;
  const plotWidth = WIDTH - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;

  return points.map((point) => ({
    x: PAD.left + ((point.date - minDate) / dateSpan) * plotWidth,
    y: PAD.top + plotHeight - ((point.value - minTemp) / tempSpan) * plotHeight,
    value: point.value,
    date: point.date,
  }));
}

export default function TemperatureTrendChart({ readings }) {
  const [rangeKey, setRangeKey] = useState("3M");
  const [fieldKey, setFieldKey] = useState("mechseal");

  const range = RANGE_OPTIONS.find((option) => option.key === rangeKey) ?? RANGE_OPTIONS[1];
  const field = FIELD_OPTIONS.find((option) => option.key === fieldKey) ?? FIELD_OPTIONS[0];

  const series = useMemo(
    () => buildSeries(readings ?? [], field, range.days),
    [readings, field, range.days]
  );

  const allValues = [...series.de.map((p) => p.de), ...series.nde.map((p) => p.nde)];
  const allDates = [...series.de.map((p) => p.date), ...series.nde.map((p) => p.date)];
  const hasEnoughData = allValues.length >= 2;
  const hasAnyData = allValues.length >= 1;

  let deScaled = [];
  let ndeScaled = [];
  if (hasAnyData) {
    const bounds = {
      minDate: new Date(Math.min(...allDates)),
      maxDate: new Date(Math.max(...allDates)),
      minTemp: Math.min(...allValues),
      maxTemp: Math.max(...allValues),
    };
    deScaled = scalePoints(series.de.map((p) => ({ date: p.date, value: p.de })), bounds);
    ndeScaled = scalePoints(series.nde.map((p) => ({ date: p.date, value: p.nde })), bounds);
  }

  return (
    <div data-testid="temperature-trend-chart">
      <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.sm, alignItems: "center", marginBottom: spacing.sm }}>
        <select
          aria-label="Temperature point"
          value={fieldKey}
          onChange={(event) => setFieldKey(event.target.value)}
          style={{ padding: `${spacing.xs}px`, borderRadius: spacing.xs, border: `1px solid ${colors.border}`, background: colors.panel, color: colors.text }}
        >
          {FIELD_OPTIONS.map((option) => (
            <option key={option.key} value={option.key}>
              {option.label} DE/NDE
            </option>
          ))}
        </select>

        <div role="group" aria-label="Trend time range" style={{ display: "flex", gap: spacing.xs }}>
          {RANGE_OPTIONS.map((option) => (
            <button
              key={option.key}
              type="button"
              aria-pressed={option.key === rangeKey}
              onClick={() => setRangeKey(option.key)}
              style={{
                padding: `2px ${spacing.xs}px`,
                borderRadius: spacing.xs,
                border: `1px solid ${colors.border}`,
                background: option.key === rangeKey ? colors.accent : "transparent",
                color: option.key === rangeKey ? colors.background : colors.text,
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {!hasAnyData ? (
        <p style={{ color: colors.textMuted, fontSize: 13 }}>
          No {field.label} temperature readings available for this pump in this range.
        </p>
      ) : (
        <>
          {!hasEnoughData && (
            <p style={{ color: colors.textMuted, fontSize: 12, marginTop: 0 }}>
              Only {allValues.length} data point available in this range -- showing available points honestly, not
              interpolated.
            </p>
          )}
          <svg width="100%" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`${field.label} temperature trend`}>
            <line x1={PAD.left} y1={HEIGHT - PAD.bottom} x2={WIDTH - PAD.right} y2={HEIGHT - PAD.bottom} stroke={colors.border} />
            <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={HEIGHT - PAD.bottom} stroke={colors.border} />

            {deScaled.length > 0 && (
              <polyline
                points={deScaled.map((p) => `${p.x},${p.y}`).join(" ")}
                fill="none"
                stroke={colors.accent ?? "#3b82f6"}
                strokeWidth={2}
                data-testid="trend-line-de"
              />
            )}
            {deScaled.map((p, index) => (
              <circle key={`de-${index}`} cx={p.x} cy={p.y} r={3} fill={colors.accent ?? "#3b82f6"}>
                <title>{`DE ${p.value}°C · ${p.date.toISOString().slice(0, 10)}`}</title>
              </circle>
            ))}

            {ndeScaled.length > 0 && (
              <polyline
                points={ndeScaled.map((p) => `${p.x},${p.y}`).join(" ")}
                fill="none"
                stroke={colors.warning ?? "#f59e0b"}
                strokeWidth={2}
                strokeDasharray="4 3"
                data-testid="trend-line-nde"
              />
            )}
            {ndeScaled.map((p, index) => (
              <circle key={`nde-${index}`} cx={p.x} cy={p.y} r={3} fill={colors.warning ?? "#f59e0b"}>
                <title>{`NDE ${p.value}°C · ${p.date.toISOString().slice(0, 10)}`}</title>
              </circle>
            ))}
          </svg>
          <div style={{ display: "flex", gap: spacing.sm, marginTop: spacing.xs }}>
            <Badge variant="info">DE ({series.de.length} pts)</Badge>
            <Badge variant="warning">NDE ({series.nde.length} pts)</Badge>
          </div>
        </>
      )}
    </div>
  );
}
