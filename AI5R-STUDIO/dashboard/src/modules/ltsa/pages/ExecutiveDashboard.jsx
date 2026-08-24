import { useEffect, useState } from "react";
import { Card, EmptyState, PageHeader } from "../../../design-system";
import { getFleetOverview, getFleetPowerBI, getFleetReliability } from "../../../api/ai5rClient";
import FleetKpiStrip from "../components/FleetKpiStrip";
import BasicFleetOverviewPanel from "../components/BasicFleetOverviewPanel";
import AssetsAttentionPanel from "../components/AssetsAttentionPanel";
import MaintenanceActivityPanel from "../components/MaintenanceActivityPanel";
import SealInventoryPanel from "../components/SealInventoryPanel";
import FleetHero from "../components/FleetHero";
import FleetMetricsGrid from "../components/FleetMetricsGrid";
import FleetMainArea from "../components/FleetMainArea";
import FleetExecutiveSummary from "../components/FleetExecutiveSummary";
import QuickNavigationPanel from "../components/QuickNavigationPanel";
import CopilotPanel from "../components/CopilotPanel";
import "./ExecutiveDashboard.css";

/**
 * MWO-LTSA-040A -- Executive Dashboard Redesign. Replaces the previous
 * RC-002 dashboard's sample-data sections (KPI/Health/Alerts/Readiness/
 * Insight/Opportunity/Digital Twin, plus the two duplicated Fleet KPI
 * boxes FleetReliabilityPanel/FleetPowerBIPanel rendered side by side)
 * with the Hero/Metrics/Main Area/Bottom layout this mission specifies --
 * per its explicit "Remove old static executive cards... Remove
 * duplicated KPI sections." Every removed component remains on disk,
 * individually valid and still covered by its own dedicated test file
 * (KpiCardGrid.test.jsx etc.) -- simply no longer wired into this page,
 * the same "orphaned, not deleted" precedent MWO-LTSA-036M already
 * established for PMWorkspace.jsx. FleetReliabilityPanel.jsx and
 * FleetPowerBIPanel.jsx are untouched for the same reason: their own
 * internal grouping (one flat card of 6 metric tiles each) doesn't match
 * this Open Design's Hero/Metrics/Main Area/Bottom regions, so this page
 * builds new, focused presentational components instead of repurposing
 * them -- restructuring either panel in place would have broken its own
 * 25 passing tests for no benefit, since neither is rendered here anymore.
 *
 * QuickNavigationPanel is the one section kept from the old page,
 * unmodified: it isn't a "static executive card," a KPI section, or
 * sample/demo data -- it's this dashboard's real workspace-navigation
 * entry point, and LTSAWorkspace.test.jsx's own cross-page navigation
 * flows (e.g. "Open Pump Registry", "Open Asset 360") depend on it being
 * reachable from here, confirmed by running that suite against an earlier
 * draft of this page that omitted it.
 *
 * MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- visual/layout redesign only,
 * data-fetch logic below is byte-identical to MWO-LTSA-DASHBOARD-RECOVERY-
 * 001's: FleetKpiStrip (always-visible top strip), the Fleet Overview /
 * Assets Attention / Maintenance Activity / Seal Inventory panels, and
 * Quick Actions (QuickNavigationPanel, retitled) replace the previous
 * flat stack of sections with the Command Center's KPI-strip -> two-
 * column (Fleet Overview + Copilot) -> two-column (Assets Attention +
 * Maintenance Activity) -> two-column (Seal Inventory + Quick Actions)
 * layout. No new fetch, no new field, no changed loading/error/empty
 * gate -- every one of these new panels reads fields BasicFleetOverview
 * already had (see basic_fleet_overview_service.py), just relocated
 * across more focused, denser panels instead of one long stack.
 *
 * MWO-LTSA-DASHBOARD-RECOVERY-001 -- Fleet Overview's REQUIRED data source
 * is now GET /api/ltsa/fleet/overview (BasicFleetOverviewService): one
 * call per canonical bulk-list gateway on the backend, no per-pump
 * LTSAKnowledgeService/n8n fan-out, so it stays fast and reliable at real
 * fleet size. GET /api/ltsa/fleet/reliability and .../powerbi (both still
 * backed by that per-pump fan-out) are now OPTIONAL: fetched separately,
 * and their failure/timeout never blocks or errors the core Fleet
 * Overview -- FleetHero/FleetMetricsGrid/FleetMainArea/
 * FleetExecutiveSummary simply do not render if that richer data isn't
 * available, exactly the "Power BI must be optional" requirement,
 * generalized to the Reliability call too since it shares the same
 * fan-out cost. No new calculation -- every displayed number is a field
 * an API already computed.
 */
