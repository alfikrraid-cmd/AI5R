import { useEffect, useState } from "react";
import { Button, Card, EmptyState, PageHeader } from "../../../design-system";
import { getFleetOverview, getFleetPowerBI, getFleetReliability, getLtsaAnalyticsExecutive, getLtsaAnalyticsFilters, getLtsaAnalyticsSeals, getLtsaAnalyticsMaterials, getLtsaAnalyticsEffectiveness } from "../../../api/ai5rClient";
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
import LtsaGlobalFilterBar, { ALL_AREAS } from "../components/LtsaGlobalFilterBar";
import AnalyticsKpiStrip from "../components/AnalyticsKpiStrip";
import TimeSeriesChart from "../components/charts/TimeSeriesChart";
import BarChart from "../components/charts/BarChart";
import BadActorsTable from "../components/BadActorsTable";
import HistoricalFindingsFeed from "../components/HistoricalFindingsFeed";
import DomainAnalyticsTabs from "../components/DomainAnalyticsTabs";
import "./ExecutiveDashboard.css";

// LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B -- the selected area persists in
// ?area= (bookmarkable/refreshable) but is never authorization: the backend
// narrows the caller's own scope and answers 403/422 for anything else.
function readAreaFromUrl() {
  if (typeof window === "undefined") return ALL_AREAS;
  const value = new URLSearchParams(window.location.search).get("area");
  return value && value.trim() ? value.trim().toUpperCase() : ALL_AREAS;
}

