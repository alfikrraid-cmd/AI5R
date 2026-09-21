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
import "./ExecutiveDashboard.css";

/**
 * MWO-LTSA-DASHBOARD-ANALYTICS-001 -- Production-grade diagram-first maintenance
 * and reliability engineering analytics dashboard. Integrates server-side
 * aggregations, interactive SVG charts, cascading filter bar, and Equipment360 drill-down.
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

  // ROW 2 LEFT: Fleet Condition by Area
  const areaBreakdownData = useMemo(() => {
    if (analyticsData?.area_breakdown && analyticsData.area_breakdown.length > 0) {
      return analyticsData.area_breakdown;
    }
    if (overview?.contract_area_distribution) {
      return Object.entries(overview.contract_area_distribution).map(([area, count]) => ({
        area,
        pump_count: count,
        pm_count: 0,
        seal_leaks: 0,
      }));
    }
    return [];
  }, [analyticsData, overview]);

  // ROW 2 RIGHT: PM Compliance Donut
  const pmComplianceDonutData = useMemo(() => {
    const done = analyticsData?.kpis?.pm_done_count ?? (overview?.pm_schedule_count ? Math.floor(overview.pm_schedule_count * 0.8) : 0);
    const scheduled = analyticsData?.kpis?.pm_scheduled_count ?? overview?.pm_schedule_count ?? 0;
    const due = Math.max(0, scheduled - done);
    const overdue = overview?.work_order_status_distribution?.OPEN ?? overview?.work_order_count ?? 0;

    const items = [];
    if (done > 0) items.push({ label: "Completed", value: done, color: colors.success });
    if (due > 0) items.push({ label: "Due", value: due, color: colors.info });
    if (overdue > 0) items.push({ label: "Overdue / Open WO", value: overdue, color: colors.danger });
    return items;
  }, [analyticsData, overview]);

  // ROW 3 RIGHT: Mechanical Seal Condition Donut
  const sealConditionDonutData = useMemo(() => {
    const deLeaks = analyticsData?.kpis?.de_leaks ?? 0;
    const ndeLeaks = analyticsData?.kpis?.nde_leaks ?? 0;
    const totalMonitored = analyticsData?.kpis?.monitored_pumps ?? overview?.pump_count ?? 0;
    const totalLeaks = analyticsData?.kpis?.confirmed_seal_leaks ?? (deLeaks + ndeLeaks);
    const normal = Math.max(0, totalMonitored - totalLeaks);

    const items = [];
    if (normal > 0) items.push({ label: "Normal Condition", value: normal, color: colors.success });
    if (deLeaks > 0) items.push({ label: "Drive End (DE) Leak", value: deLeaks, color: colors.danger });
    if (ndeLeaks > 0) items.push({ label: "Non-Drive End (NDE) Leak", value: ndeLeaks, color: colors.warning });
    if (items.length === 0 && totalLeaks > 0) {
      items.push({ label: "Leak Evident", value: totalLeaks, color: colors.danger });
    }
    return items;
  }, [analyticsData, overview]);

  // ROW 5 RIGHT: Critical Spare Inventory Donut
  const criticalSpareDonutData = useMemo(() => {
    const inStock = overview?.seal_stock_count ?? sealData?.summary?.total_inventory_items ?? 0;
    const lowStock = overview?.low_stock_seal_count ?? sealData?.summary?.low_stock_count ?? 0;
    const registered = sealData?.summary?.total_registered_seals ?? overview?.pump_count ?? 0;

    const items = [];
    if (registered > 0) items.push({ label: "Installed Seals", value: registered, color: colors.info });
    if (inStock > 0) items.push({ label: "Spares in Stock", value: inStock, color: colors.success });
    if (lowStock > 0) items.push({ label: "Low Stock Alert", value: lowStock, color: colors.danger });
    return items;
  }, [overview, sealData]);

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
          {/* Row 1: Cascading Global Filter Bar */}
          <LtsaGlobalFilterBar filters={analyticsFilters} onFilterChange={setAnalyticsFilters} />

          {/* Row 1: Production Analytics KPI Strip */}
          {analyticsData?.kpis && (
            <AnalyticsKpiStrip
              kpis={analyticsData.kpis}
              healthScore={reliability?.fleet_health_score ?? summary?.overall_health}
              criticalSpareCount={summary?.critical_spare_count ?? reliability?.total_critical_spare_count ?? overview?.seal_stock_count}
            />
          )}

          {/* Preserved Fleet KPI Strip for command center status */}
          <FleetKpiStrip overview={overview} summary={summary} />

          {/* DIAGRAM-FIRST ANALYTICS ROWS */}
          {analyticsData && (
            <>
              {/* ROW 2: Fleet Health by Area (Bar) & PM Compliance (Donut) */}
              <div className="ltsa-diagram-grid-2col">
                <div className="ltsa-diagram-card">
                  <div className="ltsa-card-header">
                    <h3 className="ltsa-card-title">Fleet Health by Area</h3>
                    <span className="ltsa-card-badge">Area Distribution</span>
                  </div>
                  <BarChart
                    data={areaBreakdownData}
                    categoryKey="area"
                    bars={[
                      { key: "pump_count", label: "Pumps", color: colors.primary },
                      { key: "seal_leaks", label: "Active Leaks", color: colors.danger },
                      { key: "pm_count", label: "PM Done", color: colors.success },
                    ]}
                    title="Seal Leaks & PMs by Area"
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
                    title="PM Status Breakdown"
                  />
                </div>
              </div>

              {/* ROW 3: Condition Monitoring Trend (Line) & Mechanical Seal Condition (Donut) */}
              <div className="ltsa-diagram-grid-2col">
                <div className="ltsa-diagram-card">
                  <div className="ltsa-card-header">
                    <h3 className="ltsa-card-title">Condition Monitoring Trend</h3>
                    <span className="ltsa-card-badge">Vibration & Inspections</span>
                  </div>
                  <TimeSeriesChart
                    data={analyticsData.trends?.daily || []}
                    series={[
                      { key: "cmon_readings", label: "CM Inspections", color: colors.info },
                      { key: "seal_leaks", label: "Seal Leaks", color: colors.danger },
                    ]}
                    title="Condition Monitoring Readings vs Seal Leaks"
                  />
                </div>
                <div className="ltsa-diagram-card">
                  <div className="ltsa-card-header">
                    <h3 className="ltsa-card-title">Mechanical Seal Condition</h3>
                    <span className="ltsa-card-badge">DE / NDE Integrity</span>
                  </div>
                  <DonutChart
                    data={sealConditionDonutData}
                    title="Seal Integrity Status"
                  />
                </div>
              </div>

              {/* ROW 4: Maintenance Activity Trend (Full Width Line) */}
              <div className="ltsa-diagram-grid-full">
                <div className="ltsa-diagram-card">
                  <div className="ltsa-card-header">
                    <h3 className="ltsa-card-title">Maintenance Activity Trend</h3>
                    <span className="ltsa-card-badge">Full Timeline (PM / CM / Leaks)</span>
                  </div>
                  <TimeSeriesChart
                    data={analyticsData.trends?.daily || []}
                    series={[
                      { key: "pm_count", label: "PM Executed", color: colors.success },
                      { key: "cmon_readings", label: "CM Readings", color: colors.info },
                      { key: "seal_leaks", label: "Confirmed Leaks", color: colors.danger },
                    ]}
                    title="Daily PM Execution, CM Inspections, and Seal Leak Incidents"
                  />
                </div>
              </div>

              {/* ROW 5: Top Bad Actors (Horizontal Bar) & Critical Spare Inventory (Donut) */}
              <div className="ltsa-diagram-grid-2col">
                <div className="ltsa-diagram-card">
                  <div className="ltsa-card-header">
                    <h3 className="ltsa-card-title">Top Bad Actors / Highest Risk Pumps</h3>
                    <span className="ltsa-card-badge">Repeat Incidents</span>
                  </div>
                  <HorizontalBarChart
                    data={analyticsData.top_bad_actors || []}
                    title="Pumps with Highest Leak & Inspection Frequency"
                    onSelect={(pump) => setAnalyticsFilters((prev) => ({ ...prev, pump_tag: pump.pump_tag }))}
                  />
                </div>
                <div className="ltsa-diagram-card">
                  <div className="ltsa-card-header">
                    <h3 className="ltsa-card-title">Critical Spare Inventory</h3>
                    <span className="ltsa-card-badge">Stock vs Installed</span>
                  </div>
                  <DonutChart
                    data={criticalSpareDonutData}
                    title="Installed Seals vs Warehouse Spare Availability"
                  />
                </div>
              </div>

              {/* ROW 6: Surfaced Domain Analytics (Leaks by Pump Type & API Plan) */}
              {sealData && ((sealData.leaks_by_pump_type && sealData.leaks_by_pump_type.length > 0) || (sealData.leaks_by_api_plan && sealData.leaks_by_api_plan.length > 0)) && (
                <div className="ltsa-diagram-grid-2col">
                  {sealData.leaks_by_pump_type && sealData.leaks_by_pump_type.length > 0 && (
                    <div className="ltsa-diagram-card">
                      <div className="ltsa-card-header">
                        <h3 className="ltsa-card-title">Seal Leaks by Pump Type</h3>
                        <span className="ltsa-card-badge">Asset Classification</span>
                      </div>
                      <BarChart
                        data={sealData.leaks_by_pump_type}
                        categoryKey="pump_type"
                        bars={[{ key: "leak_count", label: "Leaks", color: colors.danger }]}
                        title="Incidents across Pump Types"
                      />
                    </div>
                  )}
                  {sealData.leaks_by_api_plan && sealData.leaks_by_api_plan.length > 0 && (
                    <div className="ltsa-diagram-card">
                      <div className="ltsa-card-header">
                        <h3 className="ltsa-card-title">Seal Leaks by API Piping Plan</h3>
                        <span className="ltsa-card-badge">Flush Plan Analysis</span>
                      </div>
                      <BarChart
                        data={sealData.leaks_by_api_plan}
                        categoryKey="api_plan"
                        bars={[{ key: "leak_count", label: "Leaks", color: colors.warning }]}
                        title="Incidents across API Flush Plans"
                      />
                    </div>
                  )}
                </div>
              )}

              {/* Bad Actors Table & Field Leak Findings */}
              <div className="ltsa-diagram-grid-2col">
                <Card title="Top Bad Actor Pumps (Repeat Leaks & Incidents)">
                  <BadActorsTable badActors={analyticsData.top_bad_actors || []} onNavigate={onNavigate} />
                </Card>
                <Card title="Field Leak Findings & Observations">
                  <HistoricalFindingsFeed findings={analyticsData.historical_findings || []} onNavigate={onNavigate} />
                </Card>
              </div>

              {/* Domain Analytics Tabs */}
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

          {/* Preserved Fleet Overview, Attention, and Registry Panels */}
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

          {/* Collapsible Copilot Drawer */}
          <div className={`copilot-drawer ${copilotOpen ? "open" : ""}`} style={{ display: copilotOpen ? "flex" : "none" }}>
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
              <CopilotPanel />
            </div>
          </div>
          {copilotOpen && (
            <div className="copilot-drawer-backdrop" onClick={() => setCopilotOpen(false)} />
          )}
        </>
      )}
    </div>
  );
}
