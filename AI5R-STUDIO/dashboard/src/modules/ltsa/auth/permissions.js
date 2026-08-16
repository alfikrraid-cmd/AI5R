// Centralized frontend capability model for the LTSA authenticated shell
// (MWO-LTSA-AUTH-OPEN-DESIGN-001). Every navigation/action visibility
// check in the LTSA module SHALL go through `can()` against this catalog
// -- never an inline `role === "..."` or `organization === "..."` check.
//
// This is presentation-only. The backend (AUTH-001A and later) remains the
// authoritative enforcement point; hiding something here is UX, not a
// security boundary.

export const ROLES = Object.freeze({
  TAP_ADMIN: "TAP_ADMIN",
  TAP_ENGINEER: "TAP_ENGINEER",
  PERTAMINA_ENGINEER: "PERTAMINA_ENGINEER",
  PERTAMINA_VIEWER: "PERTAMINA_VIEWER",
});

export const PERMISSIONS = Object.freeze({
  DASHBOARD_READ: "dashboard.read",
  EQUIPMENT_READ: "equipment.read",
  PUMP_READ: "pump.read",
  SEAL_READ: "seal.read",
  DRAWING_READ: "drawing.read",
  DOCUMENT_READ: "document.read",
  INSTALLATION_READ: "installation.read",
  WORKORDER_READ: "workorder.read",
  PM_READ: "pm.read",
  CM_READ: "cm.read",
  CMON_READ: "cmon.read",
  KNOWLEDGEREVIEW_READ: "knowledgereview.read",
  IMPORT_EXECUTE: "import.execute",
  INVENTORY_READ: "inventory.read",
  INTERNAL_COMPONENT_READ: "internal_component.read",
  ENGINEERING_AI_ASK: "engineering_ai.ask",
  REPORTS_READ: "reports.read",
  ANALYTICS_READ: "analytics.read",
  HISTORY_READ: "history.read",
  ADMIN_ACCESS: "admin.access",
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
});

export function can(session, permission) {
  if (!session || !session.role) return false;
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
