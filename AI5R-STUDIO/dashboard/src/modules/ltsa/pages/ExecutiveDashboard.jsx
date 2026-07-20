import { PageHeader } from "../../../design-system";
import KpiCardGrid from "../components/KpiCardGrid";
import MaintenanceHealthPanel from "../components/MaintenanceHealthPanel";
import AttentionAssetList from "../components/AttentionAssetList";
import UpcomingMaintenanceList from "../components/UpcomingMaintenanceList";
import RecentActivityFeed from "../components/RecentActivityFeed";
import QuickNavigationPanel from "../components/QuickNavigationPanel";
import {
  buildAttentionAssets,
  buildKpiSummary,
  buildMaintenanceHealth,
  buildRecentActivities,
  buildUpcomingMaintenance,
} from "../utils/executiveDashboard";
import "./ExecutiveDashboard.css";

/**
 * The Plant Manager's landing page: "Is our maintenance operation healthy
 * today?" answered in the order a manager actually needs it — KPIs first,
 * then health, then what needs attention, then what's coming, then the
 * activity log, and only then links out to the detailed workspaces.
 * Every number is derived fresh from the existing LTSA sample data on
 * every render — nothing here is hardcoded, stored, or fetched.
 */
export default function ExecutiveDashboard({ onNavigate }) {
  const kpis = buildKpiSummary();
  const health = buildMaintenanceHealth();
  const attentionAssets = buildAttentionAssets();
  const upcomingMaintenance = buildUpcomingMaintenance();
  const recentActivities = buildRecentActivities();

  return (
    <div className="executive-dashboard-layout">
      <PageHeader title="Executive Dashboard" subtitle="LTSA Engineering — Maintenance Operations Overview" />

      <KpiCardGrid kpis={kpis} />

      <MaintenanceHealthPanel health={health} />

      <AttentionAssetList assets={attentionAssets} />

      <UpcomingMaintenanceList schedules={upcomingMaintenance} />

      <RecentActivityFeed activities={recentActivities} />

      <QuickNavigationPanel onNavigate={onNavigate} />
    </div>
  );
}
