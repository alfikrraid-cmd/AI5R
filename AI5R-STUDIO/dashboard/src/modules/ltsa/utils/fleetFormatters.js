// MWO-LTSA-040A -- shared formatters, extracted from the identical set
// FleetReliabilityPanel.jsx (037D) and FleetPowerBIPanel.jsx (038B) each
// independently defined. One source, reused by every panel that displays
// a Fleet Reliability / Fleet Power BI number -- no third copy.
export const UNAVAILABLE = "Unavailable";

export function formatScore(value) {
  return value === null || value === undefined ? UNAVAILABLE : String(Math.round(value));
}

export function formatDays(value) {
  return value === null || value === undefined ? UNAVAILABLE : `${Math.round(value)} days`;
}

export function formatHours(value) {
  return value === null || value === undefined ? UNAVAILABLE : `${Math.round(value)} hrs`;
}

export function formatPercent(value) {
  return value === null || value === undefined ? UNAVAILABLE : `${value}%`;
}
