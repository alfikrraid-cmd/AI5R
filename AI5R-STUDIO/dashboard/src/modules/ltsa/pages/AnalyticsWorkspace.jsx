import { PageHeader } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import KpiCardGrid from "../components/KpiCardGrid";
import MaintenanceHealthPanel from "../components/MaintenanceHealthPanel";
import AttentionAssetList from "../components/AttentionAssetList";
import CriticalityDistributionList from "../components/CriticalityDistributionList";
import ActivityTrendTable from "../components/ActivityTrendTable";
import RecommendedActionsList from "../components/RecommendedActionsList";
import { buildAttentionAssets, buildKpiSummary, buildMaintenanceHealth } from "../utils/executiveDashboard";
import { buildActivityTrend, buildCriticalityDistribution, buildRecommendedActions } from "../utils/analytics";

function QuestionHeading({ children }) {
  return (
    <h2 style={{ color: colors.text, marginTop: spacing.lg, marginBottom: spacing.sm }}>{children}</h2>
  );
}

/**
 * Manager-first Analytics workspace, structured around the four questions
 * the Product Owner asked it to answer, in priority order: Maintenance
 * KPIs and Maintenance Health answer "are we healthy?"; Asset Criticality
 * Distribution and Assets Requiring Attention (reused from the Executive
 * Dashboard, MWO-LTSA-063) answer "what needs attention?"; the Activity
 * Trend answers "what is getting worse?"; Recommended Actions answers
 * "what should managers do next?". Every widget is either reused as-is
 * or derived purely from existing sample data — no chart library.
 */
export default function AnalyticsWorkspace() {
  const kpis = buildKpiSummary();
  const health = buildMaintenanceHealth();
  const attentionAssets = buildAttentionAssets();
  const criticalityDistribution = buildCriticalityDistribution();
  const activityTrend = buildActivityTrend();
  const recommendedActions = buildRecommendedActions();

  return (
    <div>
      <PageHeader title="Analytics" subtitle="LTSA Engineering — Manager Analytics" />

      <QuestionHeading>Are we healthy?</QuestionHeading>
      <KpiCardGrid kpis={kpis} />
      <MaintenanceHealthPanel health={health} />

      <QuestionHeading>What needs attention?</QuestionHeading>
      <CriticalityDistributionList distribution={criticalityDistribution} />
      <AttentionAssetList assets={attentionAssets} />

      <QuestionHeading>What is getting worse?</QuestionHeading>
      <ActivityTrendTable trend={activityTrend} />

      <QuestionHeading>What should managers do next?</QuestionHeading>
      <RecommendedActionsList actions={recommendedActions} />
    </div>
  );
}
