import { useEffect, useMemo, useState } from "react";
import { EmptyState, PageHeader, Panel } from "../../../design-system";
import AssetSelector from "../components/AssetSelector";
import { getCMReports, getPumps } from "../../../api/ai5rClient";
import { mapPumpRecord } from "../utils/pumpMapping";
import { mapCMReportRecord, withResolvedArea } from "../utils/cmMapping";
import LTSASidebar from "../components/LTSASidebar";
import { IconSun } from "../components/PumpWorkspaceIcons";
import { IconBell } from "../components/LTSANavIcons";
import CopilotPanel from "../components/CopilotPanel";
import { can, PERMISSIONS } from "../auth/permissions";
import { useOptionalAuth } from "../auth/AuthContext";
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
import WhatsAppGroupsView from "./WhatsAppGroupsView";
import { WorkspaceProvider } from "../workspace/WorkspaceContext";
import { parseWorkspaceLocation, workspaceLocation } from "../workspace/WorkspaceRegistry";
import "../design/ltsaTokens.css";
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
  { key: "drawing", label: "Drawing" },
  { key: "document", label: "Document" },
  { key: "installation", label: "Installation" },
  { key: "workorder", label: "Work Order" },
  { key: "pm", label: "Preventive Maintenance" },
  { key: "cm", label: "Corrective Maintenance" },
  { key: "cmon", label: "Condition Monitoring" },
  // UI/UX Redesign Phase B -- three new sidebar-only entries. Each is a
  // thin routing adapter over existing pages/data (see PAGES below and
  // the KnowledgeLanding/AIInsightRoute/FailureAnalysisRoute components
  // further down this file), not new business logic or a new backend
  // call. Reachability rules unchanged: TAB_PERMISSIONS gates visibility
  // exactly like every tab above.
  { key: "failure", label: "Failure Analysis" },
  { key: "knowledge", label: "Knowledge" },
  { key: "ai-insight", label: "AI Insight" },
  { key: "knowledgereview", label: "Knowledge Review" },
  { key: "import", label: "Import" },
  { key: "history", label: "Asset 360" },
  { key: "reports", label: "Reports" },
  { key: "analytics", label: "Analytics" },
  // MWO-LTSA-PM-CMON-HISTORICAL-BATCH-REVIEW-ROUTING-019A -- relabeled
  // from "Historical Data Review" (ambiguous against the newer
  // "Historical Batch Review" below -- the owner's own report). The
  // route/key/page ("/ltsa/historical-review" -> HistoricalReview, the
  // DFE candidate-extraction review) is unchanged; label only.
  { key: "historical-review", label: "Historical Candidate Review" },
  { key: "historical-batch-review", label: "Historical Batch Review" },
  // AI5R-WHATSAPP-GROUP-ADMIN-001 -- gated on admin.users via
  // TAB_PERMISSIONS (permissions.js), same as every other tab here; no
  // nested "Admin" submenu exists in this flat Tabs bar today, so this
  // is surfaced as its own top-level, permission-gated tab rather than
  // inventing a new nav grouping concept for one entry.
  { key: "whatsapp-groups", label: "WhatsApp Groups" },
];

