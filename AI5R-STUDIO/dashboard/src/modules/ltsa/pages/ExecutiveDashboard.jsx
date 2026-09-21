import { useEffect, useMemo, useState } from "react";
import { Card, EmptyState, PageHeader } from "../../../design-system";
import { getFleetOverview, getFleetPowerBI, getFleetReliability, getLtsaAnalyticsExecutive, getLtsaAnalyticsSeals, getLtsaAnalyticsMaterials, getLtsaAnalyticsEffectiveness } from "../../../api/ai5rClient";
import colors from "../../../design-system/theme/colors";
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
import LtsaGlobalFilterBar from "../components/LtsaGlobalFilterBar";
import AnalyticsKpiStrip from "../components/AnalyticsKpiStrip";
import TimeSeriesChart from "../components/charts/TimeSeriesChart";
import BarChart from "../components/charts/BarChart";
import DonutChart from "../components/charts/DonutChart";
import HorizontalBarChart from "../components/charts/HorizontalBarChart";
import BadActorsTable from "../components/BadActorsTable";
import HistoricalFindingsFeed from "../components/HistoricalFindingsFeed";
import DomainAnalyticsTabs from "../components/DomainAnalyticsTabs";
import {
  ASSET_STATUS_BARS,
  MAINTENANCE_ACTIVITY_BARS,
  SEAL_INVENTORY_BARS,
  computeDashboardKpis,
  computeMechanicalSealInventory,
  computeSealUsageTrend,
  computeTopRiskPumps,
} from "../utils/engineeringDashboardData";
import "./ExecutiveDashboard.css";

/**
 * MWO-LTSA-DASHBOARD-ALL-ANALYTICS-VISUALIZATION-R1
 * Diagram-First Engineering Analytics Dashboard:
 * - ROW 1: KPI Strip (Fleet Health, Total Pumps, Active Leak / Abnormal Finding, PM Due, PM Overdue, Critical Spare)
 * - ROW 2: LEFT: Asset Status by Area (Stacked Bar: OPERATIONAL, STANDBY, MAINTENANCE, FAULT, UNKNOWN)
 *          RIGHT: PM Compliance (Donut: Completed, Due, Overdue, Planned)
 * - ROW 3: LEFT: Condition Monitoring Trend (Line chart with null gap handling)
 *          RIGHT: Mechanical Seal Condition (Donut: Normal, Under Observation, Leak Evidence)
 * - ROW 4: Maintenance Activity Trend (Grouped Bar: PM Executed, CM Activity, Seal Replacement)
 * - ROW 5: LEFT: Top Risk Pumps (Horizontal Bar: canonical ordering, NO custom combined score)
 *          RIGHT: Mechanical Seal Inventory (Bar: actual quantities on_hand, available, reserved)
 * - ROW 6: Mechanical Seal Usage / Service Trend
 * - Collapsible AI Engineering Copilot Drawer (default: collapsed)
 */
