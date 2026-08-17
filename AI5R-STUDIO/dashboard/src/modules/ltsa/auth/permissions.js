// Centralized frontend capability model for the LTSA authenticated shell
// (MWO-LTSA-AUTH-OPEN-DESIGN-001). Every navigation/action visibility
// check in the LTSA module SHALL go through `can()` against this catalog
// -- never an inline `role === "..."` or `organization === "..."` check.
//
// This is presentation-only. The backend (AUTH-001A and later) remains the
// authoritative enforcement point; hiding something here is UX, not a
// security boundary.

// MWO-LTSA-AUTH-003A-FINAL -- widened from 4 to the final 6 canonical
// roles (CORE-SERVICES/API/auth_service.py's own ROLE_PERMISSIONS).
export const ROLES = Object.freeze({
  SUPERUSER: "SUPERUSER",
  TAP_ADMIN: "TAP_ADMIN",
  TAP_ENGINEER: "TAP_ENGINEER",
  JOHN_CRANE_ENGINEER: "JOHN_CRANE_ENGINEER",
  PERTAMINA_ENGINEER: "PERTAMINA_ENGINEER",
  PERTAMINA_VIEWER: "PERTAMINA_VIEWER",
});

// MWO-LTSA-AUTH-002 -- these string VALUES are now the real AUTH-001
// backend permission names (CORE-SERVICES/API/auth_service.py's own
// ROLE_PERMISSIONS), not a separately-invented frontend catalog, per this
// MWO's Rule 7 ("backend is authoritative... smallest safe reconciliation,
// do not create a role-management system"). The backend has no per-tab
// granularity (document/installation both gate on drawing.read; workorder/
// pm both gate on maintenance.read; etc.) -- multiple KEYS below sharing
// one backend permission VALUE is intentional, not a mistake. The JS
// identifiers (PERMISSIONS.X) are unchanged, so no consuming code/test
// needed to change, only what they resolve to.
export const PERMISSIONS = Object.freeze({
  // DASHBOARD_READ deliberately does NOT reuse pump.read: every role has
  // pump.read (backend dashboard.py's own choice for ITS gate), but the
  // frozen Open Design shows "Executive Dashboard" to TAP only, never
  // Pertamina -- confirmed by MWO-LTSA-AUTH-OPEN-DESIGN-002B's own frozen
  // screenshots. internal_inventory.read is the closest real backend
  // permission that is TAP-only (TAP_ADMIN/TAP_ENGINEER) and absent from
  // both Pertamina roles, preserving that frozen visibility split.
  DASHBOARD_READ: "internal_inventory.read",
  EQUIPMENT_READ: "pump.read",
  PUMP_READ: "pump.read",
  SEAL_READ: "seal.read",
  DRAWING_READ: "drawing.read",
  DOCUMENT_READ: "drawing.read",
  INSTALLATION_READ: "drawing.read",
  WORKORDER_READ: "maintenance.read",
  PM_READ: "maintenance.read",
  CM_READ: "condition.read",
  CMON_READ: "condition.read",
  KNOWLEDGEREVIEW_READ: "internal_component.read",
  IMPORT_EXECUTE: "import.execute",
  INVENTORY_READ: "inventory.read",
  INTERNAL_COMPONENT_READ: "internal_component.read",
  ENGINEERING_AI_ASK: "engineering_ai.ask",
  REPORTS_READ: "maintenance.read",
  ANALYTICS_READ: "internal_component.read",
  HISTORY_READ: "maintenance.read",
  ADMIN_ACCESS: "admin.users",
});

const ENGINEERING_CORE = [
  PERMISSIONS.EQUIPMENT_READ,
  PERMISSIONS.PUMP_READ,
  PERMISSIONS.SEAL_READ,
  PERMISSIONS.DRAWING_READ,
  PERMISSIONS.DOCUMENT_READ,
  PERMISSIONS.INSTALLATION_READ,
  PERMISSIONS.WORKORDER_READ,
  PERMISSIONS.PM_READ,
  PERMISSIONS.CM_READ,
  PERMISSIONS.CMON_READ,
  PERMISSIONS.INVENTORY_READ,
  PERMISSIONS.REPORTS_READ,
  PERMISSIONS.HISTORY_READ,
];

