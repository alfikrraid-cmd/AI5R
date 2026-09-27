import { describe, expect, it } from "vitest";
import {
  installedSealSummary,
  mapCurrentInstallation,
  mapCurrentInstallations,
  mapInstallationHistory,
} from "./currentInstallationMapping";

const INSTALLED = {
  installation_status: "INSTALLED",
  installed_seal_type: "T48MP",
  installed_seal_size: '2.3/8"',
  installed_seal_unit: null,
  seal_code: null,
  installation_date: "2026-05-07",
  installation_position: null,
  source_document: "SCAN 026 INSTALLATION REPORT 945-P-9B.pdf",
  source_installation_code: "INSTL-026-2026",
  removed_at: null,
  time_since_installation_days: 141,
  time_since_installation_hours: 3384,
  time_basis: "CALENDAR_TIME",
  time_precision: "DATE_ONLY",
  actual_operating_hours: null,
};

describe("mapCurrentInstallation", () => {
  it.each([null, undefined, {}])("an absent payload (%s) is NOT RECORDED, never inferred", (payload) => {
    const mapped = mapCurrentInstallation(payload);
    expect(mapped.status).toBe("NOT_RECORDED");
    expect(mapped.statusLabel).toBe("NOT RECORDED");
    expect(mapped.installedSealType).toBeUndefined();
    expect(mapped.installedSealSize).toBeUndefined();
    expect(mapped.daysSinceInstallation).toBeUndefined();
    expect(mapped.hoursSinceInstallation).toBeUndefined();
    expect(mapped.timeBasisLabel).toBe("Calendar Time");
    expect(mapped.timePrecisionLabel).toBeUndefined();
    expect(mapped.actualOperatingHours).toBeUndefined();
  });

  it("maps an installed, DATE_ONLY installation", () => {
    const mapped = mapCurrentInstallation(INSTALLED);
    expect(mapped).toMatchObject({
      status: "INSTALLED",
      statusLabel: "INSTALLED",
      installedSealType: "T48MP",
      installedSealSize: '2.3/8"',
      installedSealUnit: undefined,
      installationDate: "2026-05-07",
      sourceInstallationCode: "INSTL-026-2026",
      daysSinceInstallation: 141,
      hoursSinceInstallation: 3384,
      timeBasisLabel: "Calendar Time",
      timePrecisionLabel: "Date only",
    });
  });

  it("never passes through a negative or non-integer counter", () => {
    const mapped = mapCurrentInstallation({ ...INSTALLED, time_since_installation_days: -3, time_since_installation_hours: 1.5 });
    expect(mapped.daysSinceInstallation).toBeUndefined();
    expect(mapped.hoursSinceInstallation).toBeUndefined();
  });

  it("labels REMOVED", () => {
    expect(mapCurrentInstallation({ installation_status: "REMOVED", removed_at: "2026-08-01" })).toMatchObject({
      statusLabel: "REMOVED",
      removedAt: "2026-08-01",
    });
  });
});

describe("installedSealSummary", () => {
  it("shows the installed seal type, flagged as type only, when no unit is tracked", () => {
    expect(installedSealSummary(mapCurrentInstallation(INSTALLED))).toEqual({ value: "T48MP", typeOnly: true });
  });

  it("prefers a tracked seal unit", () => {
    expect(installedSealSummary(mapCurrentInstallation({ ...INSTALLED, installed_seal_unit: "UNIT-7" }))).toEqual({
      value: "UNIT-7",
      typeOnly: false,
    });
  });

  it.each([
    ["not recorded", null],
    ["removed", { installation_status: "REMOVED" }],
    ["installed without a type", { ...INSTALLED, installed_seal_type: null }],
  ])("is Not Recorded when %s", (_, payload) => {
    expect(installedSealSummary(mapCurrentInstallation(payload))).toEqual({ value: "Not Recorded", typeOnly: false });
  });
});

describe("lists", () => {
  it("maps per-position installations and history without synthesizing entries", () => {
    expect(mapCurrentInstallations(null)).toEqual([]);
    expect(mapInstallationHistory(undefined)).toEqual([]);
    expect(mapCurrentInstallations([{ ...INSTALLED, installation_position: "NDE" }])[0].position).toBe("NDE");
    expect(
      mapInstallationHistory([
        {
          installation_code: "INSTL-043-2026",
          installation_date: "2026-06-10",
          installed_seal_type: "T8B1",
          installed_seal_size: '5"',
          installed_seal_unit: null,
          installation_position: "NDE",
          source_document: "SCAN 043.pdf",
          report_no: "043/INSTL/TAP/06-2026",
        },
      ])
    ).toEqual([
      {
        code: "INSTL-043-2026",
        date: "2026-06-10",
        sealType: "T8B1",
        sealSize: '5"',
        sealUnit: undefined,
        position: "NDE",
        sourceDocument: "SCAN 043.pdf",
        reportNo: "043/INSTL/TAP/06-2026",
      },
    ]);
  });
});
