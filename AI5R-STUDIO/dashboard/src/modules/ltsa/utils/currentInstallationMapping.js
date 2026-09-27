// LTSA_ASSET360_CURRENT_INSTALLATION_AND_SERVICE_AGE_R1 -- maps the Knowledge
// API's `current_installation`, `current_installations` and
// `installation_history` (backend current_installation_contract: attributed by
// installation_report.pump_tag_number, installation evidence only). Nothing
// here is derived or re-selected: an absent payload is NOT_RECORDED, never
// filled from the configured seal, compatibility, or the seal catalog status.

export const INSTALLATION_STATUS = {
  INSTALLED: "INSTALLED",
  NOT_RECORDED: "NOT_RECORDED",
  REMOVED: "REMOVED",
};

const STATUS_LABELS = {
  [INSTALLATION_STATUS.INSTALLED]: "INSTALLED",
  [INSTALLATION_STATUS.NOT_RECORDED]: "NOT RECORDED",
  [INSTALLATION_STATUS.REMOVED]: "REMOVED",
};

const PRECISION_LABELS = { DATE_ONLY: "Date only", TIMESTAMP: "Timestamp" };
const BASIS_LABELS = { CALENDAR_TIME: "Calendar Time" };

function countOrUndefined(value) {
  return Number.isInteger(value) && value >= 0 ? value : undefined;
}

export function mapCurrentInstallation(payload) {
  const status = payload?.installation_status ?? INSTALLATION_STATUS.NOT_RECORDED;
  return {
    status,
    statusLabel: STATUS_LABELS[status] ?? status,
    installedSealType: payload?.installed_seal_type ?? undefined,
    // R1.1 -- installation_report.seal_size of the selected report, source
    // text verbatim (e.g. 4.1/2", 55 MM); never converted or re-derived.
    installedSealSize: payload?.installed_seal_size ?? undefined,
    installedSealUnit: payload?.installed_seal_unit ?? undefined,
    sealCode: payload?.seal_code ?? undefined,
    installationDate: payload?.installation_date ?? undefined,
    position: payload?.installation_position ?? undefined,
    sourceDocument: payload?.source_document ?? undefined,
    sourceInstallationCode: payload?.source_installation_code ?? undefined,
    removedAt: payload?.removed_at ?? undefined,
    daysSinceInstallation: countOrUndefined(payload?.time_since_installation_days),
    hoursSinceInstallation: countOrUndefined(payload?.time_since_installation_hours),
    timeBasisLabel: BASIS_LABELS[payload?.time_basis] ?? BASIS_LABELS.CALENDAR_TIME,
    timePrecisionLabel: PRECISION_LABELS[payload?.time_precision] ?? undefined,
    actualOperatingHours: countOrUndefined(payload?.actual_operating_hours),
  };
}

export function mapCurrentInstallations(payloads) {
  return (payloads ?? []).map(mapCurrentInstallation);
}

export function mapInstallationHistory(events) {
  return (events ?? []).map((event) => ({
    code: event.installation_code,
    date: event.installation_date ?? undefined,
    sealType: event.installed_seal_type ?? undefined,
    sealSize: event.installed_seal_size ?? undefined,
    sealUnit: event.installed_seal_unit ?? undefined,
    position: event.installation_position ?? undefined,
    sourceDocument: event.source_document ?? undefined,
    reportNo: event.report_no ?? undefined,
  }));
}

// Header KPI "Installed Seal": the tracked physical unit when evidenced,
// otherwise the installed seal TYPE, flagged so it never reads as a
// uniquely tracked unit.
export function installedSealSummary(currentInstallation) {
  if (currentInstallation?.status !== INSTALLATION_STATUS.INSTALLED) {
    return { value: "Not Recorded", typeOnly: false };
  }
  if (currentInstallation.installedSealUnit) {
    return { value: currentInstallation.installedSealUnit, typeOnly: false };
  }
  if (currentInstallation.installedSealType) {
    return { value: currentInstallation.installedSealType, typeOnly: true };
  }
  return { value: "Not Recorded", typeOnly: false };
}
