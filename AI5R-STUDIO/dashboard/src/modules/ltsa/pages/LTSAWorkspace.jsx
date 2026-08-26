import { useEffect, useState } from "react";
import { EmptyState, PageHeader, Panel, Tabs } from "../../../design-system";
import AssetSelector from "../components/AssetSelector";
import { getPumps } from "../../../api/ai5rClient";
import { mapPumpRecord } from "../utils/pumpMapping";
import ExecutiveDashboard from "./ExecutiveDashboard";
import Pump from "./Pump";
import WorkOrder from "./WorkOrder";
import PM from "./PM";
import CM from "./CM";
import ConditionMonitoring from "./ConditionMonitoring";
import ConditionMonitoringWorkspace from "./ConditionMonitoringWorkspace";
import MaintenanceHistory from "./MaintenanceHistory";
import PMWorkOrderWorkspace from "./PMWorkOrderWorkspace";
import ReportsWorkspace from "./ReportsWorkspace";
import AnalyticsWorkspace from "./AnalyticsWorkspace";
import FailureAnalysisWorkspace from "./FailureAnalysisWorkspace";
import Seal from "./Seal";
import DrawingWorkspace from "./DrawingWorkspace";
import DocumentWorkspace from "./DocumentWorkspace";
import InstallationWorkspace from "./InstallationWorkspace";
import KnowledgeReviewWorkspace from "./KnowledgeReviewWorkspace";
import KnowledgeWorkspace from "./KnowledgeWorkspace";
import MechanicalSealStock from "./MechanicalSealStock";
import ImportWorkspace from "./ImportWorkspace";
import HistoricalReview from "./HistoricalReview";
import HistoricalBatchReview from "./HistoricalBatchReview";
import { WorkspaceProvider } from "../workspace/WorkspaceContext";
import { parseWorkspaceLocation, workspaceLocation } from "../workspace/WorkspaceRegistry";
import "./LTSAWorkspace.css";

// "history"'s label is "Asset 360" (renamed under APP-ASSET360-001) --
// the tab's own page already called itself that in its subtitle, and
// QuickNavigationPanel's button already said "Open Asset 360"; only this
// label had not caught up (DISCOVERY-ASSET360-UI-001's key finding). The
// key itself stays "history", unchanged, so every existing onNavigate
// ("history") call site keeps working.
//
// MWO-LTSA-036D -- "history" (Asset 360) is repointed from MaintenanceHistory
// to KnowledgeWorkspaceRoute (Phase 0/1 of the Asset360 Migration Roadmap,
// per MWO-LTSA-036A/B/C's canonical-model finding: KnowledgeWorkspace is
// the Open-Design-canonical "everything about this equipment" surface,
// MaintenanceHistory is the pre-existing, architecturally-superseded one).
// Every existing onNavigate("history", { assetTag }) call site (Pump.jsx's
// "View History") keeps working unchanged and now opens KnowledgeWorkspace
// with the right tag. Call sites with no assetTag (QuickNavigationPanel's
// "Open Asset 360", the bare tab click, App.jsx's initialActiveKey="history"
// default) land on KnowledgeWorkspace's own no-tag empty state instead of
// MaintenanceHistory's AssetSelector picker -- KnowledgeWorkspace has no
// picker of its own (host-agnostic { tag } contract, Open Design Â§8 D7),
// and this MWO's mission forbids creating one ("Do NOT create new
// components"). MaintenanceHistory remains fully intact and reachable at
// the "history-legacy" fallback route for exactly this gap, per the
// mission's explicit "keep MaintenanceHistory... temporary fallback route."
//
// "cmon" (APP-CMON-001, per ADR-CONDITION-MONITORING-001) -- key
// deliberately not "cm", to avoid colliding with the existing Corrective
// Maintenance tab, the same naming discipline this whole engineering line
// has carried since DISCOVERY-LTSA-REPORT-001 first flagged the "CM"
// acronym collision.
const TABS = [
  { key: "dashboard", label: "Executive Dashboard" },
  { key: "pump", label: "Pump" },
  { key: "seal", label: "Mechanical Seal" },
  { key: "inventory", label: "Mechanical Seal Stock" },
  { key: "drawing", label: "Drawing" },
  { key: "document", label: "Document" },
  { key: "installation", label: "Installation" },
  { key: "workorder", label: "Work Order" },
  { key: "pm", label: "Preventive Maintenance" },
  { key: "cm", label: "Corrective Maintenance" },
  { key: "cmon", label: "Condition Monitoring" },
  { key: "knowledgereview", label: "Knowledge Review" },
  { key: "import", label: "Import" },
  { key: "history", label: "Asset 360" },
  { key: "reports", label: "Reports" },
  { key: "analytics", label: "Analytics" },
  { key: "historical-review", label: "Historical Data Review" },
  { key: "historical-batch-review", label: "Historical Batch Review" },
];

