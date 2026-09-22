import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PumpOpenDesignView from "./PumpOpenDesignView";

const BASE_PUMP = {
  tag: "945-P-7A",
  name: "LPG LOADING PUMP",
  area: "OM Area",
  status: "RUNNING",
  criticality: "HIGH",
};

describe("PumpOpenDesignView Current Status canonical activity", () => {
  it("renders canonical activity for benchmark 945-P-7A in Current Status", () => {
    const lifecycle = {
      tagNumber: "945-P-7A",
      currentState: {
        lastPm: {
          event_date: "2026-06-03",
          event_code: "PMOCC-0730E69FB540",
          source: "PM_OCCURRENCE",
        },
        nextPm: null,
        lastConditionMonitoring: {
          event_date: "2026-04-20",
          event_code: "CMONR-F7A3F442C323",
          source: "CONDITION_MONITORING_READING",
        },
        lastSealReplacement: {
          event_date: "2026-05-29",
          event_code: "INSTL-036-2026",
          installation_outcome: "UNKNOWN",
          installation_mode: "UNKNOWN",
          seal_identity: "2648-2 Tandem Seal 55 MM",
          reference: "INSTL-036-2026",
        },
        lastConfirmedSealFailure: null,
        openWorkOrders: [],
      },
      timeline: [],
      analytics: {
        pmCount: 4,
        cmCount: 4,
        failureCount: 0,
      },
    };

    render(
      <PumpOpenDesignView
        pump={BASE_PUMP}
        lifecycle={lifecycle}
        lifecycleLoading={false}
        sealInventoryGroups={[]}
      />
    );

    // Switch to Performance tab
    fireEvent.click(screen.getByRole("tab", { name: "Performance" }));

    // Check Current Status labels and values
    expect(screen.getByText("Last PM")).toBeTruthy();
    expect(screen.getByText("03 Jun 2026")).toBeTruthy();

    expect(screen.getByText("Next PM")).toBeTruthy();

    expect(screen.getByText("Last Condition Monitoring")).toBeTruthy();
    expect(screen.getByText("20 Apr 2026")).toBeTruthy();

    expect(screen.getByText("Last Seal Replacement")).toBeTruthy();
    // UNKNOWN outcome must display date only -- NEVER "Mode N/A", "Unknown", or "UNKNOWN"
    expect(screen.getByText("29 May 2026")).toBeTruthy();
    expect(screen.queryByText(/Mode N\/A/)).toBeNull();
    expect(screen.queryByText(/Unknown/)).toBeNull();

    expect(screen.getByText("Last Confirmed Seal Failure")).toBeTruthy();

    // Verify N/A rendered for missing fields (Next PM, Last Confirmed Seal Failure)
    const naElements = screen.getAllByText("N/A");
    expect(naElements.length).toBeGreaterThanOrEqual(2);
  });

  it("renders 'New Seal' suffix when installation_outcome is NEW_SEAL", () => {
    const lifecycle = {
      tagNumber: "945-P-7A",
      currentState: {
        lastPm: null,
        nextPm: null,
        lastConditionMonitoring: null,
        lastSealReplacement: {
          event_date: "2026-05-29",
          installation_outcome: "NEW_SEAL",
          reference: "INSTL-036-2026",
        },
        lastConfirmedSealFailure: null,
        openWorkOrders: [],
      },
      timeline: [],
      analytics: { pmCount: 0, cmCount: 0, failureCount: 0 },
    };

    render(
      <PumpOpenDesignView
        pump={BASE_PUMP}
        lifecycle={lifecycle}
        lifecycleLoading={false}
        sealInventoryGroups={[]}
      />
    );

    fireEvent.click(screen.getByRole("tab", { name: "Performance" }));
    expect(screen.getByText("29 May 2026 · New Seal")).toBeTruthy();
  });

  it("renders 'Reuse Seal' suffix when installation_outcome is REUSE_SEAL", () => {
    const lifecycle = {
      tagNumber: "945-P-7A",
      currentState: {
        lastPm: null,
        nextPm: null,
        lastConditionMonitoring: null,
        lastSealReplacement: {
          event_date: "2026-05-29",
          installation_outcome: "REUSE_SEAL",
          reference: "INSTL-036-2026",
        },
        lastConfirmedSealFailure: null,
        openWorkOrders: [],
      },
      timeline: [],
      analytics: { pmCount: 0, cmCount: 0, failureCount: 0 },
    };

    render(
      <PumpOpenDesignView
        pump={BASE_PUMP}
        lifecycle={lifecycle}
        lifecycleLoading={false}
        sealInventoryGroups={[]}
      />
    );

    fireEvent.click(screen.getByRole("tab", { name: "Performance" }));
    expect(screen.getByText("29 May 2026 · Reuse Seal")).toBeTruthy();
  });

  it("renders date only when installation_outcome is UNKNOWN", () => {
    const lifecycle = {
      tagNumber: "945-P-7A",
      currentState: {
        lastPm: null,
        nextPm: null,
        lastConditionMonitoring: null,
        lastSealReplacement: {
          event_date: "2026-05-29",
          installation_outcome: "UNKNOWN",
          reference: "INSTL-036-2026",
        },
        lastConfirmedSealFailure: null,
        openWorkOrders: [],
      },
      timeline: [],
      analytics: { pmCount: 0, cmCount: 0, failureCount: 0 },
    };

    render(
      <PumpOpenDesignView
        pump={BASE_PUMP}
        lifecycle={lifecycle}
        lifecycleLoading={false}
        sealInventoryGroups={[]}
      />
    );

    fireEvent.click(screen.getByRole("tab", { name: "Performance" }));
    expect(screen.getByText("29 May 2026")).toBeTruthy();
    expect(screen.queryByText(/Mode N\/A/)).toBeNull();
    expect(screen.queryByText(/Unknown/)).toBeNull();
  });

  it("renders N/A for Last Seal Replacement when no replacement event exists", () => {
    const lifecycle = {
      tagNumber: "945-P-7A",
      currentState: {
        lastPm: null,
        nextPm: null,
        lastConditionMonitoring: null,
        lastSealReplacement: null,
        lastConfirmedSealFailure: null,
        openWorkOrders: [],
      },
      timeline: [],
      analytics: { pmCount: 0, cmCount: 0, failureCount: 0 },
    };

    render(
      <PumpOpenDesignView
        pump={BASE_PUMP}
        lifecycle={lifecycle}
        lifecycleLoading={false}
        sealInventoryGroups={[]}
      />
    );

    fireEvent.click(screen.getByRole("tab", { name: "Performance" }));
    const naList = screen.getAllByText("N/A");
    expect(naList.length).toBe(5); // all 5 Current Status items are N/A
  });

  it("Case H: legacy cm_report present but no condition_monitoring_reading -> Last Condition Monitoring displays N/A", () => {
    const lifecycle = {
      tagNumber: "945-P-7A",
      currentState: {
        lastPm: null,
        nextPm: null,
        lastConditionMonitoring: null, // strictly null when no condition_monitoring_reading
        lastCm: {
          event_date: "2026-04-20",
          cm_report_code: "CM-LEGACY-001",
          source: "CM_REPORT",
        },
        lastSealReplacement: null,
        lastConfirmedSealFailure: null,
        openWorkOrders: [],
      },
      timeline: [],
      analytics: { pmCount: 0, cmCount: 0, failureCount: 0 },
    };

    render(
      <PumpOpenDesignView
        pump={BASE_PUMP}
        lifecycle={lifecycle}
        lifecycleLoading={false}
        sealInventoryGroups={[]}
      />
    );

    fireEvent.click(screen.getByRole("tab", { name: "Performance" }));
    // Must NOT display legacy cm_report date or code
    expect(screen.queryByText("20 Apr 2026")).toBeNull();
    expect(screen.queryByText(/CM-LEGACY-001/)).toBeNull();
  });
});
