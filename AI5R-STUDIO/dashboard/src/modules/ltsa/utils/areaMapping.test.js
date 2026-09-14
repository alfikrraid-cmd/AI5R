import { describe, expect, it } from "vitest";
import { normalizeAreaToken, resolveAreaMA } from "./areaMapping";

/**
 * MWO-LTSA-CONTRACT-SCOPE-R4-6 -- frontend equivalence coverage for the
 * exact mapping semantics already proven backend-side
 * (CORE-SERVICES/API/TESTS/test_pump_area_scope.py's own
 * TestResolveAreaMAHCCSubareaPatch). No dedicated test file existed for
 * areaMapping.js before this MWO -- created fresh, same convention as
 * every other LTSA utils/*.test.js file in this module.
 */
describe("areaMapping -- canonical MA resolution", () => {
  it("HOC is MA1", () => {
    expect(resolveAreaMA("HOC")).toBe("MA1");
  });

  it("HCC and HSC are MA2", () => {
    expect(resolveAreaMA("HCC")).toBe("MA2");
    expect(resolveAreaMA("HSC")).toBe("MA2");
  });

  it("SPK and S_PAKNING are MA2", () => {
    expect(resolveAreaMA("SPK")).toBe("MA2");
    expect(resolveAreaMA("S_PAKNING")).toBe("MA2");
  });

  it("FRAKSINASI is MA2 (MWO-LTSA-CONTRACT-SCOPE-R4-6)", () => {
    expect(resolveAreaMA("FRAKSINASI")).toBe("MA2");
  });

  it("REAKTOR case variants are MA2", () => {
    expect(resolveAreaMA("REAKTOR")).toBe("MA2");
    expect(resolveAreaMA("Reaktor")).toBe("MA2");
  });

  it("H2Plan spacing variants are MA2", () => {
    expect(resolveAreaMA("H2Plan")).toBe("MA2");
    expect(resolveAreaMA("H2 PLAN")).toBe("MA2");
  });

  it("AMINE is MA2", () => {
    expect(resolveAreaMA("AMINE")).toBe("MA2");
  });

  it("UTL and UTILITIES are MA3", () => {
    expect(resolveAreaMA("UTL")).toBe("MA3");
    expect(resolveAreaMA("UTILITIES")).toBe("MA3");
  });

  it("OM and OIL MOVEMENT are MA4", () => {
    expect(resolveAreaMA("OM")).toBe("MA4");
    expect(resolveAreaMA("OIL MOVEMENT")).toBe("MA4");
  });

  it("unknown/blank areas return the honest N/A dash, never guessed", () => {
    expect(resolveAreaMA("DCU")).toBe("—");
    expect(resolveAreaMA("NOT_A_REAL_AREA")).toBe("—");
    expect(resolveAreaMA(null)).toBe("—");
    expect(resolveAreaMA("")).toBe("—");
  });

  it("case and whitespace normalization matches the backend exactly", () => {
    expect(normalizeAreaToken("  hcc  ")).toBe("HCC");
    expect(normalizeAreaToken("reaktor")).toBe("REAKTOR");
    expect(normalizeAreaToken("h2plan")).toBe("H2PLAN");
    expect(normalizeAreaToken("h2 plan")).toBe("H2PLAN");
    expect(resolveAreaMA("  hcc  ")).toBe("MA2");
    expect(resolveAreaMA("reaktor")).toBe("MA2");
  });
});