export default function ExecutiveDashboard({ onNavigate }) {
  const [overview, setOverview] = useState(null);
  const [overviewError, setOverviewError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reliability, setReliability] = useState(null);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    let active = true;

    // Required: the bounded core Fleet Overview. This is the only fetch
    // the loading/error/empty gate below waits on.
    getFleetOverview()
      .then((result) => {
        if (active) {
          setOverview(result.data);
          setOverviewError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setOverviewError(err?.message ?? "Fleet Overview data unavailable");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    // Optional: the richer, fan-out-backed Reliability/Power BI panels.
    // Failure here is silently absorbed -- reliability/summary simply
    // stay null and their panels don't render -- it must never surface
    // as a page-level error or block the required overview above.
    Promise.all([getFleetReliability(), getFleetPowerBI()])
      .then(([reliabilityResult, powerbiResult]) => {
        if (active) {
          setReliability(reliabilityResult.data);
          setSummary(powerbiResult.data);
        }
      })
      .catch(() => {
        // intentionally no-op: optional data, no error state for it
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="executive-dashboard-layout">
      <PageHeader
        title="Executive Dashboard"
        subtitle="LTSA Engineering — Fleet Reliability & Maintenance Intelligence"
      />

      {loading ? (
        <>
          <Card title="Fleet Overview">
            <p>Loading executive dashboard...</p>
          </Card>
          <QuickNavigationPanel onNavigate={onNavigate} />
        </>
      ) : overviewError ? (
        <>
          <Card title="Fleet Overview">
            <p role="alert">{overviewError}</p>
          </Card>
          <QuickNavigationPanel onNavigate={onNavigate} />
        </>
      ) : !overview || overview.pump_count === 0 ? (
        <>
          <EmptyState title="No fleet data available" description="No pumps were found in the registry." />
          <QuickNavigationPanel onNavigate={onNavigate} />
        </>
      ) : (
        <>
          <FleetKpiStrip overview={overview} summary={summary} />

          {/* MWO-LTSA-GATE-C -- main fleet content + AI Engineering
              Copilot as a right-side rail on desktop, stacking below on
              narrow viewports (see ExecutiveDashboard.css's
              .executive-dashboard-grid). DOM order is main-then-copilot
              so the CSS grid's single-column fallback stacks Copilot
              BELOW the primary content -- Copilot's own loading/answer
              state is independent of the fleet fetches above, so this
              placement does not change how soon it's usable, only where
              it sits. */}
          <div className="executive-dashboard-grid">
            <div className="executive-dashboard-main">
              <BasicFleetOverviewPanel overview={overview} />

              <div className="executive-dashboard-attention-row">
                <AssetsAttentionPanel summary={summary} />
                <MaintenanceActivityPanel overview={overview} />
              </div>

              <div className="executive-dashboard-bottom-row">
                <SealInventoryPanel overview={overview} />
                <QuickNavigationPanel onNavigate={onNavigate} />
              </div>

              {/* Optional richer overlay -- only rendered when the
                  fan-out-backed Reliability/Power BI calls above
                  succeeded. Their absence is silent: no error, no empty
                  state, this section just doesn't appear. */}
              {reliability && summary ? (
                <>
                  <FleetHero healthScore={reliability.fleet_health_score} status={summary.fleet_status} />

                  <FleetMetricsGrid
                    availability={reliability.fleet_availability}
                    mtbfDays={reliability.fleet_mtbf_days}
                    mttrHours={reliability.fleet_mttr_hours}
                    pumpCount={reliability.pump_count}
                    breakdownCount={reliability.total_breakdown_count}
                    criticalSpareCount={reliability.total_critical_spare_count}
                  />

                  <FleetMainArea
                    criticalAssetCount={summary.critical_asset_count}
                    topRisks={summary.top_risks}
                    insight={summary.insight}
                  />

                  <FleetExecutiveSummary summary={summary} />
                </>
              ) : null}
            </div>

            <div className="executive-dashboard-copilot-rail">
              <CopilotPanel />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
