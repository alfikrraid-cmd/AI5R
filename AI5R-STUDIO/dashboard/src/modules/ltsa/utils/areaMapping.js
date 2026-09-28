/**
 * Canonical Area -> Maintenance Area (MA) mapping, derived directly
 * from CORE-SERVICES/API/pump_area_scope.py (MA_AREA_GROUPS & _AREA_TOKEN_MAP).
 * MA1 = HOC
 * MA2 = HSC + S_PAKNING + HCC + FRAKSINASI + REAKTOR + H2PLAN + AMINE
 * MA3 = UTL
 * MA4 = OM
 *
 * Blank/null/unrecognized returns "—" (never guessed or fabricated).
 *
 * MWO-LTSA-CONTRACT-SCOPE-R4-6 -- FRAKSINASI/REAKTOR/H2PLAN/AMINE added
 * in lockstep with pump_area_scope.py's own identical patch (Chief
 * Architect approved, R4.4/R4.5, evidenced by the real Pertamina KAK
 * "TECHNICAL SERVICE AGREEMENT PEMELIHARAAN/PENGGANTIAN MECHANICAL SEAL
 * JOHN CRANE UNTUK POMPA AREA HCC RU II DUMAI PT. KILANG PERTAMINA
 * INTERNASIONAL", REV.1, WO No.8202224810, PR No.500049116) -- real
 * HCC-internal process sections, not a fourth physical complex.
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
  if (token === "FRAKSINASI") return "FRAKSINASI";
  if (token === "REAKTOR") return "REAKTOR";
  // "H2Plan" and "H2 PLAN" differ by an internal space that .toUpperCase()
  // alone does not remove -- both normalize to one canonical token, same
  // reasoning as the S_PAKNING family's own multiple literal variants.
  if (token === "H2PLAN" || token === "H2 PLAN") return "H2PLAN";
  if (token === "AMINE") return "AMINE";
  return token;
}

export function resolveAreaMA(area) {
  const normalized = normalizeAreaToken(area);
  if (!normalized) return "—";
  if (normalized === "HOC") return "MA1";
  if (
    normalized === "HSC" ||
    normalized === "S_PAKNING" ||
    normalized === "HCC" ||
    normalized === "FRAKSINASI" ||
    normalized === "REAKTOR" ||
    normalized === "H2PLAN" ||
    normalized === "AMINE"
  ) {
    return "MA2";
  }
  if (normalized === "UTL") return "MA3";
  if (normalized === "OM") return "MA4";
  return "—";
}

