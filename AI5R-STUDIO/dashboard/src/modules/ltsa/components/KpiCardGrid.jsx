import { MetricCard } from "../../../design-system";

export default function KpiCardGrid({ kpis }) {
  const cards = [
    { title: "Open Work Orders", value: kpis.openWorkOrders },
    { title: "Overdue PM", value: kpis.overduePM },
    { title: "Upcoming PM", value: kpis.upcomingPM },
    { title: "Open Corrective Maintenance", value: kpis.openCorrectiveMaintenance },
    { title: "Critical Assets", value: kpis.criticalAssets },
    { title: "Recent Maintenance Activity", value: kpis.recentMaintenanceActivity },
  ];

  return (
    <div className="executive-dashboard-kpi-grid">
      {cards.map((card) => (
        <MetricCard key={card.title} title={card.title} value={card.value} />
      ))}
    </div>
  );
}
