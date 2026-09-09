/**
 * Canonical Area -> Maintenance Area (MA) mapping, derived directly
 * from CORE-SERVICES/API/pump_area_scope.py (MA_AREA_GROUPS & _AREA_TOKEN_MAP).
 * MA1 = HOC
 * MA2 = HSC + S_PAKNING + HCC
 * MA3 = UTL
 * MA4 = OM
 *
 * Blank/null/unrecognized returns "—" (never guessed or fabricated).
 */

export function normalizeAreaToken(area) {
  if (!area) return null;
  const token = String(area).trim().toUpperCase();
  if (token === "HOC") return "HOC";
  if (token === "HSC") return "HSC";
  if (token === "HCC") return "HCC";
  if (token === "OM" || token === "OIL MOVEMENT") return "OM";
  if (token === "UTL" || token === "UTILITIES") return "UTL";
  if (
    token === "S_PAKNING" ||
    token === "S. PAKNING" ||
    token === "S.PAKNING" ||
    token === "S PAKNING" ||
    token === "SPAKNING" ||
    token === "SPK"
  ) {
    return "S_PAKNING";
  }
  return token;
}

export function resolveAreaMA(area) {
  const normalized = normalizeAreaToken(area);
  if (!normalized) return "—";
  if (normalized === "HOC") return "MA1";
  if (normalized === "HSC" || normalized === "S_PAKNING" || normalized === "HCC") return "MA2";
  if (normalized === "UTL") return "MA3";
  if (normalized === "OM") return "MA4";
  return "—";
}

