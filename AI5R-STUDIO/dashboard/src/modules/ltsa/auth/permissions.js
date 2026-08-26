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
  // MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- manual completion of
  // seal_registry.kimap_pertamina/gpn_john_crane (PATCH /api/ltsa/seals/
  // {seal_code}). Reuses master.edit verbatim, not a new permission --
  // it was reserved in advance on the backend for exactly this ("master
  // DATA edit -- pumps/seals canonical definitions, no current route",
  // auth_service.py's own ROLE_PERMISSIONS header).
  MASTER_EDIT: "master.edit",
  // MWO-LTSA-PM-CM-REVIEW-UI-001 -- the three PM/Condition Monitoring
  // workflow permissions reserved in advance by MWO-LTSA-AUTH-003A-FINAL
  // ("no UI element consumes it until the PM/CM Intake MWO builds the
  // technical-review screen", this file's own prior comment) and already
  // enforced server-side by MWO-LTSA-PM-CM-INTAKE-001's routers. Reused
  // verbatim, no new backend permission invented.
  MAINTENANCE_WRITE: "maintenance.write",
  MAINTENANCE_ADMIN_REVIEW: "maintenance.admin_review",
  MAINTENANCE_TECHNICAL_REVIEW: "maintenance.technical_review",
  // MWO-LTSA-AUDIT-CHANGE-HISTORY-001 / MWO-LTSA-HISTORICAL-REVIEW-UI-001
  // -- reused verbatim, both reserved/added on the backend for exactly
  // this (record.edit gates the generic Edit Value engine AND the
  // historical-review/resolve/reject/promote layer built over it, per
  // the latter MWO's own "reuse record.edit, no second permission"
  // decision; audit.read_full is the pre-existing, SUPERUSER-only Full
  // Change History permission, unchanged).
  RECORD_EDIT: "record.edit",
  AUDIT_HISTORY_READ: "audit.read_full",
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
    PERMISSIONS.MASTER_EDIT,
    // real backend grant: maintenance.write + maintenance.admin_review,
    // NOT maintenance.technical_review (TAP_ADMIN cannot technically
    // review its own team's work -- Hard Rule, unchanged from
    // MWO-LTSA-AUTH-003A-FINAL/MWO-LTSA-PM-CM-INTAKE-001).
    PERMISSIONS.MAINTENANCE_WRITE,
    PERMISSIONS.MAINTENANCE_ADMIN_REVIEW,
    PERMISSIONS.RECORD_EDIT,
  ]),
  [ROLES.TAP_ENGINEER]: Object.freeze([
    PERMISSIONS.DASHBOARD_READ,
    ...ENGINEERING_CORE,
    PERMISSIONS.KNOWLEDGEREVIEW_READ,
    PERMISSIONS.INTERNAL_COMPONENT_READ,
    PERMISSIONS.ENGINEERING_AI_ASK,
    PERMISSIONS.ANALYTICS_READ,
    // real backend grant: maintenance.write only -- no admin_review, no
    // technical_review.
    PERMISSIONS.MAINTENANCE_WRITE,
    // no import.execute, no admin.access, no master.edit (the real
    // backend ROLE_PERMISSIONS matrix does not grant master.edit to
    // TAP_ENGINEER today -- MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001
    // Phase 6 explicitly allows staying read-only here rather than
    // widening an existing permission to fit this UI)
  ]),
  [ROLES.PERTAMINA_ENGINEER]: Object.freeze([
    ...ENGINEERING_CORE,
    PERMISSIONS.ENGINEERING_AI_ASK,
    // no dashboard.read (TAP fleet executive view), no analytics.read
    // (cross-customer), no knowledgereview.read (internal curation), no
    // import.execute, no internal_component.read, no admin.access, no
    // maintenance.write/admin_review/technical_review (Pertamina is
    // read-only for PM/Condition Monitoring, unchanged).
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
    PERMISSIONS.MASTER_EDIT,
    PERMISSIONS.MAINTENANCE_WRITE,
    PERMISSIONS.MAINTENANCE_ADMIN_REVIEW,
    PERMISSIONS.MAINTENANCE_TECHNICAL_REVIEW,
    PERMISSIONS.RECORD_EDIT,
    PERMISSIONS.AUDIT_HISTORY_READ,
  ]),
  // JOHN_CRANE_ENGINEER: technical authority, not administrative -- reads
  // (including internal_component.read for GPN/internal-component data)
  // but no dashboard.read (internal_inventory.read), no import.execute,
  // no admin.access. Matches ROLE_PERMISSIONS["JOHN_CRANE_ENGINEER"] on
  // the backend exactly -- maintenance.technical_review only (no write,
  // no admin_review: JC reviews, it does not create/edit field records
  // or perform TAP's own administrative review).
  [ROLES.JOHN_CRANE_ENGINEER]: Object.freeze([
    ...ENGINEERING_CORE,
    PERMISSIONS.INTERNAL_COMPONENT_READ,
    PERMISSIONS.ENGINEERING_AI_ASK,
    PERMISSIONS.MAINTENANCE_TECHNICAL_REVIEW,
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
  inventory: PERMISSIONS.INVENTORY_READ,
  knowledgereview: PERMISSIONS.KNOWLEDGEREVIEW_READ,
  import: PERMISSIONS.IMPORT_EXECUTE,
  history: PERMISSIONS.HISTORY_READ,
  reports: PERMISSIONS.REPORTS_READ,
  analytics: PERMISSIONS.ANALYTICS_READ,
  // MWO-LTSA-HISTORICAL-REVIEW-UI-001 -- gated on record.edit (SUPERUSER
  // + TAP_ADMIN only), the same backend permission the review/resolve/
  // reject/promote API itself requires -- this is presentation-only tab
  // visibility (this file's own header rule); the backend 403 is what
  // actually stops the other four roles.
  "historical-review": PERMISSIONS.RECORD_EDIT,
  // MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-ROUTING-019A -- MWO-019's own
  // "historical-batch-review" TABS/PAGES entry (LTSAWorkspace.jsx) was
  // never given a TAB_PERMISSIONS entry, so visibleTabKeys() silently
  // dropped it for every role and the page was unreachable through the
  // nav menu despite being correctly registered. Gated on the same
  // maintenance.read the "pm"/"cmon" tabs themselves already use -- this
  // page reviews PM/CMON records, same read-visibility tier as those
  // domains; the individual batch-submit/technical-review actions inside
  // it remain separately gated on maintenance.write/maintenance.
  // technical_review (unchanged, HistoricalBatchReview.jsx's own RBAC).
  "historical-batch-review": PERMISSIONS.PM_READ,
});

export function visibleTabKeys(session) {
  return Object.keys(TAB_PERMISSIONS).filter((key) => can(session, TAB_PERMISSIONS[key]));
}
