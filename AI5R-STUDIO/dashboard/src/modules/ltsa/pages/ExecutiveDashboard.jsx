import { useEffect, useState } from "react";
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
import BadActorsTable from "../components/BadActorsTable";
import HistoricalFindingsFeed from "../components/HistoricalFindingsFeed";
import DomainAnalyticsTabs from "../components/DomainAnalyticsTabs";
import "./ExecutiveDashboard.css";

/**
 * MWO-LTSA-DASHBOARD-ANALYTICS-001 -- Production-grade maintenance and reliability
 * analytics dashboard upgrade with server-side aggregated production data,
 * interactive SVG charts, cascading filter bar, and Equipment360 drill-down.
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

  return (
    <div className="executive-dashboard-layout">
      <PageHeader
        title="Executive Dashboard"
        subtitle="LTSA Engineering — Fleet Reliability & Maintenance Intelligence"
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

          {/* Row 2: Production Analytics KPI Strip */}
          {analyticsData?.kpis && <AnalyticsKpiStrip kpis={analyticsData.kpis} />}

          {/* Preserved Fleet KPI Strip for command center status */}
          <FleetKpiStrip overview={overview} summary={summary} />

          {/* Row 3: Interactive Visualizations (Time Series & Area Breakdown) */}
          {analyticsData && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "16px", marginBottom: "16px" }}>
              <Card title="Operational Activity & Incident Trends">
                <TimeSeriesChart
                  data={analyticsData.trends?.daily || []}
                  title="Daily PMs vs Confirmed Seal Leaks & Inspections"
                />
              </Card>
              <Card title="Contract Area Distribution & Compliance">
                <BarChart
                  data={analyticsData.area_breakdown || []}
                  categoryKey="area"
                  bars={[
                    { key: "seal_leaks", label: "Leaks", color: colors.danger },
                    { key: "pm_count", label: "PM Done", color: colors.success },
                  ]}
                  title="Seal Leaks & PMs by Area"
                  onSelectCategory={(area) => setAnalyticsFilters((prev) => ({ ...prev, area }))}
                />
              </Card>
            </div>
          )}

          {/* Row 4: Operational Intelligence (Bad Actors & Historical Observations) */}
          {analyticsData && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "16px", marginBottom: "16px" }}>
              <Card title="Top Bad Actor Pumps (Repeat Leaks & Incidents)">
                <BadActorsTable badActors={analyticsData.top_bad_actors || []} onNavigate={onNavigate} />
              </Card>
              <Card title="Field Leak Findings & Observations">
                <HistoricalFindingsFeed findings={analyticsData.historical_findings || []} onNavigate={onNavigate} />
              </Card>
            </div>
          )}

          {/* Row 5: Domain Analytics Tabs (Seals, Material Consumption, Effectiveness) */}
          {analyticsData && (
            <Card title="Domain Analytics & Reliability Engineering">
              <DomainAnalyticsTabs
                sealAnalytics={sealData}
                materialAnalytics={materialData}
                effectivenessAnalytics={effectivenessData}
                kpis={analyticsData.kpis || {}}
              />
            </Card>
          )}

          {/* Row 6: Main Fleet Grid + Copilot */}
          <div className="executive-dashboard-grid" style={{ marginTop: "16px" }}>
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

            <div className="executive-dashboard-copilot-rail">
              <CopilotPanel />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