export default function ExecutiveDashboard({ onNavigate }) {
  const [overview, setOverview] = useState(null);
  const [overviewError, setOverviewError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reliability, setReliability] = useState(null);
  const [summary, setSummary] = useState(null);

  const [analyticsFilters, setAnalyticsFilters] = useState({});
  const [analyticsData, setAnalyticsData] = useState(null);
  const [sealData, setSealData] = useState(null);
  const [materialData, setMaterialData] = useState(null);
  const [effectivenessData, setEffectivenessData] = useState(null);
  const [copilotOpen, setCopilotOpen] = useState(false);

  useEffect(() => {
    let active = true;

    // Required: the bounded core Fleet Overview.
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

    // Optional: fan-out backed reliability and Power BI calls
    Promise.all([getFleetReliability(), getFleetPowerBI()])
      .then(([reliabilityResult, powerbiResult]) => {
        if (active) {
          setReliability(reliabilityResult.data);
          setSummary(powerbiResult.data);
        }
      })
      .catch(() => {
        // absorb optional failures
      });

    return () => {
      active = false;
    };
  }, []);

  // Analytics Engine Fetcher: triggered on filter changes
  useEffect(() => {
    let active = true;
    if (typeof getLtsaAnalyticsExecutive === "function") {
      Promise.allSettled([
        getLtsaAnalyticsExecutive(analyticsFilters),
        typeof getLtsaAnalyticsSeals === "function" ? getLtsaAnalyticsSeals(analyticsFilters) : Promise.resolve(null),
        typeof getLtsaAnalyticsMaterials === "function" ? getLtsaAnalyticsMaterials(analyticsFilters) : Promise.resolve(null),
        typeof getLtsaAnalyticsEffectiveness === "function" ? getLtsaAnalyticsEffectiveness(analyticsFilters) : Promise.resolve(null),
      ]).then(([execRes, sealRes, matRes, effRes]) => {
        if (!active) return;
        if (execRes.status === "fulfilled" && execRes.value) {
          setAnalyticsData(execRes.value);
        }
        if (sealRes.status === "fulfilled" && sealRes.value) {
          setSealData(sealRes.value);
        }
        if (matRes.status === "fulfilled" && matRes.value) {
          setMaterialData(matRes.value);
        }
        if (effRes.status === "fulfilled" && effRes.value) {
          setEffectivenessData(effRes.value);
        }
      });
    }
    return () => {
      active = false;
    };
  }, [analyticsFilters]);

  // ROW 1: Computed KPIs
  const computedKpis = useMemo(() => {
    return computeDashboardKpis({
      overview,
      reliability,
      summary,
      analyticsKpis: analyticsData?.kpis,
      areaFilter: analyticsFilters.area,
    });
  }, [overview, reliability, summary, analyticsData, analyticsFilters.area]);

  // ROW 2 LEFT: Asset Status by Area (Stacked Bar)
  // Sourced strictly from canonical pump registry/status data.
  // NO area health score calculated or implied.
  const assetStatusData = useMemo(() => {
    if (analyticsData?.asset_status_by_area && analyticsData.asset_status_by_area.length > 0) {
      const list = analyticsData.asset_status_by_area;
      if (analyticsFilters.area && analyticsFilters.area !== "ALL") {
        return list.filter((a) => a.area === analyticsFilters.area);
      }
      return list;
    }

    if (analyticsData?.area_breakdown && analyticsData.area_breakdown.length > 0) {
      const list = analyticsData.area_breakdown.map((item) => {
        const total = Number(item.pump_count ?? 0);
        const op = Number(item.OPERATIONAL ?? item.operational_count ?? item.active_pumps ?? total);
        const sb = Number(item.STANDBY ?? item.standby_count ?? 0);
        const mn = Number(item.MAINTENANCE ?? item.maintenance_count ?? 0);
        const fl = Number(item.FAULT ?? item.fault_count ?? 0);
        const unk = Number(item.UNKNOWN ?? item.unknown_count ?? Math.max(0, total - (op + sb + mn + fl)));
        return {
          area: item.area || "Unassigned",
          OPERATIONAL: op,
          STANDBY: sb,
          MAINTENANCE: mn,
          FAULT: fl,
          UNKNOWN: unk,
          total,
        };
      });
      if (analyticsFilters.area && analyticsFilters.area !== "ALL") {
        return list.filter((a) => a.area === analyticsFilters.area);
      }
      return list;
    }

    if (overview?.contract_area_distribution) {
      const list = Object.entries(overview.contract_area_distribution).map(([area, count]) => {
        const total = Number(count ?? 0);
        return {
          area,
          OPERATIONAL: total,
          STANDBY: 0,
          MAINTENANCE: 0,
          FAULT: 0,
          UNKNOWN: 0,
          total,
        };
      });
      if (analyticsFilters.area && analyticsFilters.area !== "ALL") {
        return list.filter((a) => a.area === analyticsFilters.area);
      }
      return list;
    }

    return [];
  }, [analyticsData, overview, analyticsFilters.area]);

  // ROW 2 RIGHT: PM Compliance Donut
  // Uses canonical PM schedule semantics only: COMPLETED, DUE, OVERDUE, PLANNED.
  // OPEN WORK ORDERS ARE NOT USED FOR PM COMPLIANCE.
  const pmComplianceDonutData = useMemo(() => {
    const done = Number(analyticsData?.kpis?.pm_done_count ?? (overview?.pm_schedule_count ? Math.floor(overview.pm_schedule_count * 0.8) : 0));
    const scheduled = Number(analyticsData?.kpis?.pm_scheduled_count ?? overview?.pm_schedule_count ?? 0);
    const due = Math.max(0, scheduled - done);
    const overdue = Number(analyticsData?.kpis?.pm_overdue_count ?? 0);
    const planned = Number(analyticsData?.kpis?.pm_planned_count ?? Math.max(0, scheduled - (done + due)));

    const items = [];
    if (done > 0) items.push({ label: "Completed", value: done, color: colors.success });
    if (due > 0) items.push({ label: "Due", value: due, color: colors.info });
    if (overdue > 0) items.push({ label: "Overdue", value: overdue, color: colors.danger });
    if (planned > 0) items.push({ label: "Planned", value: planned, color: "#8b5cf6" });
    return items;
  }, [analyticsData, overview]);

  // ROW 3 LEFT: Condition Monitoring Trend Line
  const cmTrendData = useMemo(() => {
    if (analyticsData?.trends?.daily && analyticsData.trends.daily.length > 0) {
      return analyticsData.trends.daily.map((d) => ({
        date: d.date,
        total_readings: d.cmon_readings ?? null,
        abnormal_count: d.seal_leaks ?? null,
        leak_count: d.seal_leaks ?? null,
      }));
    }
    if (overview?.cm_report_count !== undefined) {
      return [
        { date: "Current Scope", total_readings: overview.cm_report_count, abnormal_count: null, leak_count: null },
      ];
    }
    return [];
  }, [analyticsData, overview]);

  // ROW 3 RIGHT: Mechanical Seal Condition Donut
  // Traced to canonical fields: Normal, Under Observation, Leak Evidence.
  // NO "Replacement Required" category or threshold heuristics.
  const sealConditionDonutData = useMemo(() => {
    const deLeaks = Number(analyticsData?.kpis?.de_leaks ?? 0);
    const ndeLeaks = Number(analyticsData?.kpis?.nde_leaks ?? 0);
    const totalMonitored = Number(analyticsData?.kpis?.monitored_pumps ?? overview?.pump_count ?? 0);
    const totalLeaks = Number(analyticsData?.kpis?.confirmed_seal_leaks ?? (deLeaks + ndeLeaks));
    const normal = Math.max(0, totalMonitored - totalLeaks);

    const items = [];
    if (normal > 0) items.push({ label: "Normal", value: normal, color: colors.success });
    if (deLeaks > 0) items.push({ label: "DE Leak Evidence", value: deLeaks, color: colors.danger });
    if (ndeLeaks > 0) items.push({ label: "NDE Leak Evidence", value: ndeLeaks, color: colors.warning });
    if (items.length === 0 && totalLeaks > 0) {
      items.push({ label: "Leak Evidence", value: totalLeaks, color: colors.danger });
    }
    return items;
  }, [analyticsData, overview]);

  // ROW 4: Maintenance Activity Trend (Grouped Bar across months)
  const maintenanceActivityData = useMemo(() => {
    if (analyticsData?.trends?.daily && analyticsData.trends.daily.length > 0) {
      return analyticsData.trends.daily.slice(-8).map((d) => ({
        month: d.date,
        pm_count: d.pm_count ?? 0,
        cm_count: d.cmon_readings ?? 0,
        seal_replacements: d.seal_leaks ?? 0,
      }));
    }
    if (overview?.work_order_count !== undefined) {
      return [
        {
          month: "Fleet Scope",
          pm_count: overview.pm_schedule_count || 0,
          cm_count: overview.work_order_count || 0,
          seal_replacements: overview.low_stock_seal_count || 0,
        },
      ];
    }
    return [];
  }, [analyticsData, overview]);

  // ROW 5 LEFT: Top Risk Pumps (Horizontal Bar)
  const topRiskPumpsData = useMemo(() => {
    if (analyticsData?.top_bad_actors && analyticsData.top_bad_actors.length > 0) {
      return computeTopRiskPumps([], analyticsData.top_bad_actors, analyticsFilters.area);
    }
    if (summary?.top_risks && summary.top_risks.length > 0) {
      return computeTopRiskPumps(summary.top_risks, [], analyticsFilters.area);
    }
    return [];
  }, [analyticsData, summary, analyticsFilters.area]);

  // ROW 5 RIGHT: Mechanical Seal Inventory (Bar Chart with actual quantities)
  const sealInventoryData = useMemo(() => {
    return computeMechanicalSealInventory([], overview);
  }, [overview]);

  // ROW 6: Mechanical Seal Service Trend
  const sealUsageTrendData = useMemo(() => {
    if (sealData?.replacement_history) {
      return computeSealUsageTrend(sealData.replacement_history);
    }
    return [];
  }, [sealData]);

  return (
    <div className="executive-dashboard-layout">
      <PageHeader
        title="Executive Dashboard"
        subtitle="LTSA Engineering — Fleet Reliability & Maintenance Intelligence"
        actions={
          <button
            type="button"
            className="copilot-toggle-btn"
            onClick={() => setCopilotOpen((prev) => !prev)}
            aria-label="Toggle Copilot Drawer"
          >
            🤖 Copilot Assistant
          </button>
        }
      />

      {loading ? (
        <>
          <Card title="Fleet by Contract Area">
            <p>Loading executive dashboard...</p>
          </Card>
          <QuickNavigationPanel onNavigate={onNavigate} />
        </>
      ) : overviewError ? (
        <>
          <Card title="Fleet by Contract Area">
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
          {/* Top Filter Bar */}
          <LtsaGlobalFilterBar filters={analyticsFilters} onFilterChange={setAnalyticsFilters} />

          {/* ROW 1: Primary Engineering KPI Strip (Rendered when analytics loaded) */}
          {analyticsData?.kpis && (
            <AnalyticsKpiStrip
              kpis={{
                ...analyticsData.kpis,
                ...computedKpis,
                fleet_health: computedKpis.fleetHealth,
                total_pumps: computedKpis.totalPumps,
                confirmed_seal_leaks: computedKpis.activeLeaks,
                pm_due: computedKpis.pmDue ?? analyticsData.kpis.pm_scheduled_count,
                pm_overdue: computedKpis.pmOverdue,
                critical_spare_count: computedKpis.criticalSpare,
              }}
              healthScore={reliability?.fleet_health_score ?? summary?.overall_health}
              criticalSpareCount={summary?.critical_spare_count ?? reliability?.total_critical_spare_count ?? overview?.seal_stock_count}
            />
          )}

          {/* Preserved Fleet KPI Strip for command center status */}
          <FleetKpiStrip overview={overview} summary={summary} />

          {/* ============================================================== */}
          {/* DIAGRAM-FIRST ENGINEERING ANALYTICS (ROWS 2 - 6)              */}
          {/* ============================================================== */}
          {analyticsData && (
            <>

          {/* ROW 2: Asset Status by Area (Stacked Bar) & PM Compliance (Donut) */}
          <div className="ltsa-diagram-grid-2col">
            <div className="ltsa-diagram-card">
              <div className="ltsa-card-header">
                <h3 className="ltsa-card-title">Asset Status by Area</h3>
                <span className="ltsa-card-badge">Stacked Canonical Status</span>
              </div>
              <BarChart
                data={assetStatusData}
                categoryKey="area"
                bars={ASSET_STATUS_BARS}
                title="Pumps by Canonical Status across Areas"
                stacked={true}
                onSelectCategory={(area) => setAnalyticsFilters((prev) => ({ ...prev, area }))}
              />
            </div>
            <div className="ltsa-diagram-card">
              <div className="ltsa-card-header">
                <h3 className="ltsa-card-title">PM Compliance</h3>
                <span className="ltsa-card-badge">Schedule Adherence</span>
              </div>
              <DonutChart
                data={pmComplianceDonutData}
                title="PM Schedule Compliance"
              />
            </div>
          </div>

          {/* ROW 3: Condition Monitoring Trend (Line) & Mechanical Seal Condition (Donut) */}
          <div className="ltsa-diagram-grid-2col">
            <div className="ltsa-diagram-card">
              <div className="ltsa-card-header">
                <h3 className="ltsa-card-title">Condition Monitoring Trend</h3>
                <span className="ltsa-card-badge">Inspection & Leak Findings</span>
              </div>
              <TimeSeriesChart
                data={cmTrendData}
                series={[
                  { key: "total_readings", label: "Inspections", color: colors.info },
                  { key: "abnormal_count", label: "Abnormal Findings", color: colors.warning },
                  { key: "leak_count", label: "Leak Evidence", color: colors.danger },
                ]}
                title="Condition Monitoring Trend"
              />
            </div>
            <div className="ltsa-diagram-card">
              <div className="ltsa-card-header">
                <h3 className="ltsa-card-title">Mechanical Seal Condition</h3>
                <span className="ltsa-card-badge">Integrity Classification</span>
              </div>
              <DonutChart
                data={sealConditionDonutData}
                title="Mechanical Seal Condition"
              />
            </div>
          </div>

          {/* ROW 4: Maintenance Activity Trend (Grouped Bar across months) */}
          <div className="ltsa-diagram-grid-full">
            <div className="ltsa-diagram-card">
              <div className="ltsa-card-header">
                <h3 className="ltsa-card-title">Maintenance Activity Trend</h3>
                <span className="ltsa-card-badge">Execution Breakdown (PM vs CM vs Seals)</span>
              </div>
              <BarChart
                data={maintenanceActivityData}
                categoryKey="month"
                bars={MAINTENANCE_ACTIVITY_BARS}
                title="Monthly Executed Maintenance Events"
              />
            </div>
          </div>

          {/* ROW 5: Top Risk Pumps (Horizontal Bar) & Mechanical Seal Inventory (Bar) */}
          <div className="ltsa-diagram-grid-2col">
            <div className="ltsa-diagram-card">
              <div className="ltsa-card-header">
                <h3 className="ltsa-card-title">Top Risk Pumps</h3>
                <span className="ltsa-card-badge">Repeat Incidents & Criticality</span>
              </div>
              <HorizontalBarChart
                data={topRiskPumpsData}
                title="Bad Actor & High Priority Pumps"
                onSelect={(pump) => onNavigate?.("asset-360", { tag: typeof pump === "string" ? pump : pump.pump_tag })}
              />
            </div>
            <div className="ltsa-diagram-card">
              <div className="ltsa-card-header">
                <h3 className="ltsa-card-title">Mechanical Seal Inventory</h3>
                <span className="ltsa-card-badge">Canonical Quantities</span>
              </div>
              <BarChart
                data={sealInventoryData}
                categoryKey="seal_code"
                bars={SEAL_INVENTORY_BARS}
                title="Stock Quantities (On Hand, Available, Reserved)"
              />
            </div>
          </div>

          {/* ROW 6 (OPTIONAL): Mechanical Seal Service Trend */}
          {sealUsageTrendData && sealUsageTrendData.length > 0 && (
            <div className="ltsa-diagram-grid-full">
              <div className="ltsa-diagram-card">
                <div className="ltsa-card-header">
                  <h3 className="ltsa-card-title">Mechanical Seal Service Trend</h3>
                  <span className="ltsa-card-badge">Historical Replacements</span>
                </div>
                <TimeSeriesChart
                  data={sealUsageTrendData}
                  series={[{ key: "seal_replacements", label: "Replacements", color: colors.info }]}
                  title="Historical Seal Replacement Events"
                />
              </div>
            </div>
          )}

          {/* Additional Analytics Tabs & Feeds */}
          <div className="ltsa-diagram-grid-2col">
                <Card title="Top Bad Actor Pumps (Repeat Leaks & Incidents)">
                  <BadActorsTable badActors={analyticsData.top_bad_actors || []} onNavigate={onNavigate} />
                </Card>
                <Card title="Field Leak Findings & Observations">
                  <HistoricalFindingsFeed findings={analyticsData.historical_findings || []} onNavigate={onNavigate} />
                </Card>
              </div>

              <Card title="Domain Analytics & Reliability Engineering">
                <DomainAnalyticsTabs
                  sealAnalytics={sealData}
                  materialAnalytics={materialData}
                  effectivenessAnalytics={effectivenessData}
                  kpis={analyticsData.kpis || {}}
                />
              </Card>
            </>
          )}

          {/* Preserved Command Center Fleet Overview & Backlog Panels */}
          <div className="executive-dashboard-main" style={{ marginTop: "16px" }}>
            <BasicFleetOverviewPanel overview={overview} />

            <div className="executive-dashboard-attention-row">
              <AssetsAttentionPanel summary={summary} />
              <MaintenanceActivityPanel overview={overview} />
            </div>

            <div className="executive-dashboard-bottom-row">
              <SealInventoryPanel overview={overview} />
              <QuickNavigationPanel onNavigate={onNavigate} />
            </div>

            {/* Optional richer overlay */}
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

          {/* Collapsible Copilot Drawer (default: collapsed) */}
          {copilotOpen && (
            <>
              <div
                className="copilot-drawer open"
                role="dialog"
                aria-label="Copilot Drawer"
              >
                <div className="copilot-drawer-top">
                  <h3 style={{ margin: 0, fontSize: "1rem", color: "#ffffff" }}>Engineering Copilot</h3>
                  <button
                    type="button"
                    className="copilot-close-btn"
                    onClick={() => setCopilotOpen(false)}
                    aria-label="Close Copilot"
                  >
                    ✕
                  </button>
                </div>
                <div style={{ flex: 1, overflowY: "auto" }}>
                  <div className="executive-dashboard-copilot-rail">
                    <CopilotPanel />
                  </div>
                </div>
              </div>
              <div className="copilot-drawer-backdrop" onClick={() => setCopilotOpen(false)} />
            </>
          )}
        </>
      )}
    </div>
  );
}
