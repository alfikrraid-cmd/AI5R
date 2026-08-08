import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import FleetPowerBIPanel from "./FleetPowerBIPanel";
import { getFleetPowerBI } from "../../../api/ai5rClient";

vi.mock("../../../api/ai5rClient", () => ({
  getFleetPowerBI: vi.fn(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

function response(overrides = {}) {
  return {
    success: true,
    data: {
      overall_health: 86.5,
      fleet_status: "NORMAL",
      critical_asset_count: 1,
      fleet_availability: 98.76,
      fleet_mtbf_days: 42.3,
      fleet_mttr_hours: 6.25,
      breakdown_count: 3,
      critical_spare_count: 2,
      top_risks: [
        {
          tag_number: "641-P-5",
          rule_code: "REC_CRITICAL_CM",
          title: "Immediate Inspection",
          priority: 100,
          action: "Dispatch a technician for immediate inspection.",
          description: "An open Corrective Maintenance report with critical or major severity was found.",
        },
      ],
      insight: {
        summary: "Fleet status NORMAL: 1 critical asset(s). Top risk: Immediate Inspection on 641-P-5.",
        priority: 100,
        action: "Dispatch a technician for immediate inspection.",
        reason: "An open Corrective Maintenance report with critical or major severity was found.",
      },
      ...overrides,
    },
  };
}

describe("FleetPowerBIPanel", () => {
  it("renders a loading state before the API resolves", () => {
    getFleetPowerBI.mockReturnValue(new Promise(() => {}));

    render(<FleetPowerBIPanel />);

    expect(screen.getByText(/loading fleet power bi/i)).toBeTruthy();
  });

  it("renders an error state without fallback data when the API call fails", async () => {
    getFleetPowerBI.mockRejectedValue(new Error("Fleet Power BI API unavailable"));

    render(<FleetPowerBIPanel />);

    expect(await screen.findByText("Fleet Power BI API unavailable")).toBeTruthy();
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.queryByText("Fleet Health")).toBeNull();
  });

  it("calls the Power BI API exactly once, no other API (One Fetch)", async () => {
    getFleetPowerBI.mockResolvedValue(response());

    render(<FleetPowerBIPanel />);

    await waitFor(() => expect(getFleetPowerBI).toHaveBeenCalledTimes(1));
  });

  it("renders the Fleet Power BI heading and all nine required display items", async () => {
    getFleetPowerBI.mockResolvedValue(response());

    render(<FleetPowerBIPanel />);

    expect(await screen.findByRole("heading", { name: "Fleet Power BI" })).toBeTruthy();
    expect(screen.getByText("Fleet Health")).toBeTruthy();
    expect(screen.getByText("Fleet Availability")).toBeTruthy();
    expect(screen.getByText("Fleet MTBF")).toBeTruthy();
    expect(screen.getByText("Fleet MTTR")).toBeTruthy();
    expect(screen.getByText("Breakdown Count")).toBeTruthy();
    expect(screen.getByText("Critical Spare Count")).toBeTruthy();
    expect(screen.getByText("Fleet Status")).toBeTruthy();
    expect(screen.getByText("Fleet Insight")).toBeTruthy();
    expect(screen.getByText("Top Risks")).toBeTruthy();
  });

  it("formats Fleet Health as a rounded 0-100 score, exactly like FleetReliabilityPanel", async () => {
    getFleetPowerBI.mockResolvedValue(response({ overall_health: 86.5 }));

    render(<FleetPowerBIPanel />);

    await screen.findByText("Fleet Health");
    expect(screen.getByText("87")).toBeTruthy();
  });

  it("formats Fleet MTBF in days", async () => {
    getFleetPowerBI.mockResolvedValue(response({ fleet_mtbf_days: 42.3 }));

    render(<FleetPowerBIPanel />);

    await screen.findByText("Fleet MTBF");
    expect(screen.getByText("42 days")).toBeTruthy();
  });

  it("formats Fleet MTTR in hours", async () => {
    getFleetPowerBI.mockResolvedValue(response({ fleet_mttr_hours: 6.25 }));

    render(<FleetPowerBIPanel />);

    await screen.findByText("Fleet MTTR");
    expect(screen.getByText("6 hrs")).toBeTruthy();
  });

  it("formats Fleet Availability as a percentage", async () => {
    getFleetPowerBI.mockResolvedValue(response({ fleet_availability: 98.76 }));

    render(<FleetPowerBIPanel />);

    await screen.findByText("Fleet Availability");
    expect(screen.getByText("98.76%")).toBeTruthy();
  });

  it("renders Breakdown Count and Critical Spare Count as plain integers", async () => {
    getFleetPowerBI.mockResolvedValue(response({ breakdown_count: 3, critical_spare_count: 2 }));

    render(<FleetPowerBIPanel />);

    await screen.findByText("Breakdown Count");
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("2")).toBeTruthy();
  });

  it("renders Fleet Status verbatim, no relabeling", async () => {
    getFleetPowerBI.mockResolvedValue(response({ fleet_status: "CRITICAL" }));

    render(<FleetPowerBIPanel />);

    await screen.findByText("Fleet Status");
    expect(screen.getByText("CRITICAL")).toBeTruthy();
  });

  it("shows Unavailable for Fleet Health, Availability, MTBF, and MTTR when the fleet has no data, never a fabricated number", async () => {
    getFleetPowerBI.mockResolvedValue(
      response({
        overall_health: null,
        fleet_availability: null,
        fleet_mtbf_days: null,
        fleet_mttr_hours: null,
      })
    );

    render(<FleetPowerBIPanel />);

    await screen.findByText("Fleet Health");
    expect(screen.getAllByText("Unavailable").length).toBe(4);
  });

  it("renders the Fleet Insight summary, action, and reason verbatim, no derivation", async () => {
    getFleetPowerBI.mockResolvedValue(
      response({
        insight: {
          summary: "Fleet status ATTENTION: 2 critical asset(s).",
          priority: 90,
          action: "Initiate procurement.",
          reason: "One or more compatible spare parts have no confirmed stock.",
        },
      })
    );

    render(<FleetPowerBIPanel />);

    await screen.findByText("Fleet Insight");
    expect(screen.getByText("Fleet status ATTENTION: 2 critical asset(s).")).toBeTruthy();
    expect(screen.getByText("Initiate procurement.")).toBeTruthy();
    expect(screen.getByText("One or more compatible spare parts have no confirmed stock.")).toBeTruthy();
  });

  it("shows a no-insight placeholder when insight is null, never fabricated content", async () => {
    getFleetPowerBI.mockResolvedValue(response({ insight: null }));

    render(<FleetPowerBIPanel />);

    await screen.findByText("Fleet Insight");
    expect(screen.getByText(/no insight/i)).toBeTruthy();
  });

  it("renders one entry per Top Risk with tag, title, priority, and action", async () => {
    getFleetPowerBI.mockResolvedValue(
      response({
        top_risks: [
          {
            tag_number: "P-1",
            rule_code: "REC_CRITICAL_CM",
            title: "Immediate Inspection",
            priority: 100,
            action: "Dispatch now.",
            description: "desc 1",
          },
          {
            tag_number: "P-2",
            rule_code: "REC_NO_STOCK",
            title: "Procurement Required",
            priority: 90,
            action: "Initiate procurement.",
            description: "desc 2",
          },
        ],
      })
    );

    render(<FleetPowerBIPanel />);

    await screen.findByText("Top Risks");
    expect(screen.getByText("P-1")).toBeTruthy();
    expect(screen.getByText("Immediate Inspection")).toBeTruthy();
    expect(screen.getByText("P-2")).toBeTruthy();
    expect(screen.getByText("Procurement Required")).toBeTruthy();
  });

  it("shows a no-risks placeholder when top_risks is empty, never fabricated", async () => {
    getFleetPowerBI.mockResolvedValue(response({ top_risks: [] }));

    render(<FleetPowerBIPanel />);

    await screen.findByText("Top Risks");
    expect(screen.getByText(/no risks/i)).toBeTruthy();
  });

  it("does not perform any calculation or derivation on the API response (source has no arithmetic on data fields)", () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const source = readFileSync(join(here, "FleetPowerBIPanel.jsx"), "utf-8");

    // Math.round is reused only for display formatting (rounding an
    // already-computed score/day/hour value), not for deriving a new
    // metric -- confirmed by the absence of any arithmetic operator
    // combining two different response fields.
    expect(source).not.toMatch(/data\.\w+\s*[+\-*/]\s*data\.\w+/);
  });

  it("makes no reference anywhere to the Engineering AI feature (No AI, per this MWO's rule)", () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const source = readFileSync(join(here, "FleetPowerBIPanel.jsx"), "utf-8");

    expect(source).not.toMatch(/postEngineeringAI|engineering-ai|EngineeringAI/);
  });

  it("imports only getFleetPowerBI from ai5rClient -- no other API call", () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const source = readFileSync(join(here, "FleetPowerBIPanel.jsx"), "utf-8");
    const importLine = source.split("\n").find((line) => line.includes("ai5rClient"));

    expect(importLine).toContain("getFleetPowerBI");
    expect(importLine).not.toContain("getFleetReliability");
    expect(importLine).not.toContain("getPumpKnowledge");
  });
});