function writeAreaToUrl(area) {
  const params = new URLSearchParams(window.location.search);
  if (area === ALL_AREAS) params.delete("area");
  else params.set("area", area);
  const query = params.toString();
  window.history.replaceState(window.history.state, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
}

function isAuthorizationError(error) {
  return error?.status === 403 || error?.status === 422;
}

// TD-020 / knowledge-path breakdown: no production work-order column
// classifies breakdowns, so every breakdown count on this page is UNKNOWN
// and rendered N/A -- never the knowledge path's always-zero count.
const BREAKDOWN_NOT_AVAILABLE = "N/A";

/**
 * MWO-LTSA-DASHBOARD-ANALYTICS-001 -- Production-grade maintenance and reliability
 * analytics dashboard upgrade with server-side aggregated production data,
 * interactive SVG charts, cascading filter bar, and Equipment360 drill-down.
 *
 * LTSA_EXECUTIVE_DASHBOARD_AREA_SCOPED_R6B -- one global Area filter drives
 * every area-dependent request (fleet + analytics) with the same `area`.
 * Changing it clears all previous-area data before the new requests run, so
 * a previous area's KPIs are never shown while another area loads.
 */
export default function ExecutiveDashboard({ onNavigate }) {
  const [area, setArea] = useState(readAreaFromUrl);
  const [authorizedAreas, setAuthorizedAreas] = useState([]);
  const [filterOptions, setFilterOptions] = useState({ pumps: [], date_range: {} });

  const [overview, setOverview] = useState(null);
  const [overviewError, setOverviewError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reliability, setReliability] = useState(null);
  const [summary, setSummary] = useState(null);
  const [unauthorized, setUnauthorized] = useState(null);

  const [analyticsFilters, setAnalyticsFilters] = useState({});
  const [analyticsData, setAnalyticsData] = useState(null);
  const [sealData, setSealData] = useState(null);
  const [materialData, setMaterialData] = useState(null);
  const [effectivenessData, setEffectivenessData] = useState(null);

  const areaParams = area === ALL_AREAS ? {} : { area };

  // Authorized area options + pump/date options: once, from the backend.
  useEffect(() => {
    let active = true;
    getLtsaAnalyticsFilters()
      .then((data) => {
        if (!active || !data) return;
        setAuthorizedAreas(Array.isArray(data.authorized_areas) ? data.authorized_areas : []);
        setFilterOptions({ pumps: data.pumps || [], date_range: data.date_range || {} });
      })
      .catch(() => {
        // Options unavailable: only "All Areas" is offered.
      });
    return () => {
      active = false;
    };
  }, []);

  // Fleet datasets for the selected area.
  useEffect(() => {
    let active = true;
    setLoading(true);
    setOverview(null);
    setOverviewError(null);
    setReliability(null);
    setSummary(null);
    setUnauthorized(null);

    // Required: the bounded core Fleet Overview.
    getFleetOverview(areaParams)
      .then((result) => {
        if (active) {
          setOverview(result.data);
        }
      })
      .catch((err) => {
        if (!active) return;
        if (isAuthorizationError(err)) {
          setUnauthorized(err.code || "area_not_in_scope");
        } else {
          setOverviewError(err?.message ?? "Fleet Overview data unavailable");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    // Optional: fan-out backed reliability and Power BI calls
    Promise.all([getFleetReliability(areaParams), getFleetPowerBI(areaParams)])
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [area]);

  // Analytics datasets for the selected area + pump/date filters.
  useEffect(() => {
    let active = true;
    setAnalyticsData(null);
    setSealData(null);
    setMaterialData(null);
    setEffectivenessData(null);
    if (typeof getLtsaAnalyticsExecutive === "function") {
      const params = { ...analyticsFilters, ...areaParams };
      Promise.allSettled([
        getLtsaAnalyticsExecutive(params),
        typeof getLtsaAnalyticsSeals === "function" ? getLtsaAnalyticsSeals(params) : Promise.resolve(null),
        typeof getLtsaAnalyticsMaterials === "function" ? getLtsaAnalyticsMaterials(params) : Promise.resolve(null),
        typeof getLtsaAnalyticsEffectiveness === "function" ? getLtsaAnalyticsEffectiveness(params) : Promise.resolve(null),
      ]).then(([execRes, sealRes, matRes, effRes]) => {
        if (!active) return;
        if (execRes.status === "rejected" && isAuthorizationError(execRes.reason)) {
          setUnauthorized(execRes.reason.code || "area_not_in_scope");
          return;
        }
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [area, analyticsFilters]);

  function handleAreaChange(nextArea) {
    const normalized = nextArea || ALL_AREAS;
    if (normalized === area) return;
    writeAreaToUrl(normalized);
    // A pump picked in the previous area does not carry over.
    setAnalyticsFilters((prev) => ({ ...prev, pump_tag: undefined }));
    setArea(normalized);
  }

  const areaLabel =
    area === ALL_AREAS ? "All Areas" : authorizedAreas.find((option) => option.code === area)?.label ?? area;

  const filterBar = (
    <LtsaGlobalFilterBar
      area={area}
      authorizedAreas={authorizedAreas}
      onAreaChange={handleAreaChange}
      filterOptions={filterOptions}
      filters={analyticsFilters}
      onFilterChange={setAnalyticsFilters}
    />
  );

  return (
    <div className="executive-dashboard-layout">
      <PageHeader
        title="Executive Dashboard"
        subtitle={`LTSA Engineering — Fleet Reliability & Maintenance Intelligence · ${areaLabel}`}
      />

      {filterBar}

      {unauthorized ? (
        <>
          <div data-testid="dashboard-unauthorized">
            <EmptyState
              title="Area not authorized"
              description={
                unauthorized === "invalid_area"
                  ? `"${area}" is not a recognized area.`
                  : `You are not authorized to view ${areaLabel}. Only your authorized areas can be shown.`
              }
            />
            <Button onClick={() => handleAreaChange(ALL_AREAS)}>Show All Areas</Button>
          </div>
          <QuickNavigationPanel onNavigate={onNavigate} />
        </>
      ) : loading ? (
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
          <EmptyState
            title="No fleet data available"
            description={
              area === ALL_AREAS
                ? "No pumps were found within your authorized areas."
                : `No pumps were found in ${areaLabel}.`
            }
          />
          <QuickNavigationPanel onNavigate={onNavigate} />
        </>
      ) : (
        <>
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
                  onSelectCategory={(selected) => {
                    // Drill-down only into an authorized canonical area.
                    if (authorizedAreas.some((option) => option.code === selected)) {
                      handleAreaChange(selected);
                    }
                  }}
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
                {/* Seal stock is fleet-wide (not area-attributable): the
                    backend returns it only for an unrestricted, unfiltered
                    view; otherwise the panel is hidden, never shown beside
                    area KPIs. */}
                {overview.seal_stock_count !== null && overview.seal_stock_count !== undefined && (
                  <SealInventoryPanel overview={overview} />
                )}
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
                    breakdownCount={BREAKDOWN_NOT_AVAILABLE}
                    criticalSpareCount={reliability.total_critical_spare_count}
                  />

                  <FleetMainArea
                    criticalAssetCount={summary.critical_asset_count}
                    topRisks={summary.top_risks}
                    insight={summary.insight}
                  />

                  <FleetExecutiveSummary summary={{ ...summary, breakdown_count: BREAKDOWN_NOT_AVAILABLE }} />
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
