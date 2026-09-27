import { describe, expect, it } from "vitest";
import { formatInstallationDate, mapInstallationBasedMtbf } from "./installationMtbfMapping";

const INTERVAL = {
  pump_tag: "945-P-9B",
  position: "PUMP_LEVEL",
  previous_installation_code: "INSTL-022-2026",
  previous_installation_date: "2026-04-17",
  previous_seal_type: "T48MP",
  previous_seal_size: '2.3/8"',
  next_installation_code: "INSTL-026-2026",
  next_installation_date: "2026-05-07",
  next_seal_type: "T48MP",
  next_seal_size: '2.3/8"',
  mtbf_days: 20,
  mtbf_hours: 480,
  seal_identity_status: "CONFIRMED_SAME",
  comparability_status: "COMPARABLE",
  time_basis: "CALENDAR_TIME",
  precision: "DATE_ONLY",
};

describe("mapInstallationBasedMtbf", () => {
  it.each([null, undefined, {}])("an absent payload (%s) has no MTBF, never 0", (payload) => {
    expect(mapInstallationBasedMtbf(payload)).toEqual({ completedIntervalCount: 0, days: undefined, hours: undefined, intervals: [] });
  });

  it("maps a completed interval and the pump MTBF", () => {
    const mapped = mapInstallationBasedMtbf({
      completed_interval_count: 1,
      installation_based_mtbf_days: 20,
      installation_based_mtbf_hours: 480,
      intervals: [INTERVAL],
    });
    expect(mapped).toMatchObject({ completedIntervalCount: 1, days: 20, hours: 480 });
    expect(mapped.intervals[0]).toMatchObject({
      previousDate: "2026-04-17",
      nextDate: "2026-05-07",
      days: 20,
      hours: 480,
      previousSealSize: '2.3/8"',
      sealIdentityLabel: "Confirmed same",
    });
  });

  it("labels an unknown seal identity as not recorded", () => {
    const mapped = mapInstallationBasedMtbf({ intervals: [{ ...INTERVAL, seal_identity_status: "UNKNOWN" }] });
    expect(mapped.intervals[0].sealIdentityLabel).toBe("Not recorded");
  });

  it("formats plant calendar dates without a timezone shift", () => {
    expect(formatInstallationDate("2026-04-17")).toBe("17 Apr 2026");
    expect(formatInstallationDate("2026-05-07")).toBe("07 May 2026");
    expect(formatInstallationDate(null)).toBeUndefined();
  });
});
