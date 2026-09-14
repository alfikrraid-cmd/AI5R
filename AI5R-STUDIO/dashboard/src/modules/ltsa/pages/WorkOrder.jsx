import { useEffect, useMemo, useState } from "react";
import WorkOrderFilterBar from "../components/WorkOrderFilterBar";
import WorkOrderRegistryTable from "../components/WorkOrderRegistryTable";
import WorkOrderOpenDesignView from "../components/WorkOrderOpenDesignView";
import CreateWorkOrderModal from "../components/CreateWorkOrderModal";
import SuccessToast from "../components/SuccessToast";
import { KpiStrip } from "../components/open-design";
import {
  createWorkOrder, getWorkOrders, getWorkOrderTimeline, postEngineeringAI,
  getPMSchedules, getCMReports,
} from "../../../api/ai5rClient";
import {
  mapFormToCreatePayload,
  mapTimelineRecord,
  mapWorkOrderRecord,
  withResolvedArea,
} from "../utils/workOrderMapping";
import { mapPMScheduleRecord } from "../utils/pmMapping";
import { mapCMReportRecord } from "../utils/cmMapping";
import generateTraceId from "../utils/generateTraceId";
import { WORKSPACE_KEYS } from "../workspace/WorkspaceRegistry";
import "./WorkOrder.css";
import "./MaintenanceHistory.css";
import "./LTSAOpenDesign.css";

// UI-D2A -- "Overdue" is a real, truthfully-derived fact (dueDate in the
// past AND status not already COMPLETED/CANCELLED), not a fabricated
// value -- every input (dueDate, status) is a real already-mapped field
// (workOrderMapping.js). No new API call, no invented field.
function isOverdue(workOrder) {
  if (!workOrder.dueDate || workOrder.status === "COMPLETED" || workOrder.status === "CANCELLED") {
    return false;
  }
  const due = new Date(workOrder.dueDate);
  if (Number.isNaN(due.getTime())) {
    return false;
  }
  return due.getTime() < new Date().setHours(0, 0, 0, 0);
}

// Engineering AI: Work Order Workspace is the sixth and final Phase 1
// consumer of the canonical Engineering AI platform (Golden Reference:
// FailureAnalysisWorkspace.jsx; pattern already reused by Pump/PM/CM/
// Seal). Pure consumer -- builds an EngineeringAIRequest-shaped payload
// and calls postEngineeringAI() (HTTP transport only, ai5rClient.js).
// Never builds a prompt, never builds engineering context, never
// constructs an AI client, and never calls a Router or provider
// directly. Reuses the existing "summary" intent/prompt_type -- a Work
// Order is not exclusively PM-type ("pm_review") or CM-type
// ("cm_review"), so neither of those already-supported intents fits a
// generic work order; EngineeringContextEngine already exposes
// workorder_summary for exactly this case (same reasoning already
// applied to Pump and Seal). No new intent is invented.

function matchesSearch(workOrder, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    (workOrder.id || "").toLowerCase().includes(term) ||
    (workOrder.title || "").toLowerCase().includes(term) ||
    (workOrder.equipmentTag || "").toLowerCase().includes(term)
  );
}

function nextWorkOrderId(workOrders) {
  const maxNumber = workOrders.reduce((max, workOrder) => {
    const number = Number.parseInt((workOrder.id || "").replace("WO-", ""), 10);
    return Number.isNaN(number) ? max : Math.max(max, number);
  }, 1000);

  return `WO-${maxNumber + 1}`;
}

