import { useEffect, useMemo, useState } from "react";
import { EmptyState, PageHeader, Panel } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import KpiCardGrid from "../components/KpiCardGrid";
import MaintenanceHealthPanel from "../components/MaintenanceHealthPanel";
import AttentionAssetList from "../components/AttentionAssetList";
import CriticalityDistributionList from "../components/CriticalityDistributionList";
import ActivityTrendTable from "../components/ActivityTrendTable";
import RecommendedActionsList from "../components/RecommendedActionsList";
import {
  getCMReports,
  getConditionMonitoringReadings,
  getMaintenanceHistory,
  getPMOccurrences,
  getPMSchedules,
  getPumps,
  getWorkOrders,
} from "../../../api/ai5rClient";
import { mapPMScheduleRecord } from "../utils/pmMapping";
import { mapPumpRecord } from "../utils/pumpMapping";
import { mapWorkOrderRecord } from "../utils/workOrderMapping";
import { buildAttentionAssets, buildKpiSummary, buildMaintenanceHealth } from "../utils/executiveDashboard";
import { buildActivityTrend, buildCriticalityDistribution, buildRecommendedActions } from "../utils/analytics";

const EMPTY_ANALYTICS_SOURCE = {
  pumps: [],
  workOrders: [],
  pmSchedules: [],
  cmReports: [],
  maintenanceHistory: [],
  pmOccurrences: [],
  conditionMonitoringReadings: [],
};

function QuestionHeading({ children }) {
  return (
    <h2 style={{ color: colors.text, marginTop: spacing.lg, marginBottom: spacing.sm }}>{children}</h2>
  );
}

function hasAnyData(source) {
  return Object.values(source).some((items) => Array.isArray(items) && items.length > 0);
}

export default function AnalyticsWorkspace() {
  const [sourceData, setSourceData] = useState(EMPTY_ANALYTICS_SOURCE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;

    Promise.all([
      getPumps(),
      getWorkOrders(),
      getPMSchedules(),
      getCMReports(),
      getMaintenanceHistory(),
      getPMOccurrences(),
      getConditionMonitoringReadings(),
    ])
      .then(([pumpRecords, workOrderRecords, pmScheduleRecords, cmReportRecords, maintenanceRecords, pmOccurrenceRecords, readingRecords]) => {
        if (!active) return;

        setSourceData({
          pumps: pumpRecords.map(mapPumpRecord),
          workOrders: workOrderRecords.map(mapWorkOrderRecord),
          pmSchedules: pmScheduleRecords.map(mapPMScheduleRecord),
          cmReports: cmReportRecords,
          maintenanceHistory: maintenanceRecords,
          pmOccurrences: pmOccurrenceRecords,
          conditionMonitoringReadings: readingRecords,
        });
        setError(null);
      })
      .catch(() => {
        if (active) {
          setSourceData(EMPTY_ANALYTICS_SOURCE);
          setError("Analytics data could not be loaded.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const kpis = useMemo(() => buildKpiSummary(sourceData), [sourceData]);
  const health = useMemo(() => buildMaintenanceHealth(sourceData), [sourceData]);
  const attentionAssets = useMemo(() => buildAttentionAssets(sourceData), [sourceData]);
  const criticalityDistribution = useMemo(() => buildCriticalityDistribution(sourceData), [sourceData]);
  const activityTrend = useMemo(() => buildActivityTrend(sourceData), [sourceData]);
  const recommendedActions = useMemo(() => buildRecommendedActions(sourceData), [sourceData]);

  return (
    <div>
      <PageHeader title="Analytics" subtitle="LTSA Engineering - Manager Analytics" />

      {loading ? (
        <Panel>
          <p>Loading analytics...</p>
        </Panel>
      ) : error ? (
        <Panel>
          <p role="alert">{error}</p>
        </Panel>
      ) : !hasAnyData(sourceData) ? (
        <EmptyState
          title="No analytics data available"
          description="No LTSA production records are currently available for analytics."
        />
      ) : (
        <>
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
        </>
      )}
    </div>
  );
}
