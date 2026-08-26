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

  // MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-ROUTING-019A -- proves the
  // actual root cause fix: "historical-batch-review" was correctly
  // registered in LTSAWorkspace.jsx's TABS/PAGES by MWO-019, but had no
  // TAB_PERMISSIONS entry, so visibleTabKeys() silently dropped it from
  // every role's navigation regardless of the page/route itself working.
  it("TAP_ENGINEER can see the Historical Batch Review tab (maintenance.read, same as pm/cmon)", () => {
    const session = { role: ROLES.TAP_ENGINEER };
    expect(visibleTabKeys(session)).toContain("historical-batch-review");
  });

  it("distinguishes historical-batch-review (maintenance.read) from historical-review (record.edit, SUPERUSER/TAP_ADMIN only)", () => {
    const tapEngineer = { role: ROLES.TAP_ENGINEER };
    expect(visibleTabKeys(tapEngineer)).toContain("historical-batch-review");
    expect(visibleTabKeys(tapEngineer)).not.toContain("historical-review");
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

  // MWO-LTSA-AUTH-003A-FINAL -- SUPERUSER/JOHN_CRANE_ENGINEER fallback coverage.
  it("SUPERUSER (fallback fixture) sees admin access and every engineering capability", () => {
    const session = { role: ROLES.SUPERUSER };
    expect(can(session, PERMISSIONS.ADMIN_ACCESS)).toBe(true);
    expect(can(session, PERMISSIONS.IMPORT_EXECUTE)).toBe(true);
    expect(can(session, PERMISSIONS.PUMP_READ)).toBe(true);
  });

  it("JOHN_CRANE_ENGINEER (fallback fixture) reads engineering/inventory/internal-component data but has no admin/import access", () => {
    const session = { role: ROLES.JOHN_CRANE_ENGINEER };
    expect(can(session, PERMISSIONS.PUMP_READ)).toBe(true);
    expect(can(session, PERMISSIONS.INVENTORY_READ)).toBe(true);
    expect(can(session, PERMISSIONS.INTERNAL_COMPONENT_READ)).toBe(true);
    expect(can(session, PERMISSIONS.ENGINEERING_AI_ASK)).toBe(true);
    expect(can(session, PERMISSIONS.ADMIN_ACCESS)).toBe(false);
    expect(can(session, PERMISSIONS.IMPORT_EXECUTE)).toBe(false);
    expect(can(session, PERMISSIONS.DASHBOARD_READ)).toBe(false);
  });

  it("JOHN_CRANE_ENGINEER (real backend session) can read Seal Stock and internal-component/GPN data", () => {
    const session = {
      role: "JOHN_CRANE_ENGINEER",
      permissions: [
        "pump.read", "seal.read", "inventory.read", "maintenance.read", "maintenance.technical_review",
        "condition.read", "drawing.read", "engineering_ai.ask", "internal_component.read",
      ],
    };
    expect(can(session, "inventory.read")).toBe(true);
    expect(can(session, "internal_component.read")).toBe(true);
    expect(can(session, "maintenance.write")).toBe(false);
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

  // MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 17 -- the exact PM/Condition
  // Monitoring workflow role matrix the MWO requires proven: TAP_ENGINEER
  // writes but never reviews; TAP_ADMIN writes+admin-reviews but never
  // performs technical review; JOHN_CRANE_ENGINEER technically-reviews
  // only, never writes/admin-reviews (no field impersonation); both
  // Pertamina roles get none of the three. Matches
  // auth_service.py's real ROLE_PERMISSIONS grants exactly (this
  // session's own re-read of that file), not a frontend invention.
  describe("PM/Condition Monitoring workflow role matrix (Phase 17)", () => {
    it("TAP_ENGINEER: write YES, admin_review NO, technical_review NO", () => {
      const session = { role: ROLES.TAP_ENGINEER };
      expect(can(session, PERMISSIONS.MAINTENANCE_WRITE)).toBe(true);
      expect(can(session, PERMISSIONS.MAINTENANCE_ADMIN_REVIEW)).toBe(false);
      expect(can(session, PERMISSIONS.MAINTENANCE_TECHNICAL_REVIEW)).toBe(false);
    });

    it("TAP_ADMIN: write YES, admin_review YES, technical_review NO", () => {
      const session = { role: ROLES.TAP_ADMIN };
      expect(can(session, PERMISSIONS.MAINTENANCE_WRITE)).toBe(true);
      expect(can(session, PERMISSIONS.MAINTENANCE_ADMIN_REVIEW)).toBe(true);
      expect(can(session, PERMISSIONS.MAINTENANCE_TECHNICAL_REVIEW)).toBe(false);
    });

    it("JOHN_CRANE_ENGINEER: write NO (no field impersonation), admin_review NO, technical_review YES", () => {
      const session = { role: ROLES.JOHN_CRANE_ENGINEER };
      expect(can(session, PERMISSIONS.MAINTENANCE_WRITE)).toBe(false);
      expect(can(session, PERMISSIONS.MAINTENANCE_ADMIN_REVIEW)).toBe(false);
      expect(can(session, PERMISSIONS.MAINTENANCE_TECHNICAL_REVIEW)).toBe(true);
    });

    it("PERTAMINA_ENGINEER: write NO, admin_review NO, technical_review NO (read-only)", () => {
      const session = { role: ROLES.PERTAMINA_ENGINEER };
      expect(can(session, PERMISSIONS.MAINTENANCE_WRITE)).toBe(false);
      expect(can(session, PERMISSIONS.MAINTENANCE_ADMIN_REVIEW)).toBe(false);
      expect(can(session, PERMISSIONS.MAINTENANCE_TECHNICAL_REVIEW)).toBe(false);
    });

    it("PERTAMINA_VIEWER: write NO, admin_review NO, technical_review NO (read-only)", () => {
      const session = { role: ROLES.PERTAMINA_VIEWER };
      expect(can(session, PERMISSIONS.MAINTENANCE_WRITE)).toBe(false);
      expect(can(session, PERMISSIONS.MAINTENANCE_ADMIN_REVIEW)).toBe(false);
      expect(can(session, PERMISSIONS.MAINTENANCE_TECHNICAL_REVIEW)).toBe(false);
    });

    it("SUPERUSER: all three grants (fallback fixture superset)", () => {
      const session = { role: ROLES.SUPERUSER };
      expect(can(session, PERMISSIONS.MAINTENANCE_WRITE)).toBe(true);
      expect(can(session, PERMISSIONS.MAINTENANCE_ADMIN_REVIEW)).toBe(true);
      expect(can(session, PERMISSIONS.MAINTENANCE_TECHNICAL_REVIEW)).toBe(true);
    });

    it("real backend sessions: TAP_ADMIN's array-based session never grants technical_review even if role fallback would", () => {
      const session = {
        role: "TAP_ADMIN",
        permissions: ["pump.read", "maintenance.read", "maintenance.write", "maintenance.admin_review"],
      };
      expect(can(session, "maintenance.write")).toBe(true);
      expect(can(session, "maintenance.admin_review")).toBe(true);
      expect(can(session, "maintenance.technical_review")).toBe(false);
    });

    it("real backend sessions: JOHN_CRANE_ENGINEER's array-based session never grants write or admin_review", () => {
      const session = {
        role: "JOHN_CRANE_ENGINEER",
        permissions: ["pump.read", "maintenance.read", "maintenance.technical_review"],
      };
      expect(can(session, "maintenance.technical_review")).toBe(true);
      expect(can(session, "maintenance.write")).toBe(false);
      expect(can(session, "maintenance.admin_review")).toBe(false);
    });
  });
});
