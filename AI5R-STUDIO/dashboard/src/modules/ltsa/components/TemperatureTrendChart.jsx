import { useMemo, useState } from "react";
import { Badge } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

// MWO-LTSA-ASSET360-CONSOLIDATION-001 & LTSA_CM_TEMPERATURE_TREND_GRAPH_R1
// Dependency-free SVG trend chart for canonical Condition Monitoring readings.
// Real data points only, connected by straight segments between REAL
// points -- never interpolated/fabricated for a gap, and a null
// temperature is never plotted as (and never confused with) zero.

const RANGE_OPTIONS = [
  { key: "30D", label: "30D", days: 30 },
  { key: "90D", label: "90D", days: 90 },
  { key: "6M", label: "6M", days: 182 },
  { key: "1Y", label: "1Y", days: 365 },
  { key: "ALL", label: "ALL", days: null },
];

// Authoritative measurement points supported by condition_monitoring_reading schema.
// Every DE/NDE pair maps directly to canonical columns and mapConditionMonitoringReadingRecord.
export const FIELD_OPTIONS = [
  { key: "mechseal", label: "Mechanical Seal", deKey: "mechsealTempDe", ndeKey: "mechsealTempNde", deLabel: "DE Mechanical Seal Temp", ndeLabel: "NDE Mechanical Seal Temp" },
  { key: "flushing", label: "Flushing", deKey: "flushingTempDe", ndeKey: "flushingTempNde", deLabel: "DE Flushing Temp", ndeLabel: "NDE Flushing Temp" },
  { key: "quench", label: "Quench", deKey: "quenchTempDe", ndeKey: "quenchTempNde", deLabel: "DE Quench Temp", ndeLabel: "NDE Quench Temp" },
  { key: "flushingIn", label: "Flushing In (LBI)", deKey: "flushingInTempDe", ndeKey: "flushingInTempNde", deLabel: "DE Flushing In Temp (LBI)", ndeLabel: "NDE Flushing In Temp (LBI)" },
  { key: "flushingOut", label: "Flushing Out (LBO)", deKey: "flushingOutTempDe", ndeKey: "flushingOutTempNde", deLabel: "DE Flushing Out Temp (LBO)", ndeLabel: "NDE Flushing Out Temp (LBO)" },
  { key: "coolingWater", label: "Cooling Water", deKey: "coolingWaterInTempDe", ndeKey: "coolingWaterInTempNde", deLabel: "DE Cooling Water In Temp", ndeLabel: "NDE Cooling Water In Temp" },
  { key: "coolingWaterOut", label: "Cooling Water Out", deKey: "coolingWaterOutTempDe", ndeKey: "coolingWaterOutTempNde", deLabel: "DE Cooling Water Out Temp", ndeLabel: "NDE Cooling Water Out Temp" },
  { key: "bearing", label: "Bearing", deKey: "bearingTempDe", ndeKey: "bearingTempNde", deLabel: "DE Bearing Temp", ndeLabel: "NDE Bearing Temp" },
  { key: "waterJacket", label: "Water Jacket", deKey: "waterJacketTempDe", ndeKey: "waterJacketTempNde", deLabel: "DE Water Jacket Temp", ndeLabel: "NDE Water Jacket Temp" },
  { key: "stuffingBox", label: "Stuffing Box", deKey: "stuffingBoxTempDe", ndeKey: "stuffingBoxTempNde", deLabel: "DE Stuffing Box Temp", ndeLabel: "NDE Stuffing Box Temp" },
  { key: "sealGland", label: "Seal Gland", deKey: "sealGlandTempDe", ndeKey: "sealGlandTempNde", deLabel: "DE Seal Gland Temp", ndeLabel: "NDE Seal Gland Temp" },
  { key: "process", label: "Process (Suction/Discharge)", deKey: "suctionTemp", ndeKey: "dischargeTemp", deLabel: "Suction Temp", ndeLabel: "Discharge Temp" },
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

function withinRange(date, latestDate, rangeDays) {
  if (rangeDays === null) return true;
  const cutoff = new Date(latestDate);
  cutoff.setDate(cutoff.getDate() - rangeDays);
  return date >= cutoff && date <= latestDate;
}

function buildSeries(readings, field, rangeDays) {
  const dated = (readings ?? []).map((reading) => ({ ...reading, date: parseDate(reading.readingDate) })).filter((reading) => reading.date);
  const latestDate = dated.reduce((latest, reading) => (reading.date > latest ? reading.date : latest), new Date(0));
  const points = (readings ?? [])
    .map((reading) => ({
      date: parseDate(reading.readingDate),
      readingDate: reading.readingDate,
      occurrence: reading.id,
      de: reading[field.deKey],
      nde: reading[field.ndeKey],
    }))
    .filter((point) => point.date !== null && withinRange(point.date, latestDate, rangeDays))
    .sort((a, b) => a.date - b.date);

  return {
    de: points
      .filter((point) => point.de !== null && point.de !== undefined)
      .map((p) => ({ date: p.date, readingDate: p.readingDate, occurrence: p.occurrence, value: p.de })),
    nde: points
      .filter((point) => point.nde !== null && point.nde !== undefined)
      .map((p) => ({ date: p.date, readingDate: p.readingDate, occurrence: p.occurrence, value: p.nde })),
  };
}

function scaleDate(date, minDate, maxDate) {
  const dateSpan = maxDate.getTime() - minDate.getTime();
  if (dateSpan === 0) {
    return PAD.left + (WIDTH - PAD.left - PAD.right) / 2;
  }
  return PAD.left + ((date.getTime() - minDate.getTime()) / dateSpan) * (WIDTH - PAD.left - PAD.right);
}

function scaleTemp(value, minTemp, maxTemp) {
  const tempSpan = maxTemp - minTemp;
  if (tempSpan === 0) {
    return PAD.top + (HEIGHT - PAD.top - PAD.bottom) / 2;
  }
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
  return [minTemp, Math.round((minTemp + maxTemp) / 2), maxTemp];
}

function SingleTemperatureTrendChart({ readings, title, fieldKeys, testIdSuffix = "" }) {
  const [rangeKey, setRangeKey] = useState("6M");
  const [fieldKey, setFieldKey] = useState("mechseal");
  const [activePoint, setActivePoint] = useState(null);

  const range = RANGE_OPTIONS.find((option) => option.key === rangeKey) ?? RANGE_OPTIONS[1];
  const availableFields = FIELD_OPTIONS.filter((option) => !fieldKeys || fieldKeys.includes(option.key));
  const field = availableFields.find((option) => option.key === fieldKey) ?? availableFields[0] ?? FIELD_OPTIONS[0];
  const tid = (name) => `${name}${testIdSuffix}`;

  const series = useMemo(
    () => buildSeries(readings ?? [], field, range.days),
    [readings, field, range.days]
  );

  const allValues = [...series.de.map((p) => p.value), ...series.nde.map((p) => p.value)];
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
    deScaled = scalePoints(series.de, axisBounds);
    ndeScaled = scalePoints(series.nde, axisBounds);
    dateTicks = buildDateTicks(allDates);
    tempTicks = buildTempTicks(axisBounds.minTemp, axisBounds.maxTemp);
  }

  return (
    <div data-testid={tid("temperature-trend-subchart")} style={{ position: "relative" }}>
      <h4 style={{ margin: `0 0 ${spacing.xs}px` }}>{title}</h4>
      <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.sm, alignItems: "center", marginBottom: spacing.sm }}>
        {availableFields.length > 1 && <select
          aria-label="Temperature point"
          value={fieldKey}
          onChange={(event) => {
            setFieldKey(event.target.value);
            setActivePoint(null);
          }}
          style={{ padding: `${spacing.xs}px`, borderRadius: spacing.xs, border: `1px solid ${colors.border}`, background: colors.panel, color: colors.text }}
        >
          {availableFields.map((option) => (
            <option key={option.key} value={option.key}>
              {option.key === "process" ? option.label : `${option.label} DE/NDE`}
            </option>
          ))}
        </select>}

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
              onClick={() => {
                setRangeKey(option.key);
                setActivePoint(null);
              }}
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
        <p data-testid={tid("trend-empty-state")} style={{ color: colors.textMuted, fontSize: 13 }}>
          {title === "Seal System Temperature" ? "No seal-system temperature measurements available for this period." : "No process temperature measurements available for this period."}
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
                <g key={`date-${date.toISOString()}`} data-testid={tid("trend-date-tick")}>
                  <line x1={x} y1={HEIGHT - PAD.bottom} x2={x} y2={HEIGHT - PAD.bottom + 5} stroke={colors.border} />
                  <text x={x} y={HEIGHT - PAD.bottom + 19} textAnchor="middle" fontSize="11" fill={colors.textMuted}>
                    {DATE_LABEL.format(date)}
                  </text>
                </g>
              );
            })}

            {axisBounds && tempTicks.map((value, index) => {
              const y = scaleTemp(value, axisBounds.minTemp, axisBounds.maxTemp);
              return (
                <g key={`temp-${value}-${index}`} data-testid={tid("trend-temp-tick")}>
                  <line x1={PAD.left - 5} y1={y} x2={PAD.left} y2={y} stroke={colors.border} />
                  <text x={PAD.left - 8} y={y + 4} textAnchor="end" fontSize="11" fill={colors.textMuted}>
                    {Math.round(value)}
                  </text>
                </g>
              );
            })}

            <text x={(PAD.left + WIDTH - PAD.right) / 2} y={HEIGHT - 8} textAnchor="middle" fontSize="12" fill={colors.textMuted} data-testid={tid("trend-date-axis-label")}>
              Measurement date
            </text>
            <text x="14" y={(PAD.top + HEIGHT - PAD.bottom) / 2} textAnchor="middle" fontSize="12" fill={colors.textMuted} transform={`rotate(-90 14 ${(PAD.top + HEIGHT - PAD.bottom) / 2})`} data-testid={tid("trend-temp-axis-label")}>
              {"Temperature (\u00b0C)"}
            </text>

            {deScaled.length > 0 && (
              <polyline
                points={deScaled.map((p) => `${p.x},${p.y}`).join(" ")}
                fill="none"
                stroke={colors.accent ?? "#3b82f6"}
                strokeWidth={2}
                data-testid={tid("trend-line-de")}
              />
            )}
            {deScaled.map((p, index) => {
              const dateStr = p.date ? p.date.toISOString().slice(0, 10) : "N/A";
              const pointLabel = field.deLabel ?? "DE Temperature";
              const titleText = `Date: ${dateStr}\nMeasurement point: ${pointLabel}\nTemperature: ${p.value} \u00b0C\nOccurrence: ${p.occurrence ?? "N/A"}`;
              return (
                <circle
                  key={`de-${index}`}
                  cx={p.x}
                  cy={p.y}
                  r={activePoint?.series === "de" && activePoint?.index === index ? 5 : 3}
                  fill={colors.accent ?? "#3b82f6"}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={() =>
                    setActivePoint({
                      series: "de",
                      index,
                      x: p.x,
                      y: p.y,
                      dateStr,
                      pointLabel,
                      value: p.value,
                    })
                  }
                  onMouseLeave={() => setActivePoint(null)}
                >
                  <title>{titleText}</title>
                </circle>
              );
            })}

            {ndeScaled.length > 0 && (
              <polyline
                points={ndeScaled.map((p) => `${p.x},${p.y}`).join(" ")}
                fill="none"
                stroke={colors.warning ?? "#f59e0b"}
                strokeWidth={2}
                strokeDasharray="4 3"
                data-testid={tid("trend-line-nde")}
              />
            )}
            {ndeScaled.map((p, index) => {
              const dateStr = p.date ? p.date.toISOString().slice(0, 10) : "N/A";
              const pointLabel = field.ndeLabel ?? "NDE Temperature";
              const titleText = `Date: ${dateStr}\nMeasurement point: ${pointLabel}\nTemperature: ${p.value} \u00b0C\nOccurrence: ${p.occurrence ?? "N/A"}`;
              return (
                <circle
                  key={`nde-${index}`}
                  cx={p.x}
                  cy={p.y}
                  r={activePoint?.series === "nde" && activePoint?.index === index ? 5 : 3}
                  fill={colors.warning ?? "#f59e0b"}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={() =>
                    setActivePoint({
                      series: "nde",
                      index,
                      x: p.x,
                      y: p.y,
                      dateStr,
                      pointLabel,
                      value: p.value,
                    })
                  }
                  onMouseLeave={() => setActivePoint(null)}
                >
                  <title>{titleText}</title>
                </circle>
              );
            })}
          </svg>

          {activePoint && (
            <div
              data-testid={tid("trend-tooltip")}
              style={{
                position: "absolute",
                top: Math.max(10, activePoint.y - 70),
                left: Math.min(Math.max(activePoint.x - 70, 10), WIDTH - 180),
                background: colors.panel ?? "#1e293b",
                border: `1px solid ${colors.border ?? "#334155"}`,
                borderRadius: "6px",
                padding: "6px 10px",
                boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
                pointerEvents: "none",
                zIndex: 10,
                fontSize: "12px",
              }}
            >
              <div data-testid={tid("trend-tooltip-date")} style={{ color: colors.textMuted ?? "#94a3b8", fontSize: "11px" }}>
                Date: {activePoint.dateStr}
              </div>
              <div data-testid={tid("trend-tooltip-point")} style={{ fontWeight: 600, color: colors.text ?? "#ffffff" }}>
                Measurement point: {activePoint.pointLabel}
              </div>
              <div data-testid={tid("trend-tooltip-temp")} style={{ color: colors.accent ?? "#3b82f6", fontWeight: 700 }}>
                Temperature: {activePoint.value} °C
              </div>
            </div>
          )}

          <div style={{ display: "flex", gap: spacing.sm, marginTop: spacing.xs }}>
            <Badge variant="info">{`${field.key === "process" ? "Suction" : "DE"} (${series.de.length} pts)`}</Badge>
            <Badge variant="warning">{`${field.key === "process" ? "Discharge" : "NDE"} (${series.nde.length} pts)`}</Badge>
          </div>
        </>
      )}
    </div>
  );
}

export default function TemperatureTrendChart({ readings }) {
  return (
    <div data-testid="temperature-trend-chart">
      <SingleTemperatureTrendChart readings={readings} title="Seal System Temperature" fieldKeys={["mechseal", "flushing", "quench"]} />
      <SingleTemperatureTrendChart readings={readings} title="Process Temperature" fieldKeys={["process"]} testIdSuffix="-process" />
    </div>
  );
}