// V1 role -> permission grants. Permission names are taken verbatim from
// the AUTH-001 contract where it already names them (inventory.read,
// engineering_ai.ask, import.execute, internal_component.read); the
// per-tab *.read permissions are this MWO's frontend-only extension of
// that catalog, not a backend invention -- they gate presentation of
// existing LTSA tabs, nothing else.
export const ROLE_PERMISSIONS = Object.freeze({
  [ROLES.TAP_ADMIN]: Object.freeze([
    PERMISSIONS.DASHBOARD_READ,
    ...ENGINEERING_CORE,
    PERMISSIONS.KNOWLEDGEREVIEW_READ,
    PERMISSIONS.IMPORT_EXECUTE,
    PERMISSIONS.INTERNAL_COMPONENT_READ,
    PERMISSIONS.ENGINEERING_AI_ASK,
    PERMISSIONS.ANALYTICS_READ,
    PERMISSIONS.ADMIN_ACCESS,
  ]),
  [ROLES.TAP_ENGINEER]: Object.freeze([
    PERMISSIONS.DASHBOARD_READ,
    ...ENGINEERING_CORE,
    PERMISSIONS.KNOWLEDGEREVIEW_READ,
    PERMISSIONS.INTERNAL_COMPONENT_READ,
    PERMISSIONS.ENGINEERING_AI_ASK,
    PERMISSIONS.ANALYTICS_READ,
    // no import.execute, no admin.access
  ]),
  [ROLES.PERTAMINA_ENGINEER]: Object.freeze([
    ...ENGINEERING_CORE,
    PERMISSIONS.ENGINEERING_AI_ASK,
    // no dashboard.read (TAP fleet executive view), no analytics.read
    // (cross-customer), no knowledgereview.read (internal curation), no
    // import.execute, no internal_component.read, no admin.access
  ]),
  [ROLES.PERTAMINA_VIEWER]: Object.freeze([
    ...ENGINEERING_CORE,
    // read-only: everything PERTAMINA_ENGINEER has except
    // engineering_ai.ask
  ]),
  // MWO-LTSA-AUTH-003A-FINAL -- SUPERUSER is the superset of TAP_ADMIN's
  // fallback grant (the backend's own admin.superuser/audit.read_full are
  // deliberately not mirrored here: no frontend UI element checks either
  // yet, and this fallback array is never consulted for a real session
  // per this file's own header -- session.permissions from a real
  // /api/auth/me response is always authoritative).
  [ROLES.SUPERUSER]: Object.freeze([
    PERMISSIONS.DASHBOARD_READ,
    ...ENGINEERING_CORE,
    PERMISSIONS.KNOWLEDGEREVIEW_READ,
    PERMISSIONS.IMPORT_EXECUTE,
    PERMISSIONS.INTERNAL_COMPONENT_READ,
    PERMISSIONS.ENGINEERING_AI_ASK,
    PERMISSIONS.ANALYTICS_READ,
    PERMISSIONS.ADMIN_ACCESS,
  ]),
  // JOHN_CRANE_ENGINEER: technical authority, not administrative -- reads
  // (including internal_component.read for GPN/internal-component data)
  // but no dashboard.read (internal_inventory.read), no import.execute,
  // no admin.access. Matches ROLE_PERMISSIONS["JOHN_CRANE_ENGINEER"] on
  // the backend exactly (maintenance.technical_review has no frontend
  // PERMISSIONS constant yet -- no UI element consumes it until the
  // PM/CM Intake MWO builds the technical-review screen).
  [ROLES.JOHN_CRANE_ENGINEER]: Object.freeze([
    ...ENGINEERING_CORE,
    PERMISSIONS.INTERNAL_COMPONENT_READ,
    PERMISSIONS.ENGINEERING_AI_ASK,
  ]),
});

// MWO-LTSA-AUTH-002 -- when session.permissions is present (every real
// session from authClient.js's real /api/auth/me now carries it), that
// REAL backend-granted array is authoritative, checked directly -- no
// frontend role->permission duplication in the runtime path at all.
// ROLE_PERMISSIONS below is kept only as the fallback for callers/tests
// that pass a bare {role} fixture with no permissions array (Rule 2:
// "tests may use fixtures/mocks"); it must stay a subset AUTH-001's own
// matrix would grant, but is never consulted for a real session.
export function can(session, permission) {
  if (!session) return false;
  if (Array.isArray(session.permissions)) {
    return session.permissions.includes(permission);
  }
  if (!session.role) return false;
  const grants = ROLE_PERMISSIONS[session.role];
  return Array.isArray(grants) && grants.includes(permission);
}

// LTSAWorkspace tab key -> the permission that gates it. Tabs with no
// entry here are always visible to any authenticated session (none
// currently -- every tab is gated deliberately).
export const TAB_PERMISSIONS = Object.freeze({
  dashboard: PERMISSIONS.DASHBOARD_READ,
  equipment: PERMISSIONS.EQUIPMENT_READ,
  pump: PERMISSIONS.PUMP_READ,
  seal: PERMISSIONS.SEAL_READ,
  drawing: PERMISSIONS.DRAWING_READ,
  document: PERMISSIONS.DOCUMENT_READ,
  installation: PERMISSIONS.INSTALLATION_READ,
  workorder: PERMISSIONS.WORKORDER_READ,
  pm: PERMISSIONS.PM_READ,
  cm: PERMISSIONS.CM_READ,
  cmon: PERMISSIONS.CMON_READ,
  knowledgereview: PERMISSIONS.KNOWLEDGEREVIEW_READ,
  import: PERMISSIONS.IMPORT_EXECUTE,
  history: PERMISSIONS.HISTORY_READ,
  reports: PERMISSIONS.REPORTS_READ,
  analytics: PERMISSIONS.ANALYTICS_READ,
});

export function visibleTabKeys(session) {
  return Object.keys(TAB_PERMISSIONS).filter((key) => can(session, TAB_PERMISSIONS[key]));
}
