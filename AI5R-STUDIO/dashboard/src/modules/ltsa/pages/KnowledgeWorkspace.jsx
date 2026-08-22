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
          <aside className="inspector-rail" data-testid="knowledge-workspace-success">
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

            <KnowledgeSection
              id="summary"
              title="Equipment Summary"
              badge={data.equipment.status}
              footer={`Diperbarui ${data.equipment.lastUpdated ?? "-"}`}
            >
              <KnowledgeCard variant="grid">
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

            <KnowledgeSection id="pm-history" title="PM History" badge={String(data.pmHistory.length)}>
              <KnowledgeCard variant="row-list">
                <RefRows items={data.pmHistory} emptyTitle="Belum ada riwayat PM" />
              </KnowledgeCard>
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

            <KnowledgeSection id="drawings" title="Drawings" badge={String(data.drawings.length)}>
              <KnowledgeCard variant="row-list">
                <KnowledgeDrawingSection items={data.drawings} />
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

            <KnowledgeSection
              id="ai-insights"
              title="AI Insights"
              badge={data.aiInsights ? "Deterministic" : "Segera Hadir"}
              defaultOpen={false}
            >
              <KnowledgeCard variant="prose" locked={!data.aiInsights}>
                <KnowledgeAIInsight insight={data.aiInsights} />
              </KnowledgeCard>
            </KnowledgeSection>
          </aside>
        )}
      </div>
    </WorkspaceShell>
  );
}