export default function WorkOrder({ navContext, onNavigate }) {
  const [workOrders, setWorkOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [areaFilter, setAreaFilter] = useState("ALL");
  const [selectedId, setSelectedId] = useState(null);
  const [mobileRegistryCollapsed, setMobileRegistryCollapsed] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);

  function refreshWorkOrders() {
    return getWorkOrders().then((records) =>
      Promise.all(records.map(mapWorkOrderRecord).map(withResolvedArea))
    );
  }

  useEffect(() => {
    let active = true;

    refreshWorkOrders()
      .then((resolved) => {
        if (active) {
          setWorkOrders(resolved);
          setListError(null);
        }
      })
      .catch(() => {
        if (active) {
          setListError("Work orders could not be loaded.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  // Deep-link entry point (APP-ASSET360-001, per ADR-ASSET360-001):
  // cross-domain links elsewhere (e.g. Asset 360's WO/MH/CM/PM detail
  // cards) navigate here with { selectId } to pre-select this work order.
  useEffect(() => {
    if (navContext?.selectId) {
      selectWorkOrder(navContext.selectId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navContext]);

  const statusOptions = useMemo(
    () => [...new Set(workOrders.map((workOrder) => workOrder.status))],
    [workOrders]
  );

  // UI-D2A -- Priority/Area filters, reusing the same already-real fields
  // (workOrder.priority/area) the table already displays; options are
  // derived from whatever is actually present in the loaded data, never a
  // hardcoded enum guess.
  const priorityOptions = useMemo(
    () => [...new Set(workOrders.map((workOrder) => workOrder.priority).filter(Boolean))],
    [workOrders]
  );

  const areaOptions = useMemo(
    () => [...new Set(workOrders.map((workOrder) => workOrder.area).filter(Boolean))],
    [workOrders]
  );

  const filteredWorkOrders = useMemo(
    () =>
      workOrders.filter(
        (workOrder) =>
          matchesSearch(workOrder, search) &&
          (statusFilter === "ALL" || workOrder.status === statusFilter) &&
          (priorityFilter === "ALL" || workOrder.priority === priorityFilter) &&
          (areaFilter === "ALL" || workOrder.area === areaFilter)
      ),
    [workOrders, search, statusFilter, priorityFilter, areaFilter]
  );

  // UI-D2A -- KPI strip: derived from the full (unfiltered) registry, the
  // same "at-a-glance fleet truth, independent of the current search/
  // filter view" convention Pump/Seal's own header health cards follow.
  // Every count is a real reduction over already-fetched records -- no
  // new fetch, no fabricated number.
  const kpiItems = useMemo(
    () => [
      { label: "Total WO", value: workOrders.length },
      { label: "Open", value: workOrders.filter((wo) => wo.status === "OPEN").length },
      { label: "In Progress", value: workOrders.filter((wo) => wo.status === "IN_PROGRESS").length },
      { label: "Completed", value: workOrders.filter((wo) => wo.status === "COMPLETED").length },
      { label: "Overdue", value: workOrders.filter(isOverdue).length, tone: "critical" },
    ],
    [workOrders]
  );

  function handleClearFilters() {
    setSearch("");
    setStatusFilter("ALL");
    setPriorityFilter("ALL");
    setAreaFilter("ALL");
  }

  const selectedWorkOrder =
    filteredWorkOrders.find((workOrder) => workOrder.id === selectedId) ?? null;

  const [aiResponse, setAiResponse] = useState(null), [aiLoading, setAiLoading] = useState(false), [aiError, setAiError] = useState(null);

  useEffect(() => {
    if (!selectedWorkOrder) { setAiResponse(null); setAiError(null); setAiLoading(false); return; }
    let active = true;
    setAiLoading(true); setAiError(null); setAiResponse(null);
    postEngineeringAI({
      asset_code: selectedWorkOrder.equipmentTag,
      intent: "summary",
      prompt_type: "summary",
      trace_id: generateTraceId(),
      selected_record_id: selectedWorkOrder.id,
      workspace: WORKSPACE_KEYS.WORK_ORDER,
    })
      .then((response) => { if (active) setAiResponse(response); })
      .catch((error) => { if (active) setAiError(error?.message || "Engineering AI request failed"); })
      .finally(() => active && setAiLoading(false));
    return () => { active = false; };
  }, [selectedWorkOrder?.id]);

  const aiBusinessError = aiResponse?.error ?? null;
  const aiReady = !aiLoading && !aiError && !!aiResponse && !aiBusinessError;
  const aiStatusText = aiLoading ? "Generating work order summary…" : (aiError || aiBusinessError || "Engineering AI has not run for this work order yet.");
  const aiStatusVariant = aiLoading ? "neutral" : (aiError || aiBusinessError) ? "critical" : aiReady ? (aiResponse.execution_status === "SUCCESS" ? "normal" : "attention") : "unavailable";
  const aiStatusLabel = aiLoading ? "Generating…" : (aiError || aiBusinessError) ? "Error" : aiReady ? aiResponse.execution_status : "Unavailable";

  // MWO-LTSA-055 -- Related Engineering (PM/CM), reusing getPMSchedules()/
  // getCMReports() and mapPMScheduleRecord/mapCMReportRecord exactly as
  // Seal.jsx/PM.jsx already do -- no new endpoint, no new mapping.
  // Filtered client-side by equipmentTag, the same field every one of
  // those mappers already derives from asset_code. Never throws -- a
  // failed fetch leaves the group empty (rendered as an honest "no data"
  // state by WorkOrderOpenDesignView), same "degrade, never fabricate"
  // discipline as the rest of this file.
  const [relatedPM, setRelatedPM] = useState([]);
  const [relatedCM, setRelatedCM] = useState([]);

  useEffect(() => {
    const equipmentTag = selectedWorkOrder?.equipmentTag;
    if (!equipmentTag) {
      setRelatedPM([]); setRelatedCM([]);
      return undefined;
    }
    let active = true;
    Promise.all([
      getPMSchedules().catch(() => []),
      getCMReports().catch(() => []),
    ]).then(([pm, cm]) => {
      if (!active) return;
      setRelatedPM(pm.map(mapPMScheduleRecord).filter((item) => item.equipmentTag === equipmentTag));
      setRelatedCM(cm.map(mapCMReportRecord).filter((item) => item.equipmentTag === equipmentTag));
    });
    return () => { active = false; };
  }, [selectedWorkOrder?.equipmentTag]);

  // Related Work Orders: derived from the work order list already loaded
  // in this component's own state -- no new fetch, unlike Related PM/CM
  // above (WorkOrder.jsx uniquely already holds the full sibling list,
  // unlike Seal.jsx/PM.jsx which fetch getWorkOrders() separately).
  const relatedWorkOrders = useMemo(() => {
    const equipmentTag = selectedWorkOrder?.equipmentTag;
    if (!equipmentTag) return [];
    return workOrders.filter(
      (workOrder) => workOrder.equipmentTag === equipmentTag && workOrder.id !== selectedWorkOrder.id
    );
  }, [workOrders, selectedWorkOrder]);

  // MWO-LTSA-055 -- Open Pump / Open Drawing reuse the exact same
  // onNavigate(key, context) mechanism Pump.jsx/Seal.jsx/DocumentWorkspace.jsx
  // already use for their own cross-workspace links. No new navigation
  // pattern, no new route -- the same "pump"/"drawing" tab keys
  // LTSAWorkspace.jsx already registers. Preserves the Pump -> Seal ->
  // Drawing -> Document -> PM -> CM -> Work Order navigation chain this
  // MWO's own Navigation section requires.
  function handleOpenPump(equipmentTag) {
    onNavigate?.("pump", { selectId: equipmentTag });
  }

  function handleOpenDrawing(equipmentTag) {
    onNavigate?.("drawing", { assetTag: equipmentTag });
  }

  function selectWorkOrder(id) {
    setSelectedId(id);
    // UI-D2A.1 -- auto-collapse the mobile registry once a work order is
    // selected (CSS-gated to the mobile breakpoint only, WorkOrder.css;
    // no effect on desktop, which always shows the full dense table).
    setMobileRegistryCollapsed(true);

    getWorkOrderTimeline(id)
      .then((records) => {
        const timeline = records.map(mapTimelineRecord);

        setWorkOrders((current) =>
          current.map((workOrder) =>
            workOrder.id === id ? { ...workOrder, timeline } : workOrder
          )
        );
      })
      .catch(() => {
        // Timeline is supplementary to the Detail Panel -- leave the work
        // order's existing (empty) timeline as-is rather than blocking or
        // erroring the rest of the detail view on a timeline-only failure.
      });
  }

  function handleCreate(formValues) {
    const workOrderCode = nextWorkOrderId(workOrders);

    // CreateWorkOrderModal (frozen, per APP-008) clears its own form and
    // closes the moment onCreate is called, regardless of what happens
    // next -- it never awaits this. Closing here matches that existing
    // behavior; a create failure is reported via createError below rather
    // than by reopening the modal (whose form contents are already gone).
    setIsCreateModalOpen(false);
    setCreating(true);
    setCreateError(null);

    createWorkOrder(mapFormToCreatePayload(formValues, workOrderCode))
      .then(() => refreshWorkOrders())
      .then((resolved) => {
        setWorkOrders(resolved);
        setSelectedId(workOrderCode);
        setSuccessMessage(`Work Order ${workOrderCode} created.`);
      })
      .catch(() => {
        setCreateError("Work order could not be created.");
      })
      .finally(() => {
        setCreating(false);
      });
  }

  return (
    <div className="ltsa-open-design">
      <div className="workorder-page-header">
        <div>
          <h1 className="workorder-page-title">WORK ORDERS</h1>
          <p className="workorder-page-subtitle">Operational maintenance work-order workspace</p>
        </div>
        <button type="button" className="workorder-create-btn" onClick={() => setIsCreateModalOpen(true)}>
          + Create Work Order
        </button>
      </div>

      {!loading && !listError && <KpiStrip items={kpiItems} />}

      <div style={{ maxWidth: 1240, margin: "0 auto", padding: "0 32px" }}>
        <SuccessToast message={successMessage} onDismiss={() => setSuccessMessage(null)} />
      </div>

      {creating ? <p className="workorder-status-panel">Creating work order...</p> : null}

      {createError ? (
        <p className="workorder-status-panel" role="alert">{createError}</p>
      ) : null}

      <WorkOrderFilterBar
        searchValue={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statusOptions={statusOptions}
        priorityFilter={priorityFilter}
        onPriorityFilterChange={setPriorityFilter}
        priorityOptions={priorityOptions}
        areaFilter={areaFilter}
        onAreaFilterChange={setAreaFilter}
        areaOptions={areaOptions}
        onClear={handleClearFilters}
      />

      {loading ? (
        <p className="workorder-status-panel">Loading work orders...</p>
      ) : listError ? (
        <p className="workorder-status-panel" role="alert">{listError}</p>
      ) : (
        <div className="workorder-workspace-layout">
          <div className="workorder-workspace-registry">
            <WorkOrderRegistryTable
              workOrders={filteredWorkOrders}
              selectedId={selectedId}
              onSelect={selectWorkOrder}
              mobileCollapsed={mobileRegistryCollapsed}
              onExpand={() => setMobileRegistryCollapsed(false)}
            />
          </div>

          <div className="workorder-workspace-detail">
            {selectedWorkOrder ? (
              <>
                <p className="workorder-selected-label">Selected Work Order</p>
                <WorkOrderOpenDesignView
                workOrder={selectedWorkOrder}
                relatedPMRecords={relatedPM}
                cmRecords={relatedCM}
                relatedWorkOrders={relatedWorkOrders}
                onOpenPump={handleOpenPump}
                onOpenDrawing={handleOpenDrawing}
                onOpenPMWorkspace={() => onNavigate?.("pm-workspace", { workOrderId: selectedWorkOrder.id })}
                onBack={() => onNavigate?.("dashboard")}
                aiResponse={aiResponse}
                aiReady={aiReady}
                aiStatusText={aiStatusText}
                  aiStatusVariant={aiStatusVariant}
                  aiStatusLabel={aiStatusLabel}
                />
              </>
            ) : (
              <div className="workorder-empty-state">
                <p className="workorder-empty-title">No work order selected</p>
                <p className="workorder-empty-description">Select a work order from the work order list to view its details.</p>
              </div>
            )}
          </div>
        </div>
      )}

      <CreateWorkOrderModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreate}
      />
    </div>
  );
}
