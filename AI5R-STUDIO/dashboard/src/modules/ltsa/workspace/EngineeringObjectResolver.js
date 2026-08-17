/**
 * MWO-LTSA-071 -- Engineering Object Resolver.
 *
 * ONE canonical function deciding "given this engineering object, which
 * workspace tab and navContext do I open" -- replacing the same decision
 * that was previously re-implemented ad hoc in multiple places. The
 * clearest, most complete prior instance was Pump.jsx's own
 * `handleOpenEngineeringObject(eventType, payload)` (Pump Workspace
 * Timeline/Related-Engineering click-through), whose own header comment
 * already documented every rule below with direct citations to each
 * target page's real navContext-consumption code -- that comment is the
 * primary evidence base for this module, cross-checked against every
 * other real onNavigate() call site in modules/ltsa (CM.jsx, PM.jsx,
 * WorkOrder.jsx, DocumentWorkspace.jsx, InstallationWorkspace.jsx,
 * Seal.jsx, DrawingWorkspace.jsx).
 *
 * This does NOT replace WorkspaceRegistry.js -- that module is a
 * separate, narrower concern (building/parsing browser URL paths for a
 * handful of pump-scoped deep-linkable sub-views: PM Workspace,
 * Condition Monitoring Workspace, Failure Analysis, Knowledge). This
 * resolver targets the general in-memory `onNavigate(key, navContext)`
 * tab-switch mechanism LTSAWorkspace.jsx's own TABS/PAGES already
 * implement, which is what every one of the 8 supported entity types
 * above actually navigates through today. No new routing mechanism, no
 * new endpoint, no schema change -- this module makes zero network calls
 * and touches no backend.
 *
 * Per-type resolution rules (workspace key + navContext shape), each
 * confirmed against the TARGET page's own real navContext-consumption
 * code, not assumed from the caller side alone:
 *
 *   PUMP        -> "pump",        { selectId } -- Pump.jsx's own
 *                  navContext?.selectId branch is the only pre-selection
 *                  path; a pump's tag itself doubles as its id, so
 *                  `assetTag` is accepted as a fallback identity when no
 *                  distinct entityId is given.
 *   INSTALLATION -> "installation", { selectId } -- InstallationWorkspace.jsx
 *                  matches `installation.id === navContext.selectId`
 *                  directly; no assetTag-based lookup exists there.
 *   PM          -> "pm",          { selectId } | { assetTag } -- PM.jsx's
 *                  own useEffect reads selectId first, else assetTag
 *                  (both real, both already exercised: DocumentWorkspace/
 *                  Drawing send assetTag, Pump.jsx's own PM Timeline
 *                  events send selectId when a pm_schedule_code exists).
 *   CM          -> "cm",          { selectId } | { assetTag } -- CM.jsx's
 *                  own useEffect reads selectId first, else assetTag
 *                  (same dual pattern as PM, confirmed in CM.jsx itself).
 *   WORK_ORDER  -> "workorder",   { selectId } ONLY -- WorkOrder.jsx's own
 *                  useEffect reads ONLY navContext?.selectId; other call
 *                  sites (DocumentWorkspace/CM/WorkOrder's own Documents
 *                  section) pass { assetTag } to "workorder" today, but
 *                  WorkOrder.jsx never reads it, so it has no effect --
 *                  this resolver deliberately does not perpetuate that
 *                  dead field, it follows what the target page actually
 *                  consumes.
 *   DRAWING     -> "drawing",     { assetTag } ONLY -- DrawingWorkspace.jsx
 *                  fetches by navContext.assetTag only (MWO-LTSA-062:
 *                  "no document_number-keyed lookup path exists"); there
 *                  is no per-drawing selectId concept to resolve to.
 *   DOCUMENT    -> "document",    { selectId } | { assetTag } --
 *                  DocumentWorkspace.jsx's own selection effect reads
 *                  selectId first, else looks up the first document
 *                  matching assetTag.
 *   SEAL        -> "seal",        { selectId } -- disclosed, pre-existing
 *                  gap: Seal.jsx does not currently read navContext at
 *                  all (confirmed by inspection), so this resolves to a
 *                  real, already-registered workspace key with the same
 *                  { selectId } shape every other record-scoped type
 *                  uses, ready for Seal.jsx to consume once it does --
 *                  this resolver does not add that consumption itself
 *                  ("No frontend redesign").
 *
 * Missing identity (no entityId AND no assetTag) is NOT an error -- it
 * resolves to an empty navContext (`{}`), the same "open this workspace
 * with no specific selection" pattern already real and in use elsewhere
 * (Pump.jsx: `onNavigate?.("drawing", {})`). An unrecognized entityType
 * IS an error (throws) -- silently guessing a workspace, or silently
 * doing nothing, would hide an integration bug; failing loudly here is
 * the same "never fabricate, never silently misroute" discipline this
 * whole product's ingestion/mapping code already follows.
 */

export const ENGINEERING_OBJECT_TYPES = Object.freeze({
  PUMP: "PUMP",
  INSTALLATION: "INSTALLATION",
  PM: "PM",
  CM: "CM",
  WORK_ORDER: "WORK_ORDER",
  DRAWING: "DRAWING",
  DOCUMENT: "DOCUMENT",
  SEAL: "SEAL",
});

function selectIdOrAssetTag({ entityId, assetTag }) {
  if (entityId) return { selectId: entityId };
  if (assetTag) return { assetTag };
  return {};
}

const RESOLVERS = {
  [ENGINEERING_OBJECT_TYPES.PUMP]: ({ entityId, assetTag }) => {
    const selectId = entityId ?? assetTag;
    return { workspace: "pump", navigationContext: selectId ? { selectId } : {} };
  },
  [ENGINEERING_OBJECT_TYPES.INSTALLATION]: ({ entityId }) => ({
    workspace: "installation",
    navigationContext: entityId ? { selectId: entityId } : {},
  }),
  [ENGINEERING_OBJECT_TYPES.PM]: (context) => ({
    workspace: "pm",
    navigationContext: selectIdOrAssetTag(context),
  }),
  [ENGINEERING_OBJECT_TYPES.CM]: (context) => ({
    workspace: "cm",
    navigationContext: selectIdOrAssetTag(context),
  }),
  [ENGINEERING_OBJECT_TYPES.WORK_ORDER]: ({ entityId }) => ({
    workspace: "workorder",
    navigationContext: entityId ? { selectId: entityId } : {},
  }),
  [ENGINEERING_OBJECT_TYPES.DRAWING]: ({ assetTag }) => ({
    workspace: "drawing",
    navigationContext: assetTag ? { assetTag } : {},
  }),
  [ENGINEERING_OBJECT_TYPES.DOCUMENT]: (context) => ({
    workspace: "document",
    navigationContext: selectIdOrAssetTag(context),
  }),
  [ENGINEERING_OBJECT_TYPES.SEAL]: ({ entityId }) => ({
    workspace: "seal",
    navigationContext: entityId ? { selectId: entityId } : {},
  }),
};

/**
 * @param {{ entityType: string, entityId?: string, assetTag?: string }} input
 * @returns {{ workspace: string, navigationContext: object }}
 */
export function resolveEngineeringObject({ entityType, entityId, assetTag } = {}) {
  const resolver = RESOLVERS[entityType];
  if (!resolver) {
    throw new Error(`EngineeringObjectResolver: unsupported entityType "${entityType}"`);
  }
  return resolver({ entityId, assetTag });
}
