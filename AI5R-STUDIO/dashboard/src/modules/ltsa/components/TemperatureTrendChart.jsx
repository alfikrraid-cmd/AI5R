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
const HEIGHT = 240;
const PAD = { top: 20, right: 20, bottom: 46, left: 54 };
const DATE_LABEL = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short" });

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

function scaleDate(date, minDate, maxDate) {
  const dateSpan = maxDate - minDate || 1;
  return PAD.left + ((date - minDate) / dateSpan) * (WIDTH - PAD.left - PAD.right);
}

function scaleTemp(value, minTemp, maxTemp) {
  const tempSpan = maxTemp - minTemp || 1;
  return PAD.top + (HEIGHT - PAD.top - PAD.bottom) - ((value - minTemp) / tempSpan) * (HEIGHT - PAD.top - PAD.bottom);
}

function scalePoints(points, bounds) {
  return points.map((point) => ({
    x: scaleDate(point.date, bounds.minDate, bounds.maxDate),
    y: scaleTemp(point.value, bounds.minTemp, bounds.maxTemp),
    value: point.value,
    date: point.date,
  }));
}

function buildDateTicks(dates) {
  const uniqueDates = Array.from(new Set(dates.map((date) => date.getTime())))
    .sort((a, b) => a - b)
    .map((time) => new Date(time));

  if (uniqueDates.length <= 3) return uniqueDates;

  return [uniqueDates[0], uniqueDates[Math.floor(uniqueDates.length / 2)], uniqueDates[uniqueDates.length - 1]];
}

function buildTempTicks(minTemp, maxTemp) {
  if (minTemp === maxTemp) return [minTemp];
  return [minTemp, (minTemp + maxTemp) / 2, maxTemp];
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
  let axisBounds = null;
  let dateTicks = [];
  let tempTicks = [];
  if (hasAnyData) {
    axisBounds = {
      minDate: new Date(Math.min(...allDates)),
      maxDate: new Date(Math.max(...allDates)),
      minTemp: Math.min(...allValues),
      maxTemp: Math.max(...allValues),
    };
    deScaled = scalePoints(series.de.map((p) => ({ date: p.date, value: p.de })), axisBounds);
    ndeScaled = scalePoints(series.nde.map((p) => ({ date: p.date, value: p.nde })), axisBounds);
    dateTicks = buildDateTicks(allDates);
    tempTicks = buildTempTicks(axisBounds.minTemp, axisBounds.maxTemp);
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

        <div
          role="group"
          aria-label="Trend time range"
          style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs, alignItems: "center" }}
        >
          {RANGE_OPTIONS.map((option) => (
            <button
              key={option.key}
              type="button"
              aria-pressed={option.key === rangeKey}
              aria-label={option.label}
              onClick={() => setRangeKey(option.key)}
              style={{
                minWidth: 36,
                minHeight: 28,
                padding: `4px ${spacing.sm}px`,
                borderRadius: spacing.xs,
                border: `1px solid ${option.key === rangeKey ? colors.accent : colors.border}`,
                background: option.key === rangeKey ? colors.accent : colors.panel,
                color: option.key === rangeKey ? colors.background : colors.text,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                fontWeight: 700,
                lineHeight: 1,
                whiteSpace: "nowrap",
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

            {axisBounds && dateTicks.map((date) => {
              const x = scaleDate(date, axisBounds.minDate, axisBounds.maxDate);
              return (
                <g key={`date-${date.toISOString()}`} data-testid="trend-date-tick">
                  <line x1={x} y1={HEIGHT - PAD.bottom} x2={x} y2={HEIGHT - PAD.bottom + 5} stroke={colors.border} />
                  <text x={x} y={HEIGHT - PAD.bottom + 19} textAnchor="middle" fontSize="11" fill={colors.textMuted}>
                    {DATE_LABEL.format(date)}
                  </text>
                </g>
              );
            })}

            {axisBounds && tempTicks.map((value) => {
              const y = scaleTemp(value, axisBounds.minTemp, axisBounds.maxTemp);
              return (
                <g key={`temp-${value}`} data-testid="trend-temp-tick">
                  <line x1={PAD.left - 5} y1={y} x2={PAD.left} y2={y} stroke={colors.border} />
                  <text x={PAD.left - 8} y={y + 4} textAnchor="end" fontSize="11" fill={colors.textMuted}>
                    {Math.round(value)}
                  </text>
                </g>
              );
            })}

            <text x={(PAD.left + WIDTH - PAD.right) / 2} y={HEIGHT - 8} textAnchor="middle" fontSize="12" fill={colors.textMuted} data-testid="trend-date-axis-label">
              Measurement date
            </text>
            <text x="14" y={(PAD.top + HEIGHT - PAD.bottom) / 2} textAnchor="middle" fontSize="12" fill={colors.textMuted} transform={`rotate(-90 14 ${(PAD.top + HEIGHT - PAD.bottom) / 2})`} data-testid="trend-temp-axis-label">
              {"Temperature (\u00b0C)"}
            </text>

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
                <title>{`DE ${p.value}\u00b0C - ${p.date.toISOString().slice(0, 10)}`}</title>
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
                <title>{`NDE ${p.value}\u00b0C - ${p.date.toISOString().slice(0, 10)}`}</title>
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
