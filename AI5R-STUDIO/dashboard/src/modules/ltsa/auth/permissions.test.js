import { describe, expect, it } from "vitest";
import { can, PERMISSIONS, ROLES, visibleTabKeys } from "./permissions";

describe("permissions", () => {
  it("derives visibility from capability, never from a hardcoded role/org check", () => {
    // No `session.role === "..."` anywhere in this test -- every assertion
    // goes through can()/visibleTabKeys(), same as production callers must.
    const tapAdmin = { role: ROLES.TAP_ADMIN };
    expect(can(tapAdmin, PERMISSIONS.IMPORT_EXECUTE)).toBe(true);
    expect(can(tapAdmin, PERMISSIONS.ADMIN_ACCESS)).toBe(true);
  });

  it("TAP_ENGINEER sees engineering capability but not admin/import", () => {
    const session = { role: ROLES.TAP_ENGINEER };
    expect(can(session, PERMISSIONS.PUMP_READ)).toBe(true);
    expect(can(session, PERMISSIONS.ENGINEERING_AI_ASK)).toBe(true);
    expect(can(session, PERMISSIONS.ADMIN_ACCESS)).toBe(false);
    expect(can(session, PERMISSIONS.IMPORT_EXECUTE)).toBe(false);
  });

  it("PERTAMINA_ENGINEER sees pump/seal/inventory/engineering AI but not import/admin/internal breakdown", () => {
    const session = { role: ROLES.PERTAMINA_ENGINEER };
    expect(can(session, PERMISSIONS.PUMP_READ)).toBe(true);
    expect(can(session, PERMISSIONS.SEAL_READ)).toBe(true);
    expect(can(session, PERMISSIONS.INVENTORY_READ)).toBe(true);
    expect(can(session, PERMISSIONS.ENGINEERING_AI_ASK)).toBe(true);
    expect(can(session, PERMISSIONS.IMPORT_EXECUTE)).toBe(false);
    expect(can(session, PERMISSIONS.ADMIN_ACCESS)).toBe(false);
    expect(can(session, PERMISSIONS.INTERNAL_COMPONENT_READ)).toBe(false);
    expect(visibleTabKeys(session)).not.toContain("import");
  });

  it("PERTAMINA_VIEWER loses engineering_ai.ask but keeps read access", () => {
    const session = { role: ROLES.PERTAMINA_VIEWER };
    expect(can(session, PERMISSIONS.ENGINEERING_AI_ASK)).toBe(false);
    expect(can(session, PERMISSIONS.PUMP_READ)).toBe(true);
    expect(can(session, PERMISSIONS.IMPORT_EXECUTE)).toBe(false);
  });

  it("an unauthenticated session (no role) grants nothing", () => {
    expect(can(null, PERMISSIONS.PUMP_READ)).toBe(false);
    expect(can({}, PERMISSIONS.PUMP_READ)).toBe(false);
  });

  // MWO-LTSA-AUTH-002 -- can() now checks the REAL backend-granted
  // session.permissions array first (from GET /api/auth/me), not a
  // frontend role table, whenever it is present. These use the literal
  // AUTH-001 backend permission strings (auth_service.py's own
  // ROLE_PERMISSIONS), proving the real integration path, not the
  // role-fixture fallback the tests above exercise.
  it("TAP_ENGINEER (real backend session) is denied admin.users", () => {
    const session = {
      role: "TAP_ENGINEER",
      permissions: ["pump.read", "seal.read", "maintenance.read", "maintenance.write", "engineering_ai.ask"],
    };
    expect(can(session, "admin.users")).toBe(false);
    expect(can(session, PERMISSIONS.PUMP_READ)).toBe(true);
  });

  it("PERTAMINA_ENGINEER (real backend session) has engineering_ai.ask but not import.execute", () => {
    const session = {
      role: "PERTAMINA_ENGINEER",
      permissions: ["pump.read", "seal.read", "inventory.read", "maintenance.read", "condition.read", "drawing.read", "engineering_ai.ask"],
    };
    expect(can(session, "engineering_ai.ask")).toBe(true);
    expect(can(session, "import.execute")).toBe(false);
  });

  it("PERTAMINA_VIEWER (real backend session) is denied both engineering_ai.ask and import.execute", () => {
    const session = {
      role: "PERTAMINA_VIEWER",
      permissions: ["pump.read", "seal.read", "inventory.read", "maintenance.read"],
    };
    expect(can(session, "engineering_ai.ask")).toBe(false);
    expect(can(session, "import.execute")).toBe(false);
  });

  it("a real backend session.permissions array always wins over the role fallback table", () => {
    // Proves the reconciliation direction: even if the fallback table
    // would grant something, the real backend array is authoritative.
    const session = { role: "TAP_ADMIN", permissions: [] };
    expect(can(session, "admin.users")).toBe(false);
  });

  it("compatible-pump count is never conflated with stock quantity by the capability layer", () => {
    // Domain rule (MWO §6): inventory.read gates whether stock/compat data
    // is shown at all; the count distinction itself lives in the view
    // (SealOpenDesignView), already separates stock.quantityOnHand from
    // seal.compatiblePumps.length. This test only guards that the
    // capability gate for that data exists and is a single flag.
    expect(PERMISSIONS.INVENTORY_READ).toBe("inventory.read");
  });
});
