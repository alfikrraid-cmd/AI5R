import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import TimeSeriesChart from "./TimeSeriesChart";
import BarChart from "./BarChart";
import DonutChart from "./DonutChart";
import HorizontalBarChart from "./HorizontalBarChart";

describe("TimeSeriesChart Component", () => {
  it("renders SVG with role=img and title", () => {
    const data = [
      { date: "2026-07-01", pm_count: 0, cmon_readings: 25, seal_leaks: 5 },
      { date: "2026-07-02", pm_count: 4, cmon_readings: 14, seal_leaks: 1 },
    ];
    render(<TimeSeriesChart data={data} title="Daily Trend" />);

    expect(screen.getByTestId("timeseries-chart")).toBeTruthy();
    expect(screen.getByRole("img", { name: "Daily Trend" })).toBeTruthy();
    expect(screen.getByText("Seal Leaks")).toBeTruthy();
    expect(screen.getByText("PM Done")).toBeTruthy();
  });

  it("handles empty data gracefully without crashing", () => {
    render(<TimeSeriesChart data={[]} title="Daily Trend" />);
    expect(screen.getByText(/no trend records available/i)).toBeTruthy();
  });
});

describe("BarChart Component", () => {
  it("renders category bars and handles selection", () => {
    const data = [
      { area: "HCC", pump_count: 82, pm_count: 19, seal_leaks: 22 },
      { area: "HOC", pump_count: 54, pm_count: 19, seal_leaks: 15 },
    ];
    const onSelect = vi.fn();
    render(<BarChart data={data} categoryKey="area" onSelectCategory={onSelect} />);

    expect(screen.getByTestId("bar-chart")).toBeTruthy();
    expect(screen.getByText("HCC")).toBeTruthy();
    expect(screen.getByText("HOC")).toBeTruthy();

    fireEvent.click(screen.getByText("HCC"));
    expect(onSelect).toHaveBeenCalledWith("HCC");
  });

  it("handles empty data gracefully", () => {
    render(<BarChart data={[]} />);
    expect(screen.getByText(/no category records available/i)).toBeTruthy();
  });
});

describe("DonutChart Component", () => {
  it("renders slices and total count", () => {
    const data = [
      { label: "Drive End (DE)", value: 45 },
      { label: "Non-Drive End (NDE)", value: 9 },
    ];
    render(<DonutChart data={data} labelKey="label" valueKey="value" title="Leak Location" />);

    expect(screen.getByTestId("donut-chart")).toBeTruthy();
    expect(screen.getByText("54")).toBeTruthy(); // 45 + 9 = 54
    expect(screen.getByText("Drive End (DE)")).toBeTruthy();
    expect(screen.getByText("Non-Drive End (NDE)")).toBeTruthy();
  });

  it("handles empty or zero data gracefully", () => {
    render(<DonutChart data={[]} />);
    expect(screen.getByText(/no distribution data available/i)).toBeTruthy();
  });
});

describe("HorizontalBarChart Component", () => {
  it("renders ranked bars and handles pump selection", () => {
    const data = [
      { pump_tag: "011-P-1A", leak_count: 4, area: "MA1", cmon_readings: 12 },
      { pump_tag: "022-P-2B", leak_count: 2, area: "MA2", cmon_readings: 8 },
    ];
    const onSelect = vi.fn();
    render(<HorizontalBarChart data={data} onSelect={onSelect} />);

    expect(screen.getByTestId("horizontal-bar-chart")).toBeTruthy();
    expect(screen.getByText("011-P-1A")).toBeTruthy();
    expect(screen.getByText("022-P-2B")).toBeTruthy();
    expect(screen.getByText("MA1")).toBeTruthy();
    expect(screen.getByText("4 leaks")).toBeTruthy();

    fireEvent.click(screen.getByText("011-P-1A"));
    expect(onSelect).toHaveBeenCalledWith("011-P-1A");
  });

  it("handles empty data gracefully", () => {
    render(<HorizontalBarChart data={[]} />);
    expect(screen.getByText(/no risk\/bad actor records identified/i)).toBeTruthy();
  });
});

