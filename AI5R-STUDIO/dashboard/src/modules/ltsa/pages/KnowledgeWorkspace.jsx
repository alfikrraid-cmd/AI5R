import KnowledgeSection from "../components/KnowledgeSection";
import KnowledgeCard, { EmptySection } from "../components/KnowledgeCard";
import ActivePlansPanel from "../components/ActivePlansPanel";
import KnowledgeTimeline from "../components/KnowledgeTimeline";
import KnowledgeSummary from "../components/KnowledgeSummary";
import KnowledgeInventory from "../components/KnowledgeInventory";
import KnowledgeSeal from "../components/KnowledgeSeal";
import KnowledgeAIInsight from "../components/KnowledgeAIInsight";
import KnowledgeDrawingSection from "../components/KnowledgeDrawingSection";
import KnowledgeRecommendation from "../components/KnowledgeRecommendation";
import AssetHeaderKpis from "../components/AssetHeaderKpis";
import AssetSectionNav from "../components/AssetSectionNav";
import KnowledgeConditionMonitoringSection from "../components/KnowledgeConditionMonitoringSection";
import KnowledgeUnifiedHistory from "../components/KnowledgeUnifiedHistory";
import KnowledgePmHistorySection from "../components/KnowledgePmHistorySection";
import KnowledgeWorkOrdersSection from "../components/KnowledgeWorkOrdersSection";
import CopilotPanel from "../components/CopilotPanel";
import { useKnowledgeWorkspace } from "../hooks/useKnowledgeWorkspace";
import WorkspaceShell from "../workspace/WorkspaceShell";
import { useWorkspaceTheme } from "../workspace/WorkspaceTheme";
import "./MaintenanceHistory.css";
import "./KnowledgeWorkspace.css";

// MWO-LTSA-032A -- KnowledgeWorkspace: the canonical LTSA Knowledge
// Workspace, built exactly from the approved Open Design
// (DESIGN/LTSA/KNOWLEDGE_PANEL/knowledge-panel-spec.md, ODR-LTSA-031E-R1).
// Consumes exactly one API (GET /api/ltsa/pumps/{tag}/knowledge, via
// useKnowledgeWorkspace) -- every one of the 12 sections below is derived
// from that single response, never a second fetch. No backend, API,
// Gateway, SQL, Workflow, or Router logic lives here -- Router only on
// the backend side (MWO-LTSA-031D); this file is presentation only.
//
// MWO-LTSA-036F -- Active Plans mounted between Equipment Summary and
// Equipment Timeline, per ActivePlansPanel's own header comment ("what
// SHOULD happen... deliberately separate from the History timeline below
// it, since a Plan is not a past event"). ActivePlansPanel is reused
// unmodified and renders its own Card/title, so it is placed directly
// inside KnowledgeSection without a KnowledgeCard wrapper (unlike every
// other section) -- wrapping it in a second card shell would nest two
// title bars for no reason. onNavigate is intentionally not passed:
// KnowledgeWorkspace's prop contract stays host-agnostic ({ tag }, per
// Open Design ODR-LTSA-031E-R1 §8 D7), so Condition Monitoring Schedule
// rows render as ActivePlansPanel's own tested non-interactive fallback
// rather than this MWO adding a navigation prop to that contract.

function RefRows({ items, emptyTitle }) {
  if (!items.length) {
    return <EmptySection title={emptyTitle} />;
  }

  return items.map((item) => (
    <div className="part-item" key={item.id}>
      <div className="part-row">
        <span className="part-name">{item.name}</span>
        {item.flag ? <span className={`stock-flag ${item.flag}`}>{item.flagLabel ?? item.flag}</span> : null}
      </div>
      <div className="part-meta">{item.meta}</div>
    </div>
  ));
}

