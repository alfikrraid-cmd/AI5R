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

  it("maps canonical Current Status fields (Last PM, Condition Monitoring, Seal Replacement)", () => {
    const lifecycle = mapPumpLifecycleRecord({
      success: true,
      data: {
        tag_number: "945-P-7A",
        current_state: {
          current_installation: null,
          current_seal: null,
          elapsed_service_days: 10,
          running_hours_derived: null,
          last_pm: {
            event_date: "2026-06-03",
            event_code: "PMOCC-0730E69FB540",
            source: "PM_OCCURRENCE",
          },
          next_pm: null,
          last_condition_monitoring: {
            event_date: "2026-04-20",
            event_code: "CMONR-F7A3F442C323",
            source: "CONDITION_MONITORING_READING",
          },
          last_seal_replacement: {
            event_date: "2026-05-29",
            event_code: "INSTL-036-2026",
            installation_mode: "UNKNOWN",
            seal_identity: "2648-2 Tandem Seal 55 MM",
            reference: "INSTL-036-2026",
          },
          last_confirmed_seal_failure: null,
          last_cm: null,
          last_failure: null,
          open_work_orders: [],
        },
        timeline: [],
        analytics: null,
        related_engineering: null,
      },
    });

    const cs = lifecycle.currentState;
    expect(cs.lastPm).toEqual({
      event_date: "2026-06-03",
      event_code: "PMOCC-0730E69FB540",
      source: "PM_OCCURRENCE",
    });
    expect(cs.lastConditionMonitoring).toEqual({
      event_date: "2026-04-20",
      event_code: "CMONR-F7A3F442C323",
      source: "CONDITION_MONITORING_READING",
    });
    expect(cs.lastSealReplacement).toEqual({
      event_date: "2026-05-29",
      event_code: "INSTL-036-2026",
      installation_mode: "UNKNOWN",
      seal_identity: "2648-2 Tandem Seal 55 MM",
      reference: "INSTL-036-2026",
    });
    expect(cs.lastConfirmedSealFailure).toBeNull();
    expect(cs.nextPm).toBeNull();
  });
});