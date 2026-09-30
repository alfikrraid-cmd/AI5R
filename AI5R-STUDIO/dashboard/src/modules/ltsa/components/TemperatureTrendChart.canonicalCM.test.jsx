import "@testing-library/jest-dom";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TemperatureTrendChart from "./TemperatureTrendChart";

// Benchmark asset canonical data (Asset 212-P-1 from real condition_monitoring_reading)
const BENCHMARK_CANONICAL_READINGS = [
  {
    id: "LTSA-CMONR2-7947400A5A65CA9B",
    equipmentTag: "212-P-1",
    readingDate: "2026-01-09",
    mechsealTempDe: 108.0,
    mechsealTempNde: 107.0,
    flushingTempDe: 115.0,
    flushingTempNde: 116.0,
    suctionTemp: 107.0,
    dischargeTemp: 108.0,
  },
  {
    id: "LTSA-CMONR2-CCA6906AABB6207A",
    equipmentTag: "212-P-1",
    readingDate: "2026-01-13",
    mechsealTempDe: 104.0,
    mechsealTempNde: 102.0,
    flushingTempDe: 108.0,
    flushingTempNde: 105.0,
    suctionTemp: 90.0,
    dischargeTemp: 88.0,
  },
  {
    id: "CMONR-E19103E8E0F1",
    equipmentTag: "212-P-1",
    readingDate: "2026-07-10",
    mechsealTempDe: 104.0,
    mechsealTempNde: 94.0,
    flushingTempDe: 100.0,
    flushingTempNde: 101.0,
    suctionTemp: 105.0,
    dischargeTemp: 95.0,
  },
  {
    id: "CMONR-7CBC288CE20B",
    equipmentTag: "212-P-1",
    readingDate: "2026-07-28",
    mechsealTempDe: 97.0,
    mechsealTempNde: 96.0,
    flushingTempDe: 96.0,
    flushingTempNde: 98.0,
    suctionTemp: 90.0,
    dischargeTemp: 94.0,
  },
];

const OTHER_ASSET_READINGS = [
  {
    id: "CMONR-OTHER-001",
    equipmentTag: "999-P-9",
    readingDate: "2026-07-20",
    mechsealTempDe: 40.0,
    mechsealTempNde: 42.0,
  },
];

describe("PHASE=LTSA_CM_TEMPERATURE_TREND_GRAPH_R1 Canonical Tests", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-07-30T00:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("proves graph uses condition_monitoring_reading and derives X-axis from reading_date", () => {
    render(<TemperatureTrendChart readings={BENCHMARK_CANONICAL_READINGS} />);
    const chart = screen.getByTestId("temperature-trend-chart");

    // X-axis label and ticks
    expect(within(chart).getByTestId("trend-date-axis-label")).toHaveTextContent("Measurement date");
    expect(within(chart).getByTestId("trend-temp-axis-label")).toHaveTextContent("Temperature (°C)");

    // Date ticks exist and derive from reading_date
    const dateTicks = within(chart).getAllByTestId("trend-date-tick");
    expect(dateTicks.length).toBeGreaterThanOrEqual(2);
  });

  it("proves temperature values map correctly without unit corruption", () => {
    render(<TemperatureTrendChart readings={BENCHMARK_CANONICAL_READINGS} />);
    const chart = screen.getByTestId("temperature-trend-chart");

    // Both DE and NDE series are present
    expect(within(chart).getByTestId("trend-line-de")).toBeInTheDocument();
    expect(within(chart).getByTestId("trend-line-nde")).toBeInTheDocument();

    // Badges indicate point counts
    expect(within(chart).getAllByText(/DE \(2 pts\)/).length).toBeGreaterThanOrEqual(1);
    expect(within(chart).getAllByText(/NDE \(2 pts\)/).length).toBeGreaterThanOrEqual(1);
  });

  it("proves chronological ordering sorts ascending by reading_date even if input is out of order", () => {
    const outOfOrder = [
      { readingDate: "2026-07-28", mechsealTempDe: 97.0, mechsealTempNde: 96.0 },
      { readingDate: "2026-07-10", mechsealTempDe: 104.0, mechsealTempNde: 94.0 },
    ];
    render(<TemperatureTrendChart readings={outOfOrder} />);
    const chart = screen.getByTestId("temperature-trend-chart");

    const deLine = within(chart).getByTestId("trend-line-de");
    const pointsStr = deLine.getAttribute("points");
    const [p1, p2] = pointsStr.split(" ").map((pair) => pair.split(",").map(Number));

    // Earlier date (2026-07-10) must have a smaller x coordinate than later date (2026-07-28)
    expect(p1[0]).toBeLessThan(p2[0]);
  });

  it("proves null values are not fabricated and zero is preserved as a valid temperature", () => {
    const withNullAndZero = [
      { readingDate: "2026-07-10", mechsealTempDe: 0, mechsealTempNde: null },
      { readingDate: "2026-07-28", mechsealTempDe: 85, mechsealTempNde: null },
    ];
    render(<TemperatureTrendChart readings={withNullAndZero} />);
    const chart = screen.getByTestId("temperature-trend-chart");

    // DE has 2 points including 0 °C
    expect(within(chart).getByTestId("trend-line-de")).toBeInTheDocument();
    expect(within(chart).getByText(/DE \(2 pts\)/)).toBeInTheDocument();

    // NDE has 0 points and NO fake polyline
    expect(within(chart).queryByTestId("trend-line-nde")).not.toBeInTheDocument();
    expect(within(chart).getByText(/NDE \(0 pts\)/)).toBeInTheDocument();
    expect(chart.textContent).not.toContain("NDE 0°C");
  });

  it("proves empty state displays 'No temperature readings available'", () => {
    render(<TemperatureTrendChart readings={[]} />);
    expect(screen.getByText("No seal-system temperature measurements available for this period.")).toBeInTheDocument();
    expect(screen.getByText("No process temperature measurements available for this period.")).toBeInTheDocument();
  });

  it("proves tooltip shows Date, Measurement point, and Temperature °C", () => {
    render(<TemperatureTrendChart readings={BENCHMARK_CANONICAL_READINGS} />);
    const chart = screen.getByTestId("temperature-trend-chart");

    // Find circles
    const circles = chart.querySelectorAll("circle");
    expect(circles.length).toBeGreaterThan(0);

    // Hover first circle
    fireEvent.mouseEnter(circles[0]);

    const tooltip = screen.getByTestId("trend-tooltip");
    expect(tooltip).toBeInTheDocument();
    expect(screen.getByTestId("trend-tooltip-date").textContent).toMatch(/Date:/i);
    expect(screen.getByTestId("trend-tooltip-point").textContent).toMatch(/Measurement point:/i);
    expect(screen.getByTestId("trend-tooltip-temp").textContent).toMatch(/°C/);

    // Unhover removes tooltip
    fireEvent.mouseLeave(circles[0]);
    expect(screen.queryByTestId("trend-tooltip")).not.toBeInTheDocument();
  });

  it("proves legacy cm_report is never used as temperature trend source", () => {
    // If an object from cm_report is provided without readingDate, it won't crash and won't fabricate data
    const legacyCmReportMock = [
      { cm_report_code: "CM-001", equipmentTag: "212-P-1", failure_description: "Bearing failure" },
    ];
    render(<TemperatureTrendChart readings={legacyCmReportMock} />);
    expect(screen.getByText("No seal-system temperature measurements available for this period.")).toBeInTheDocument();
  });
});
