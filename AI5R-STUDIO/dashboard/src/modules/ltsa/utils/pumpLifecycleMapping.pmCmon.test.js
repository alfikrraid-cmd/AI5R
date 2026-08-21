import { describe, expect, it } from "vitest";
import { mapPumpLifecycleRecord } from "./pumpLifecycleMapping";

describe("mapPumpLifecycleRecord PM/CMON timeline", () => {
  it("passes backend PM and CMON events through without synthesizing or coercing payload values", () => {
    const lifecycle = mapPumpLifecycleRecord({
      success: true,
      data: {
        tag_number: "110-P-10",
        current_state: null,
        timeline: [
          {
            id: "PM:PM-110-P-10-0",
            event_type: "PM",
            occurred_at: "2026-07-01",
            title: "PM Occurrence PM-110-P-10-0",
            description: null,
            severity: "UNKNOWN",
            source: "PM_OCCURRENCE",
            derived: true,
            payload: { pm_occurrence_code: "PM-110-P-10-0", asset_code: "110-P-10", remarks: null },
          },
          {
            id: "INSPECTION:CMON-110-P-10-0",
            event_type: "INSPECTION",
            occurred_at: "2026-08-01",
            title: "Condition Monitoring CMON-110-P-10-0",
            description: "Finding text",
            severity: "UNKNOWN",
            source: "CONDITION_MONITORING_READING",
            derived: true,
            payload: {
              condition_monitoring_reading_code: "CMON-110-P-10-0",
              asset_code: "110-P-10",
              pump_operating_state: null,
              suction_pressure: 0,
              mechanical_seal_leak_de: false,
            },
          },
        ],
        analytics: null,
        related_engineering: null,
      },
    });

    expect(lifecycle.timeline.map((event) => event.source)).toEqual(["PM_OCCURRENCE", "CONDITION_MONITORING_READING"]);
    expect(lifecycle.timeline[0].payload.remarks).toBeNull();
    expect(lifecycle.timeline[1].payload.pump_operating_state).toBeNull();
    expect(lifecycle.timeline[1].payload.suction_pressure).toBe(0);
    expect(lifecycle.timeline[1].payload.mechanical_seal_leak_de).toBe(false);
  });
});