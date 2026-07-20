import { useMemo, useState } from "react";
import { EmptyState, PageHeader } from "../../../design-system";
import AssetSelector from "../components/AssetSelector";
import AssetSummaryCard from "../components/AssetSummaryCard";
import MaintenanceHistoryFilterBar from "../components/MaintenanceHistoryFilterBar";
import MaintenanceTimelineTable from "../components/MaintenanceTimelineTable";
import MaintenanceEventDetailPanel from "../components/MaintenanceEventDetailPanel";
import { buildAssetSummary, buildAssetTimeline, findAssetByTag, listAssets } from "../utils/maintenanceHistory";
import "./MaintenanceHistory.css";

const EMPTY_FILTERS = {
  dateFrom: "",
  dateTo: "",
  eventTypeFilter: "ALL",
  statusFilter: "ALL",
  technicianFilter: "ALL",
};

function matchesFilters(event, filters) {
  if (filters.eventTypeFilter !== "ALL" && event.type !== filters.eventTypeFilter) {
    return false;
  }

  if (filters.statusFilter !== "ALL" && event.status !== filters.statusFilter) {
    return false;
  }

  if (filters.technicianFilter !== "ALL" && event.assignedTechnician !== filters.technicianFilter) {
    return false;
  }

  if (filters.dateFrom || filters.dateTo) {
    if (!event.date) {
      return false;
    }

    if (filters.dateFrom && event.date < filters.dateFrom) {
      return false;
    }

    if (filters.dateTo && event.date > filters.dateTo) {
      return false;
    }
  }

  return true;
}

export default function MaintenanceHistory() {
  const assets = useMemo(() => listAssets(), []);
  const [selectedTag, setSelectedTag] = useState(null);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  function handleSelectAsset(tag) {
    setSelectedTag(tag);
    setSelectedEventId(null);
    setFilters(EMPTY_FILTERS);
  }

  function setFilter(name) {
    return (value) => setFilters((current) => ({ ...current, [name]: value }));
  }

  const selectedPump = selectedTag ? findAssetByTag(selectedTag) : null;
  const fullTimeline = useMemo(
    () => (selectedTag ? buildAssetTimeline(selectedTag) : []),
    [selectedTag]
  );
  const summary = useMemo(
    () => (selectedPump ? buildAssetSummary(selectedPump, fullTimeline) : null),
    [selectedPump, fullTimeline]
  );

  const statusOptions = useMemo(
    () => [...new Set(fullTimeline.map((event) => event.status))],
    [fullTimeline]
  );
  const technicianOptions = useMemo(
    () => [...new Set(fullTimeline.map((event) => event.assignedTechnician))],
    [fullTimeline]
  );

  const filteredTimeline = useMemo(
    () => fullTimeline.filter((event) => matchesFilters(event, filters)),
    [fullTimeline, filters]
  );

  const selectedEvent = filteredTimeline.find((event) => event.id === selectedEventId) ?? null;

  return (
    <div>
      <PageHeader title="Maintenance History" subtitle="LTSA Engineering — Asset 360 View" />

      <AssetSelector assets={assets} selectedTag={selectedTag} onSelect={handleSelectAsset} />

      {!selectedPump ? (
        <EmptyState
          title="No asset selected"
          description="Select a pump above to see everything that has ever happened to it."
        />
      ) : (
        <>
          <AssetSummaryCard summary={summary} />

          <MaintenanceHistoryFilterBar
            dateFrom={filters.dateFrom}
            onDateFromChange={setFilter("dateFrom")}
            dateTo={filters.dateTo}
            onDateToChange={setFilter("dateTo")}
            eventTypeFilter={filters.eventTypeFilter}
            onEventTypeFilterChange={setFilter("eventTypeFilter")}
            statusFilter={filters.statusFilter}
            onStatusFilterChange={setFilter("statusFilter")}
            statusOptions={statusOptions}
            technicianFilter={filters.technicianFilter}
            onTechnicianFilterChange={setFilter("technicianFilter")}
            technicianOptions={technicianOptions}
          />

          <div className="maintenance-history-layout">
            <div className="maintenance-history-timeline">
              <MaintenanceTimelineTable
                events={filteredTimeline}
                selectedId={selectedEventId}
                onSelect={setSelectedEventId}
              />
            </div>

            <div className="maintenance-history-detail">
              <MaintenanceEventDetailPanel event={selectedEvent} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