function LoadingSkeleton() {
  return (
    <div className="inspector-rail" data-testid="knowledge-workspace-loading">
      {[0, 1, 2].map((row) => (
        <div className="rail-section" key={row}>
          <div className="skel skel-text skel-line-sm" />
          <div className="skel skel-text skel-line-lg" />
          <div className="skel skel-text skel-line-md" />
        </div>
      ))}
    </div>
  );
}

export default function KnowledgeWorkspace({ tag }) {
  const [theme, setTheme] = useWorkspaceTheme();
  const { data, loading, error, refetch, refresh } = useKnowledgeWorkspace(tag);

  // MWO-LTSA-036I -- Breadcrumb, Theme Toggle, and Command Palette are now
  // WorkspaceShell's own chrome, reused unchanged from MaintenanceHistory.jsx.
  // Only shown once a tag is known, mirroring MaintenanceHistory's own
  // "no chrome-bar until an asset is selected" precedent -- no new logic,
  // no new data derivation, `tag` is the same prop this component already
  // receives.
  return (
    <WorkspaceShell
      className="knowledge-workspace"
      theme={theme}
      onToggleTheme={tag ? () => setTheme((current) => (current === "dark" ? "light" : "dark")) : undefined}
      breadcrumb={
        tag ? (
          <>
            <span>Asset 360</span>
            <span className="sep">›</span>
            <b>{tag}</b>
          </>
        ) : undefined
      }
      commandPaletteActions={tag ? [] : undefined}
      commandPaletteTag={tag}
    >
      <div className="knowledge-workspace-standalone">
        {loading ? (
          <LoadingSkeleton />
        ) : error ? (
          <div className="eng-empty is-error" data-testid="knowledge-workspace-error">
            <h4>Gagal memuat data</h4>
            <p>{error}</p>
            <button type="button" className="btn-link" onClick={refetch}>
              Coba Lagi
            </button>
          </div>
        ) : !data ? (
          <div className="eng-empty" data-testid="knowledge-workspace-empty">
            <h4>Belum ada peralatan dipilih</h4>
          </div>
        ) : (
          // MWO-LTSA-ASSET360-UI-PRODUCTION-HARDENING-001 -- .workspace-grid/
          // .object-column/.inspector-rail are reused verbatim from
          // MaintenanceHistory.css (already scoped under this same
          // .pump-workspace-root WorkspaceShell applies, already responsive
          // -- see its own @media max-width:980px rule). Root cause of the
          // narrow-desktop-column defect: this page previously put every
          // section inside a bare .inspector-rail (a component CSS-designed
          // to be the narrow 336px SIDE column of that grid, sticky-
          // positioned) with no accompanying wide .object-column, and
          // .knowledge-workspace-standalone additionally capped the whole
          // page at max-width:336px (KnowledgeWorkspace.css) -- copied from
          // .inspector-rail's own sidebar width as if it were meant for the
          // whole page. No new CSS/design language: reference/context
          // sections (Mechanical Seal, Compatible Seals, Inventory,
          // Drawings) now live in the sidebar rail; every other section
          // (Equipment Summary, Active Plans, Timeline, PM/CM/Breakdown
          // History, Recommendation, AI Insights) lives in the wide main
          // column -- the exact main/sidebar split this MWO's own guidance
          // describes, and the same shape MaintenanceHistory.jsx (the
          // richer, pre-existing implementation this was ported from)
          // already uses.
          <div className="workspace-grid" data-testid="knowledge-workspace-success">
            <main className="object-column">
              <div className="rail-section kn-header-row">
                <div>
                  <span className="eyebrow">{data.equipment.tag}</span>
                  <h2 className="rail-title">{data.equipment.name ?? data.equipment.tag}</h2>
                </div>
                <button
                  type="button"
                  className="btn-link"
                  data-testid="knowledge-workspace-refresh"
                  aria-label="Muat ulang data peralatan"
                  onClick={refresh}
                >
                  Muat Ulang
                </button>
              </div>

              {/* MWO-LTSA-ASSET360-CONSOLIDATION-001 -- Section navigator:
                  page anchors only (scrollIntoView), never a route change. */}
              <AssetSectionNav />

              <KnowledgeSection
                id="summary"
                title="Equipment Summary"
                badge={data.equipment.condition}
                footer={`Data dihasilkan ${data.equipment.lastUpdated ?? "-"}`}
              >
                <KnowledgeCard variant="grid">
                  {/* Section A -- Asset Header/Health KPI cards, derived
                      entirely from data already fetched on this page. */}
                  <AssetHeaderKpis
                    equipment={data.equipment}
                    mechanicalSeal={data.mechanicalSeal}
                    pmOccurrences={data.pmOccurrences}
                    conditionMonitoringReadings={data.conditionMonitoringReadings}
                    workOrders={data.workOrders}
                  />
                  <KnowledgeSummary equipment={data.equipment} />
                </KnowledgeCard>
              </KnowledgeSection>

              <KnowledgeSection
                id="active-plans"
                title="Active Plans"
                badge={String(data.activePlans.pmSchedules.length + data.activePlans.conditionMonitoringSchedules.length)}
              >
                <ActivePlansPanel
                  pmSchedules={data.activePlans.pmSchedules}
                  conditionMonitoringSchedules={data.activePlans.conditionMonitoringSchedules}
                />
              </KnowledgeSection>

              <KnowledgeSection id="timeline" title="Equipment Timeline" badge={`${data.timeline.length} peristiwa`}>
                <KnowledgeTimeline items={data.timeline} />
              </KnowledgeSection>

              {/* Section C -- Condition Monitoring: latest snapshot, ALL
                  temperature points (DE/NDE), trend chart (3M/6M/1Y/3Y/4Y/
                  All), and browsable reading history without leaving
                  Asset 360. */}
              <KnowledgeSection
                id="condition"
                title="Condition Monitoring"
                badge={String(data.conditionMonitoringReadings.length)}
              >
                <KnowledgeConditionMonitoringSection readings={data.conditionMonitoringReadings} />
              </KnowledgeSection>

              {/* Section D -- Unified Maintenance History: one chronological
                  DISPLAY combining PM/CMON/CM/WO/Breakdown, "Same Visit"
                  presentation logic only when a real PM and real CMON share
                  a calendar date. Underlying records are never merged. */}
              <KnowledgeSection id="maintenance" title="Unified Maintenance History">
                <KnowledgeUnifiedHistory
                  pmOccurrences={data.pmOccurrences}
                  conditionMonitoringReadings={data.conditionMonitoringReadings}
                  workOrders={data.workOrders}
                  cmHistory={data.cmHistory}
                  breakdownHistory={data.breakdownHistory}
                  lifecycleTimeline={data.lifecycleTimeline}
                />
              </KnowledgeSection>

              {/* Section E -- Preventive Maintenance History: full PM
                  occurrence detail (activities/checklist, source
                  traceability, UNSCHEDULED::* visibly identified), never
                  used to derive a schedule/frequency. */}
              <KnowledgeSection id="pm-history" title="PM History" badge={String(data.pmOccurrences.length)}>
                <KnowledgePmHistorySection pmOccurrences={data.pmOccurrences} />
              </KnowledgeSection>

              <KnowledgeSection id="cm-history" title="CM History" badge={String(data.cmHistory.length)}>
                <KnowledgeCard variant="row-list">
                  <RefRows items={data.cmHistory} emptyTitle="Belum ada riwayat CM" />
                </KnowledgeCard>
              </KnowledgeSection>

              <KnowledgeSection id="breakdown-history" title="Breakdown History" badge={String(data.breakdownHistory.length)}>
                <KnowledgeCard variant="row-list">
                  <RefRows items={data.breakdownHistory} emptyTitle="Belum ada riwayat breakdown" />
                </KnowledgeCard>
              </KnowledgeSection>

              <KnowledgeSection
                id="recommendation"
                title="Recommendation"
                badge={String(data.recommendations.length)}
              >
                <KnowledgeCard variant="prose">
                  <KnowledgeRecommendation recommendations={data.recommendations} loading={false} error={null} />
                </KnowledgeCard>
              </KnowledgeSection>

              {/* Section B -- AI Engineering Summary: the existing
                  deterministic (non-LLM) insight engine, kept unchanged --
                  compact, pump-scoped-only, always was. Distinct from
                  Section J's interactive Copilot below. */}
              <KnowledgeSection
                id="ai-insights"
                title="AI Engineering Summary"
                badge={data.aiInsights ? "Deterministic" : "Segera Hadir"}
                defaultOpen={false}
              >
                <KnowledgeCard variant="prose" locked={!data.aiInsights}>
                  <KnowledgeAIInsight insight={data.aiInsights} />
                </KnowledgeCard>
              </KnowledgeSection>

              {/* Section H -- Work Orders: this pump's own open/in-progress/
                  historical work orders only, never fleet-wide. */}
              <KnowledgeSection id="work-orders" title="Work Orders" badge={String(data.workOrders.length)}>
                <KnowledgeWorkOrdersSection workOrders={data.workOrders} />
              </KnowledgeSection>

              {/* Section J -- AI Engineering Copilot: the same CopilotPanel/
                  useCopilot already used unchanged by ExecutiveDashboard.jsx
                  (fleet-wide, no assetContext there), reused here with this
                  page's own tag as assetContext -- exactly the reuse its own
                  header comment already anticipated. Never calls OpenRouter
                  except on a real user-submitted question. */}
              <KnowledgeSection id="ai-copilot" title="AI Engineering Copilot">
                <CopilotPanel assetContext={tag} />
              </KnowledgeSection>
            </main>

            <aside className="inspector-rail">
              <KnowledgeSection id="seal" title="Mechanical Seal" badge={data.mechanicalSeal?.status}>
                <KnowledgeCard variant="kv">
                  <KnowledgeSeal configuredSeal={data.configuredSeal} currentSeal={data.mechanicalSeal} />
                </KnowledgeCard>
              </KnowledgeSection>

              <KnowledgeSection id="compat-seals" title="Compatible Seals" badge={String(data.compatibleSeals.length)}>
                <KnowledgeCard variant="row-list">
                  <RefRows items={data.compatibleSeals} emptyTitle="Belum ada seal kompatibel" />
                </KnowledgeCard>
              </KnowledgeSection>

              <KnowledgeSection
                id="inventory"
                title="Inventory"
                badge={`${data.inventory.filter((item) => item.level === "low" || item.level === "out").length} Rendah`}
              >
                <KnowledgeCard variant="row-list">
                  <KnowledgeInventory items={data.inventory} />
                </KnowledgeCard>
              </KnowledgeSection>

              <KnowledgeSection id="drawings" title="Drawings" badge={String(data.drawings.length)}>
                <KnowledgeCard variant="row-list">
                  <KnowledgeDrawingSection items={data.drawings} />
                </KnowledgeCard>
              </KnowledgeSection>

              {/* MWO-LTSA-ASSET360-COMPLETENESS-FIX-021B (item B) -- a
                  genuinely separate section from Drawings above, bound to
                  the Knowledge API's own `documents` key (reused,
                  unfiltered EquipmentTimelineService._list_documents()
                  output). KnowledgeDrawingSection is reused unmodified --
                  documents come from the same seal_engineering_document
                  table/shape, just not filtered to document_type ==
                  "DRAWING" -- no new component, no new visual language. */}
              <KnowledgeSection id="documents" title="Documents" badge={String(data.documents.length)}>
                <KnowledgeCard variant="row-list">
                  <KnowledgeDrawingSection items={data.documents} />
                </KnowledgeCard>
              </KnowledgeSection>
            </aside>
          </div>
        )}
      </div>
    </WorkspaceShell>
  );
}
