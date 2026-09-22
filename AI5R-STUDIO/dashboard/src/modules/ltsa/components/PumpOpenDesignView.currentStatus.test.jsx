import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PumpOpenDesignView from "./PumpOpenDesignView";

const BASE_PUMP = {
  tag: "945-P-7A",
  name: "LPG LOADING PUMP",
  area: "OM Area",
  status: "RUNNING",
  criticality: "HIGH",
};

describe("PumpOpenDesignView Current Status canonical activity", () => {
  it("renders canonical activity for 945-P-7A in Current Status", () => {
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
    expect(screen.getByText("PMOCC-0730E69FB540 · 2026-06-03")).toBeTruthy();

    expect(screen.getByText("Next PM")).toBeTruthy();

    expect(screen.getByText("Last Condition Monitoring")).toBeTruthy();
    expect(screen.getByText("CMONR-F7A3F442C323 · 2026-04-20")).toBeTruthy();

    expect(screen.getByText("Last Seal Replacement")).toBeTruthy();
    expect(screen.getByText("2026-05-29 · Mode N/A")).toBeTruthy();

    expect(screen.getByText("Last Confirmed Seal Failure")).toBeTruthy();
  });
});
