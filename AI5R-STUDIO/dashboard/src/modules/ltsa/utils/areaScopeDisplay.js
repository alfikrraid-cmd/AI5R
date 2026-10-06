/**
 * Format data scope into human-friendly string for display in LTSA Profile & UI.
 *
 * Rules:
 * - dataScopeType === 'ALL' -> "All Areas"
 * - dataScopeType === 'AREA' and value present -> value
 * - dataScopeType === 'MA' and value present -> value
 * - else -> "No Area Access / Not Assigned"
 *
 * CRITICAL:
 * Never display NULL or empty as "All Areas".
 * Only explicit ALL can display "All Areas".
 */
export function formatAreaScopeDisplay(dataScopeType, dataScopeValue) {
  if (dataScopeType === "ALL") {
    return "All Areas";
  }
  if ((dataScopeType === "AREA" || dataScopeType === "MA") && dataScopeValue && String(dataScopeValue).trim()) {
    return String(dataScopeValue).trim();
  }
  return "No Area Access / Not Assigned";
}
