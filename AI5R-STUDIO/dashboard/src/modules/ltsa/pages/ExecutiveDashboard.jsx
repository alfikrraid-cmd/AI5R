import { PageHeader } from "../../../design-system";
import DashboardTopBar from "../components/DashboardTopBar";
import KpiCardGrid from "../components/KpiCardGrid";
import FleetReliabilityPanel from "../components/FleetReliabilityPanel";
import FleetPowerBIPanel from "../components/FleetPowerBIPanel";
import EngineeringReadinessPanel from "../components/EngineeringReadinessPanel";
import MaintenanceHealthPanel from "../components/MaintenanceHealthPanel";
import EngineeringAlertsPanel from "../components/EngineeringAlertsPanel";
import EngineeringInsightPanel from "../components/EngineeringInsightPanel";
import BusinessOpportunityPanel from "../components/BusinessOpportunityPanel";
import AttentionAssetList from "../components/AttentionAssetList";
import ImmediateActionTable from "../components/ImmediateActionTable";
import UpcomingMaintenanceList from "../components/UpcomingMaintenanceList";
import RecentActivityFeed from "../components/RecentActivityFeed";
import QuickNavigationPanel from "../components/QuickNavigationPanel";
import DigitalTwinPanel from "../components/DigitalTwinPanel";
import {
  buildAttentionAssets,
  buildEngineeringAlerts,
  buildEngineeringReadiness,
  buildKpiSummary,
  buildMaintenanceHealth,
  buildRecentActivities,
  buildUpcomingMaintenance,
} from "../utils/executiveDashboard";
import "./ExecutiveDashboard.css";

/**
 * The Plant Manager's / Reliability Engineering Lead's landing page,
 * per RC-002 (Executive Dashboard React Implementation) extending
 * MWO-LTSA-063 (closed). Every original MWO-063 section (KPI, Maintenance
 * Health, Assets Requiring Attention, Upcoming Maintenance, Recent
 * Activities, Quick Navigation) is retained unchanged in its original
 * position and heading text -- nothing discarded, nothing renamed, no
 * existing test broken. New RC-002 widgets are inserted between the
 * existing ones (Engineering Readiness, Engineering Alerts, Today's
 * Engineering Insight, Business Opportunity, Assets Requiring Immediate
 * Action, Digital Twin) plus a Top Bar above everything. Every number is
 * derived fresh from existing LTSA sample data on every render (or is a
 * disclosed placeholder where no data source exists) — nothing here is
 * hardcoded or stored. MWO-LTSA-037D's FleetReliabilityPanel is the one
 * exception: it fetches the real Fleet Reliability API on its own, self-
 * contained, on mount -- every other section on this page is still pure
 * sample-data derivation, unchanged.
 */
export default function ExecutiveDashboard({ onNavigate }) {
  const kpis = buildKpiSummary();
  const health = buildMaintenanceHealth();
  const readiness = buildEngineeringReadiness();
  const alerts = buildEngineeringAlerts();
  const attentionAssets = buildAttentionAssets();
  const upcomingMaintenance = buildUpcomingMaintenance();
  const recentActivities = buildRecentActivities();

  return (
    <div className="executive-dashboard-layout">
      <PageHeader title="Executive Dashboard" subtitle="LTSA Engineering — Maintenance Operations Overview" />

      <DashboardTopBar onNavigate={onNavigate} />

      <KpiCardGrid kpis={kpis} health={health} />

      {/* MWO-LTSA-037D -- the only real (non-sample-data) section on this
          page today: fetches the real Fleet Reliability API on its own,
          independent of every other section here's synchronous sample-data
          derivation. */}
      <FleetReliabilityPanel />

      {/* MWO-LTSA-038B -- Power BI Dashboard foundation: a second, separate
          real (non-sample-data) section, fetching the real Power BI API on
          its own. Not a replacement for FleetReliabilityPanel above --
          that panel's own MWO-037C endpoint is unrelated to and untouched
          by this one. */}
      <FleetPowerBIPanel />

      <EngineeringReadinessPanel readiness={readiness} />

      <MaintenanceHealthPanel health={health} />

      <EngineeringAlertsPanel alerts={alerts} />

      <EngineeringInsightPanel />

      <BusinessOpportunityPanel />

      <AttentionAssetList assets={attentionAssets} />

      <ImmediateActionTable assets={attentionAssets} />

      <UpcomingMaintenanceList schedules={upcomingMaintenance} />

      <RecentActivityFeed activities={recentActivities} onNavigate={onNavigate} />

      <QuickNavigationPanel onNavigate={onNavigate} />

      <DigitalTwinPanel />
    </div>
  );
}
