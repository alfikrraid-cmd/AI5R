// LTSA_INSTALLATION_BASED_MTBF_R1 -- maps the Knowledge API's
// `installation_based_mtbf` (backend installation_interval_contract): the
// pump's completed installation-to-installation intervals in calendar time.
// A temporary proxy, never the failure-based mtbf_days and never Current
// Service Age. No interval -> MTBF not available (never 0, never derived).

const IDENTITY_LABELS = {
  CONFIRMED_SAME: "Confirmed same",
  CHANGED: "Changed",
  UNKNOWN: "Not recorded",
};

function numberOrUndefined(value) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : undefined;
}

// "2026-04-17" -> "17 Apr 2026" (the plant calendar date as recorded; a
// date-only value is formatted in UTC so no timezone shift can move it).
export function formatInstallationDate(value) {
  if (!value) return undefined;
  const day = String(value).slice(0, 10);
  const parsed = new Date(`${day}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).format(parsed);
}

function mapInterval(interval) {
  return {
    key: `${interval.previous_installation_code}->${interval.next_installation_code}`,
    position: interval.position,
    previousCode: interval.previous_installation_code,
    previousDate: interval.previous_installation_date,
    previousSealType: interval.previous_seal_type ?? undefined,
    previousSealSize: interval.previous_seal_size ?? undefined,
    nextCode: interval.next_installation_code,
    nextDate: interval.next_installation_date,
    nextSealType: interval.next_seal_type ?? undefined,
    nextSealSize: interval.next_seal_size ?? undefined,
    days: numberOrUndefined(interval.mtbf_days),
    hours: numberOrUndefined(interval.mtbf_hours),
    sealIdentityStatus: interval.seal_identity_status,
    sealIdentityLabel: IDENTITY_LABELS[interval.seal_identity_status] ?? "Not recorded",
  };
}

export function mapInstallationBasedMtbf(payload) {
  const intervals = (payload?.intervals ?? []).map(mapInterval);
  return {
    completedIntervalCount: Number.isInteger(payload?.completed_interval_count) ? payload.completed_interval_count : 0,
    days: numberOrUndefined(payload?.installation_based_mtbf_days),
    hours: numberOrUndefined(payload?.installation_based_mtbf_hours),
    intervals,
  };
}
