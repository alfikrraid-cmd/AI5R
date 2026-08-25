import { afterEach, describe, expect, it, vi } from "vitest";

import { getPump } from "../../../api/ai5rClient";
import {
  mapConditionMonitoringReadingRecord,
  mapConditionMonitoringScheduleRecord,
  withResolvedArea,
} from "./conditionMonitoringMapping";

vi.mock("../../../api/ai5rClient", () => ({
  getPump: vi.fn(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("mapConditionMonitoringScheduleRecord", () => {
  it("renames API fields to the Condition Monitoring Schedule UI shape", () => {
    const mapped = mapConditionMonitoringScheduleRecord({
      condition_monitoring_schedule_code: "CMON-SCHED-001",
      asset_code: "641-P-5",
      frequency: "WEEKLY",
      applicable_parameters: ["mechseal_temp", "mechanical_seal_leak"],
    });

    expect(mapped.id).toBe("CMON-SCHED-001");
    expect(mapped.equipmentTag).toBe("641-P-5");
    expect(mapped.area).toBeNull();
    expect(mapped.frequency).toBe("WEEKLY");
    expect(mapped.applicableParameters).toEqual(["mechseal_temp", "mechanical_seal_leak"]);
  });

  it("never fabricates applicableParameters -- defaults to an empty array, not null", () => {
    const mapped = mapConditionMonitoringScheduleRecord({
      condition_monitoring_schedule_code: "CMON-SCHED-001",
    });

    expect(mapped.applicableParameters).toEqual([]);
    expect(() => mapped.applicableParameters.length).not.toThrow();
  });
});

describe("mapConditionMonitoringReadingRecord", () => {
  it("renames API fields to the Condition Monitoring Reading UI shape", () => {
    const mapped = mapConditionMonitoringReadingRecord({
      condition_monitoring_reading_code: "CMON-READ-101",
      condition_monitoring_schedule_code: "CMON-SCHED-001",
      asset_code: "641-P-5",
      reading_date: "2026-07-12T00:00:00.000Z",
      mechseal_temp_de: 84,
      mechseal_temp_nde: 79,
      suction_temp: 51,
      discharge_temp: 50,
      pump_operating_state: "Running",
      mechanical_seal_leak_de: true,
      mechanical_seal_leak_nde: false,
    });

    expect(mapped.id).toBe("CMON-READ-101");
    expect(mapped.scheduleCode).toBe("CMON-SCHED-001");
    expect(mapped.equipmentTag).toBe("641-P-5");
    expect(mapped.readingDate).toBe("2026-07-12");
    expect(mapped.mechsealTempDe).toBe(84);
    expect(mapped.mechsealTempNde).toBe(79);
    expect(mapped.suctionTemp).toBe(51);
    expect(mapped.dischargeTemp).toBe(50);
    expect(mapped.pumpOperatingState).toBe("Running");
    expect(mapped.leakDe).toBe(true);
    expect(mapped.leakNde).toBe(false);
  });

  it("preserves null/undefined leak flags as unknown, never fabricates false", () => {
    const mapped = mapConditionMonitoringReadingRecord({
      condition_monitoring_reading_code: "CMON-READ-102",
      condition_monitoring_schedule_code: "CMON-SCHED-001",
      mechanical_seal_leak_de: null,
    });

    expect(mapped.leakDe).toBeNull();
    expect(mapped.leakNde).toBeUndefined();
  });
});

describe("withResolvedArea", () => {
  it("reuses the existing Pump API to resolve area", async () => {
    getPump.mockResolvedValue({ tag_number: "641-P-5", area: "SWS Unit" });

    const result = await withResolvedArea({ equipmentTag: "641-P-5", area: null });

    expect(result).toEqual({ equipmentTag: "641-P-5", area: "SWS Unit" });
    expect(getPump).toHaveBeenCalledWith("641-P-5");
  });

  it("leaves area null without calling the API when equipmentTag is absent", async () => {
    const record = { equipmentTag: null, area: null };
    const result = await withResolvedArea(record);

    expect(result).toEqual(record);
    expect(getPump).not.toHaveBeenCalled();
  });

  it("leaves area at its safe default when the API call fails", async () => {
    getPump.mockRejectedValue(new Error("not found"));

    const record = { equipmentTag: "999-X-9", area: null };
    const result = await withResolvedArea(record);

    expect(result).toEqual(record);
  });
});
