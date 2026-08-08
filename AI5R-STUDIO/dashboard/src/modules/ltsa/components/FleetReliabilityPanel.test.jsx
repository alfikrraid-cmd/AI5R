import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import FleetReliabilityPanel from "./FleetReliabilityPanel";
import { getFleetReliability } from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({
  getFleetReliability: vi.fn(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

function response(overrides = {}) {
  return {
    success: true,
    data: {
      pump_count: 4,
      fleet_health_score: 86.5,
      fleet_mtbf_days: 42.3,
      fleet_mttr_hours: 6.25,
      fleet_availability: 98.76,
      total_breakdown_count: 3,
      total_critical_spare_count: 2,
      ...overrides,
    },
  };
}

describe("FleetReliabilityPanel", () => {
  it("renders a loading state before the API resolves", () => {
    getFleetReliability.mockReturnValue(new Promise(() => {}));

    render(<FleetReliabilityPanel />);

    expect(screen.getByText(/loading fleet reliability/i)).toBeTruthy();
  });

  it("renders an error state without fallback data when the API call fails", async () => {
    getFleetReliability.mockRejectedValue(new Error("Fleet reliability API unavailable"));

    render(<FleetReliabilityPanel />);

    expect(await screen.findByText("Fleet reliability API unavailable")).toBeTruthy();
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.queryByText("Fleet Health")).toBeNull();
  });

  it("calls the Fleet Reliability API exactly once, no other API", async () => {
    getFleetReliability.mockResolvedValue(response());

    render(<FleetReliabilityPanel />);

    await waitFor(() => expect(getFleetReliability).toHaveBeenCalledTimes(1));
  });

  it("renders the Fleet Reliability heading and all six required metric cards", async () => {
    getFleetReliability.mockResolvedValue(response());

    render(<FleetReliabilityPanel />);

    expect(await screen.findByRole("heading", { name: "Fleet Reliability" })).toBeTruthy();
    expect(screen.getByText("Fleet Health")).toBeTruthy();
    expect(screen.getByText("Fleet MTBF")).toBeTruthy();
    expect(screen.getByText("Fleet MTTR")).toBeTruthy();
    expect(screen.getByText("Fleet Availability")).toBeTruthy();
    expect(screen.getByText("Breakdown Count")).toBeTruthy();
    expect(screen.getByText("Critical Spare Count")).toBeTruthy();
  });

  it("formats Fleet Health as a rounded 0-100 score", async () => {
    getFleetReliability.mockResolvedValue(response({ fleet_health_score: 86.5 }));

    render(<FleetReliabilityPanel />);

    await screen.findByText("Fleet Health");
    expect(screen.getByText("87")).toBeTruthy();
  });

  it("formats Fleet MTBF in days", async () => {
    getFleetReliability.mockResolvedValue(response({ fleet_mtbf_days: 42.3 }));

    render(<FleetReliabilityPanel />);

    await screen.findByText("Fleet MTBF");
    expect(screen.getByText("42 days")).toBeTruthy();
  });

  it("formats Fleet MTTR in hours", async () => {
    getFleetReliability.mockResolvedValue(response({ fleet_mttr_hours: 6.25 }));

    render(<FleetReliabilityPanel />);

    await screen.findByText("Fleet MTTR");
    expect(screen.getByText("6 hrs")).toBeTruthy();
  });

  it("formats Fleet Availability as a percentage", async () => {
    getFleetReliability.mockResolvedValue(response({ fleet_availability: 98.76 }));

    render(<FleetReliabilityPanel />);

    await screen.findByText("Fleet Availability");
    expect(screen.getByText("98.76%")).toBeTruthy();
  });

  it("renders Breakdown Count and Critical Spare Count as plain integers", async () => {
    getFleetReliability.mockResolvedValue(response({ total_breakdown_count: 3, total_critical_spare_count: 2 }));

    render(<FleetReliabilityPanel />);

    await screen.findByText("Breakdown Count");
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("2")).toBeTruthy();
  });

  it("shows Unavailable for Fleet Health, MTBF, MTTR, and Availability when the fleet has no data, never a fabricated number", async () => {
    getFleetReliability.mockResolvedValue(
      response({
        fleet_health_score: null,
        fleet_mtbf_days: null,
        fleet_mttr_hours: null,
        fleet_availability: null,
      })
    );

    render(<FleetReliabilityPanel />);

    await screen.findByText("Fleet Health");
    expect(screen.getAllByText("Unavailable").length).toBe(4);
  });

  it("makes no reference anywhere to the Engineering AI feature (No AI, per this MWO's rule)", () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const source = readFileSync(join(here, "FleetReliabilityPanel.jsx"), "utf-8");

    expect(source).not.toMatch(/postEngineeringAI|engineering-ai|EngineeringAI/);
  });
});
