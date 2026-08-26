export const WORKSPACE_KEYS={PUMP:"history",PM:"pm-workspace",CONDITION_MONITORING:"cmon-workspace",FAILURE_ANALYSIS:"failure-analysis-workspace",WORK_ORDER:"work-order-workspace",KNOWLEDGE:"knowledge-workspace",PUMP_LEGACY:"history-legacy"};
// MWO-LTSA-DASHBOARD-RECOVERY-001 -- workspaceLocation's catch-all used to
// unconditionally return "/ltsa/pump-workspace" for EVERY key that isn't
// one of the 6 asset-context keys above (dashboard/seal/workorder/
// reports/etc. all fell through to it), so the URL bar showed the Pump
// Workspace route no matter which tab was actually active. The catch-all
// now maps any other key to its own generic /ltsa/{key} route, so the URL
// always agrees with the rendered tab; the 6 asset-context routes above
// are unchanged.
export function workspaceLocation(key,context={}){const tag=encodeURIComponent(context.assetTag??"");if(key===WORKSPACE_KEYS.PUMP)return tag?`/ltsa/pump/${tag}`:"/ltsa/pump-workspace";if(key===WORKSPACE_KEYS.PM)return `/ltsa/pump/${tag}/pm/${encodeURIComponent(context.workOrderId??"")}`;if(key===WORKSPACE_KEYS.CONDITION_MONITORING)return `/ltsa/pump/${tag}/monitoring`;if(key===WORKSPACE_KEYS.FAILURE_ANALYSIS)return `/ltsa/pump/${tag}/failure/${encodeURIComponent(context.selectId??"")}`;if(key===WORKSPACE_KEYS.KNOWLEDGE)return `/ltsa/pump/${tag}/knowledge`;if(key===WORKSPACE_KEYS.PUMP_LEGACY)return "/ltsa/pump-workspace-legacy";return `/ltsa/${encodeURIComponent(key)}`}
// Generic /ltsa/{key} recognition (e.g. /ltsa/dashboard) is additive and
// deliberately whitelist-gated -- LTSAWorkspace.jsx's own TABS keys only.
// /ltsa/{organization} is an EXISTING, unrelated routing convention
// (ApplicationRouter/OrganizationResolver resolve the org slug from this
// same raw pathname before LTSAWorkspace ever mounts; the segment is
// still present in window.location.pathname when it does); an unbounded
// "any 2-segment /ltsa/* path is a workspace key" fallback would
// misinterpret an org slug like "/ltsa/tap" as key "tap" (PAGES["tap"] is
// undefined -- ActivePage renders as undefined -- hard crash), so only
// these known generic tab keys are recognized here. Asset-context keys
// (pump/pm/monitoring/failure/knowledge, "history") are handled by their
// own patterns above and are not part of this whitelist.
const GENERIC_TAB_KEYS=new Set(["dashboard","pump","seal","drawing","document","installation","workorder","pm","cm","cmon","knowledgereview","import","reports","analytics","historical-review","historical-batch-review"]);
export function parseWorkspaceLocation(pathname){const parts=pathname.split("/").filter(Boolean);if(parts[0]!=="ltsa")return null;if(parts[1]==="pump-workspace")return {key:WORKSPACE_KEYS.PUMP,context:{}};if(parts[1]==="pump-workspace-legacy")return {key:WORKSPACE_KEYS.PUMP_LEGACY,context:{}};if(parts[1]==="pump"&&parts[2]){const assetTag=decodeURIComponent(parts[2]);if(parts[3]==="pm"&&parts[4])return {key:WORKSPACE_KEYS.PM,context:{assetTag,workOrderId:decodeURIComponent(parts[4])}};if(parts[3]==="monitoring")return {key:WORKSPACE_KEYS.CONDITION_MONITORING,context:{assetTag}};if(parts[3]==="failure"&&parts[4])return {key:WORKSPACE_KEYS.FAILURE_ANALYSIS,context:{assetTag,selectId:decodeURIComponent(parts[4])}};if(parts[3]==="knowledge")return {key:WORKSPACE_KEYS.KNOWLEDGE,context:{assetTag}};return {key:WORKSPACE_KEYS.PUMP,context:{assetTag}}}if(parts.length===2&&GENERIC_TAB_KEYS.has(parts[1]))return {key:decodeURIComponent(parts[1]),context:{}};return null}