// "pm-workspace" (PM Work Order Workspace) is deep-link-only, not a TABS
// entry -- like the PM Workspace design itself, it's scoped to one Work
// Order (navContext.workOrderId) and is entered from Work Order
// Workspace's "Open PM Workspace" action, not browsed to directly.

// "knowledge-workspace" (MWO-LTSA-032E) is deep-link-only, like
// cmon-workspace and failure-analysis-workspace above it -- reachable via
// URL/onNavigate(WORKSPACE_KEYS.KNOWLEDGE, {assetTag}), not a TABS entry.
// KnowledgeWorkspace's own prop contract is deliberately host-agnostic
// ({ tag }, not navContext -- Open Design ODR-LTSA-031E-R1 Â§8 D7, "so
// Dashboard and future products can import one stable entry point"), so
// this adapter is the only routing-specific glue; KnowledgeWorkspace.jsx
// itself is untouched.
//
// MWO-LTSA-036G -- Asset Launcher: KnowledgeWorkspace must never receive a
// null tag, and stays host-agnostic (no internal picker of its own, tag
// stays a required prop). When navContext carries no assetTag yet (every
// untagged launcher -- QuickNavigationPanel's "Open Asset 360", the bare
// "Asset 360" tab click, App.jsx's initialActiveKey default -- all
// converge on this one PAGES.history entry), this adapter resolves the
// asset FIRST by falling back to MaintenanceHistory's existing,
// unmodified AssetSelector-based pump-selection flow, rather than
// inventing a new picker. Once a caller already knows the tag (Pump.jsx's
// "View History", or a /ltsa/pump/{tag} deep link), it goes straight to
// KnowledgeWorkspace, unchanged from MWO-LTSA-032E/036D.
// MWO-LTSA-DEMO-READINESS-CLOSURE-001 -- AssetLauncher: the untagged
// entry point used to hand off to the FULL legacy MaintenanceHistory page
// (its own AssetSelector, its own PumpWorkspaceTimeline, its own
// "Coming Soon"/"Not available" placeholders) once a pump was picked --
// not just to resolve the asset, per MWO-LTSA-036G's own comment. That is
// a second, non-canonical Equipment History rendering (forbidden -- see
// this MWO's Hard Rule 8) and was confirmed as the root cause of a
// demo-facing symptom: navigating here untagged could land on a
// differently-selected pump inside a visually similar but architecturally
// separate screen (legacy breadcrumb "Pumps > {tag}", legacy timeline's
// "No history matches this filter" text -- both distinct from
// KnowledgeWorkspace's own "Asset 360 > {tag}"/"Belum ada riwayat"),
// which read as an identity-integrity bug rather than a wrong-destination
// one. AssetLauncher only resolves a tag (reusing AssetSelector.jsx and
// getPumps/mapPumpRecord, all pre-existing) and then re-enters this same
// "history" key WITH that tag via the existing onNavigate mechanism, so
// KnowledgeWorkspaceRoute's own tag-present branch takes over -- every
// untagged path now converges on the one canonical KnowledgeWorkspace,
// same as every tagged path already did. No new history/timeline engine.
// MaintenanceHistory.jsx itself is untouched and remains reachable,
// unchanged, at its own explicit "history-legacy" fallback route.
function AssetLauncher({ onNavigate }) {
  const [pumps, setPumps] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    getPumps()
      .then((records) => records.map(mapPumpRecord))
      .then((mapped) => {
        if (active) {
          setPumps(mapped);
        }
      })
      .catch(() => {
        if (active) {
          setPumps([]);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="pump-workspace-picker">
      <PageHeader title="Pump Workspace" subtitle="LTSA Engineering — Asset 360" />
      {loading ? (
        <Panel>
          <p>Loading assets...</p>
        </Panel>
      ) : (
        <AssetSelector
          assets={pumps.map((pump) => ({ tag: pump.tag, name: pump.name }))}
          selectedTag={null}
          onSelect={(tag) => {
            if (tag) {
              onNavigate("history", { assetTag: tag });
            }
          }}
        />
      )}
      <EmptyState
        title="No pump selected"
        description="Select a pump above to open its workspace."
      />
    </div>
  );
}

function KnowledgeWorkspaceRoute({ navContext, onNavigate }) {
  if (!navContext?.assetTag) {
    return <AssetLauncher onNavigate={onNavigate} />;
  }
  return <KnowledgeWorkspace tag={navContext.assetTag} />;
}


const PAGES = {
  dashboard: ExecutiveDashboard,
  pump: Pump,
  seal: Seal,
  inventory: MechanicalSealStock,
  drawing: DrawingWorkspace,
  document: DocumentWorkspace,
  installation: InstallationWorkspace,
  knowledgereview: KnowledgeReviewWorkspace,
  import: ImportWorkspace,
  workorder: WorkOrder,
  pm: PM,
  cm: CM,
  cmon: ConditionMonitoring,
  "cmon-workspace": ConditionMonitoringWorkspace,
  "failure-analysis-workspace": FailureAnalysisWorkspace,
  "knowledge-workspace": KnowledgeWorkspaceRoute,
  history: KnowledgeWorkspaceRoute,
  "history-legacy": MaintenanceHistory,
  "pm-workspace": PMWorkOrderWorkspace,
  reports: ReportsWorkspace,
  analytics: AnalyticsWorkspace,
  "historical-review": HistoricalReview,
  "historical-batch-review": HistoricalBatchReview,
};

// `capabilities` is optional (MWO-LTSA-AUTH-OPEN-DESIGN-001) -- when
// omitted, every tab renders exactly as before this MWO (every existing
// caller/test keeps working unchanged). When provided by LTSAAuthGate,
// `capabilities.allowedKeys` filters which TABS entries are shown; tab
// content itself is untouched, this only gates navigation visibility.
export default function LTSAWorkspace({ initialActiveKey = "dashboard", capabilities = null }) {
  const initialLocation = parseWorkspaceLocation(window.location.pathname);
  const [activeKey, setActiveKey] = useState(initialLocation?.key ?? initialActiveKey);
  const [navContext, setNavContext] = useState(initialLocation?.context ?? null);
  const ActivePage = PAGES[activeKey];

  // MWO-LTSA-DASHBOARD-RECOVERY-001 -- when the URL on mount didn't
  // already resolve to a valid workspace location (initialLocation is
  // null: e.g. a fresh login landing on "/" or "/ltsa"), activeKey falls
  // back to initialActiveKey above, but nothing used to update the URL to
  // match -- the browser kept showing whatever stale/unrecognized path it
  // was already on while the canonical Executive Dashboard rendered.
  // replaceState (not pushState) so this sync never adds an extra history
  // entry; runs once, only when the URL didn't already agree.
  useEffect(() => {
    if (!initialLocation) {
      window.history.replaceState({}, "", workspaceLocation(activeKey, {}));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const visibleTabs = capabilities
    ? TABS.filter((tab) => capabilities.allowedKeys.includes(tab.key))
    : TABS;

  // Extended under APP-ASSET360-001 (per ADR-ASSET360-001) with an
  // optional payload -- { assetTag, selectId } -- carrying cross-domain
  // navigation context (e.g. "jump to Asset 360 already scoped to this
  // pump", or "jump to Work Order already scoped to this record"). Every
  // pre-existing onNavigate(key) call site keeps working unchanged;
  // `context` is a new, optional second argument, not a breaking change
  // to the callback's shape.
  function handleNavigate(key, context) {
    const nextContext = context ?? {};
    window.history.pushState({}, "", workspaceLocation(key, nextContext));
    setActiveKey(key);
    setNavContext(nextContext);
  }
  useEffect(() => { const onPopState = () => { const location = parseWorkspaceLocation(window.location.pathname); if (location) { setActiveKey(location.key); setNavContext(location.context); } }; window.addEventListener("popstate", onPopState); return () => window.removeEventListener("popstate", onPopState); }, []);

  return (
    <WorkspaceProvider value={{ navigate: handleNavigate }}><div>
      <div className="no-print ltsa-tabs-row">
        <Tabs items={visibleTabs} activeKey={activeKey} onChange={handleNavigate} />
      </div>

      <div className="ltsa-workspace-content">
        <ActivePage onNavigate={handleNavigate} navContext={navContext} />
      </div>
    </div></WorkspaceProvider>
  );
}

