import "@testing-library/jest-dom";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TemperatureTrendChart from "./TemperatureTrendChart";

const READINGS = [
  {
    readingDate: "2026-06-24",
    mechsealTempDe: 50,
    mechsealTempNde: null,
  },
  {
    readingDate: "2026-07-24",
    mechsealTempDe: 52,
    mechsealTempNde: 49,
  },
  {
    readingDate: "2026-08-20",
    mechsealTempDe: 54,
    mechsealTempNde: 50,
  },
];

describe("TemperatureTrendChart", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-25T00:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders 30D/90D/6M/1Y/ALL controls with 6M selected by default", () => {
    render(<TemperatureTrendChart readings={READINGS} />);

    const chart = screen.getByTestId("temperature-trend-chart");
    const sealChart = within(chart).getAllByTestId("temperature-trend-subchart")[0];
    ["30D", "90D", "6M", "1Y", "ALL"].forEach((label) => {
      const button = within(sealChart).getByRole("button", { name: label });
      expect(button).toBeVisible();
      expect(button).toHaveTextContent(label);
      expect(button).toHaveStyle({ minWidth: "36px", whiteSpace: "nowrap" });
    });
    expect(within(sealChart).getByRole("button", { name: "6M" })).toHaveAttribute("aria-pressed", "true");
  });

  it("switches range selection without changing the allowed control set", () => {
    render(<TemperatureTrendChart readings={READINGS} />);

    const chart = screen.getByTestId("temperature-trend-chart");
    const sealChart = within(chart).getAllByTestId("temperature-trend-subchart")[0];
    fireEvent.click(within(sealChart).getByRole("button", { name: "1Y" }));

    expect(within(sealChart).getByRole("button", { name: "1Y" })).toHaveAttribute("aria-pressed", "true");
    expect(within(sealChart).getAllByRole("button")).toHaveLength(5);
  });

  it("renders date and Celsius axes with DE/NDE as distinct real-data series", () => {
    render(<TemperatureTrendChart readings={READINGS} />);

    const chart = screen.getByTestId("temperature-trend-chart");
    expect(within(chart).getByTestId("trend-date-axis-label")).toHaveTextContent("Measurement date");
    expect(within(chart).getByTestId("trend-temp-axis-label")).toHaveTextContent("Temperature (°C)");
    expect(within(chart).getAllByTestId("trend-date-tick").length).toBeGreaterThanOrEqual(2);
    expect(within(chart).getAllByTestId("trend-temp-tick").length).toBeGreaterThanOrEqual(2);
    expect(within(chart).getByTestId("trend-line-de")).toBeInTheDocument();
    expect(within(chart).getByTestId("trend-line-nde")).toBeInTheDocument();
    expect(within(chart).getByText(/DE \(3 pts\)/)).toBeInTheDocument();
    expect(within(chart).getByText(/NDE \(2 pts\)/)).toBeInTheDocument();
  });

  it("does not fabricate a zero-temperature NDE series when NDE readings are null", () => {
    render(
      <TemperatureTrendChart
        readings={[
          { readingDate: "2026-07-24", mechsealTempDe: 52, mechsealTempNde: null },
          { readingDate: "2026-08-20", mechsealTempDe: 54, mechsealTempNde: null },
        ]}
      />
    );

    const chart = screen.getByTestId("temperature-trend-chart");
    expect(within(chart).getByTestId("trend-line-de")).toBeInTheDocument();
    expect(within(chart).queryByTestId("trend-line-nde")).not.toBeInTheDocument();
    expect(within(chart).getByText(/NDE \(0 pts\)/)).toBeInTheDocument();
    expect(chart.textContent).not.toContain("NDE 0°C");
  });
});