// UI/UX Redesign Phase B -- the persistent left sidebar groups the same
// TABS entries above under the mission's target navigation taxonomy
// (Dashboard/Pump/Mechanical Seal/Work Order/PM/Condition Monitoring/
// Failure Analysis/Inventory/Knowledge/AI Insight, plus the existing
// "history" tab under the forward-looking "Asset360" position -- it is
// already the real, working Asset 360 surface, just previously reachable
// only via Pump -> View History or the tab bar, never fabricated). Every
// other pre-existing tab (Drawing, Document, Installation, Corrective
// Maintenance, Knowledge Review, Import, Reports, Analytics, both
// Historical Review tabs, WhatsApp Groups) stays fully reachable under
// "More" -- nothing above is hidden or removed, only regrouped for
// display. TABS/PAGES themselves are unchanged in shape, so
// LTSAWorkspace.consolidation.test.jsx's source-text assertions keep
// passing unmodified.
const PRIMARY_NAV_KEYS = [
  "dashboard",
  "pump",
  "seal",
  "workorder",
  "pm",
  "cmon",
  "failure",
  "knowledge",
  "ai-insight",
  "history",
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

// UI/UX Redesign Phase B -- "Knowledge" sidebar entry. Both destinations
// (Knowledge Review, Document Library) already exist as their own TABS/
// PAGES entries, unchanged; this is only a new landing page linking to
// them (mission decision: preserve both existing capabilities under one
// nav item rather than picking a single winner). Knowledge Review is
// only offered when the session actually holds that permission --
// useOptionalAuth() never throws without a provider (see its own header
// comment), degrading to "link hidden" for any render without one (e.g.
// a bare unit test), never a crash.
function KnowledgeLanding({ onNavigate }) {
  const session = useOptionalAuth()?.session ?? null;
  const showKnowledgeReview = can(session, PERMISSIONS.KNOWLEDGEREVIEW_READ);

  return (
    <div className="ltsa-landing">
      <PageHeader title="Knowledge" subtitle="Engineering knowledge and document capabilities" />
      <div className="ltsa-landing-grid">
        <Panel>
          <h2>Document Library</h2>
          <p>Engineering documents, drawings, and reference material already on file.</p>
          <button type="button" onClick={() => onNavigate("document")}>
            Open Document Library
          </button>
        </Panel>
        {showKnowledgeReview ? (
          <Panel>
            <h2>Knowledge Review</h2>
            <p>Curation queue for engineering knowledge under internal review.</p>
            <button type="button" onClick={() => onNavigate("knowledgereview")}>
              Open Knowledge Review
            </button>
          </Panel>
        ) : null}
      </div>
    </div>
  );
}

// UI/UX Redesign Phase B -- "AI Insight" sidebar entry. Mounts the same
// global CopilotPanel already embedded in ExecutiveDashboard (unscoped
// -- no assetContext, same as that existing usage), just as its own
// first-class destination instead of only appearing inside the
// Dashboard. No new AI capability, no new backend call.
function AIInsightRoute() {
  return (
    <div className="ltsa-landing">
      <PageHeader
        title="AI Insight"
        subtitle="Fact, inference, and recommendation over existing equipment, PM/CM, seal, and inventory data."
      />
      <CopilotPanel />
    </div>
  );
}

// UI/UX Redesign Phase B -- "Failure Analysis" sidebar entry.
// FailureAnalysisWorkspace itself is pre-existing and untouched (it was
// deep-link-only, reachable solely from a Corrective Maintenance
// report); this adapter reuses the same getCMReports() data source and
// mapping utilities FailureAnalysisWorkspace already imports to offer a
// picker in front of it, mirroring the AssetLauncher pattern above --
// no new backend endpoint, no new business logic.
function FailureAnalysisLauncher({ onSelect }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    getCMReports()
      .then((items) => Promise.all(items.map(mapCMReportRecord).map(withResolvedArea)))
      .then((mapped) => {
        if (active) {
          setReports(mapped);
        }
      })
      .catch(() => {
        if (active) {
          setReports([]);
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
    <div className="ltsa-landing">
      <PageHeader title="Failure Analysis" subtitle="Select a Corrective Maintenance report to open its failure analysis." />
      {loading ? (
        <Panel>
          <p>Loading corrective maintenance reports...</p>
        </Panel>
      ) : reports.length === 0 ? (
        <EmptyState
          title="No corrective maintenance reports"
          description="Failure analysis opens from an existing Corrective Maintenance report."
        />
      ) : (
        <Panel>
          <ul className="ltsa-failure-picker-list">
            {reports.map((report) => (
              <li key={report.id}>
                <button type="button" onClick={() => onSelect(report)}>
                  {report.equipmentTag ?? "N/A"} — {report.failureDescription ?? "Failure report"}
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}

function FailureAnalysisRoute({ navContext }) {
  const [selected, setSelected] = useState(
    navContext?.selectId ? { selectId: navContext.selectId, assetTag: navContext.assetTag } : null
  );

  if (!selected) {
    return (
      <FailureAnalysisLauncher
        onSelect={(report) => setSelected({ selectId: report.id, assetTag: report.equipmentTag })}
      />
    );
  }

  return <FailureAnalysisWorkspace navContext={selected} />;
}

const PAGES = {
  dashboard: ExecutiveDashboard,
  pump: Pump,
  seal: Seal,
  inventory: Seal,
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
  failure: FailureAnalysisRoute,
  knowledge: KnowledgeLanding,
  "ai-insight": AIInsightRoute,
  "knowledge-workspace": KnowledgeWorkspaceRoute,
  history: KnowledgeWorkspaceRoute,
  "history-legacy": MaintenanceHistory,
  "pm-workspace": PMWorkOrderWorkspace,
  reports: ReportsWorkspace,
  analytics: AnalyticsWorkspace,
  "historical-review": HistoricalReview,
  "historical-batch-review": HistoricalBatchReview,
  "whatsapp-groups": WhatsAppGroupsView,
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

  // UI/UX Redesign Phase B -- split the already permission-filtered
  // `visibleTabs` into the sidebar's two display groups. Order within
  // "primary" follows PRIMARY_NAV_KEYS (the mission's nav taxonomy), not
  // TABS' own declaration order; "more" keeps every remaining visible
  // tab, in its existing TABS order.
  const navGroups = useMemo(() => {
    const byKey = new Map(visibleTabs.map((tab) => [tab.key, tab]));
    const primary = PRIMARY_NAV_KEYS.map((key) => byKey.get(key)).filter(Boolean);
    const more = visibleTabs.filter((tab) => !PRIMARY_NAV_KEYS.includes(tab.key));
    const groups = [{ heading: null, items: primary }];
    if (more.length > 0) {
      groups.push({ heading: "More", items: more });
    }
    return groups;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleTabs]);

  const activeTabLabel = TABS.find((tab) => tab.key === activeKey)?.label ?? "";

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
    <WorkspaceProvider value={{ navigate: handleNavigate }}>
      <div className="ltsa-shell">
        <div className="no-print">
          <LTSASidebar groups={navGroups} activeKey={activeKey} onChange={handleNavigate} />
        </div>

        <div className="ltsa-main">
          <div className="no-print ltsa-topbar">
            <span className="ltsa-topbar-title">{activeTabLabel}</span>
            {/* UI-D1.2 -- decorative icon row matching Chief's reference
                topbar (theme toggle / notifications). No real dark-mode or
                notification backend exists yet -- these are visual-parity
                placeholders only, not wired to any behavior, so they never
                claim a capability this phase doesn't actually add. */}
            <div className="ltsa-topbar-icons" aria-hidden="true">
              <span className="ltsa-topbar-icon"><IconSun /></span>
              <span className="ltsa-topbar-icon"><IconBell /></span>
            </div>
          </div>

          <div className="ltsa-workspace-content">
            <ActivePage onNavigate={handleNavigate} navContext={navContext} />
          </div>
        </div>
      </div>
    </WorkspaceProvider>
  );
}

