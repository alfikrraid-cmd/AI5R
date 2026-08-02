import { useEffect, useMemo, useState } from "react";
import { Button, PageHeader, Panel } from "../../../design-system";
import WorkOrderFilterBar from "../components/WorkOrderFilterBar";
import WorkOrderRegistryTable from "../components/WorkOrderRegistryTable";
import WorkOrderDetailPanel from "../components/WorkOrderDetailPanel";
import CreateWorkOrderModal from "../components/CreateWorkOrderModal";
import SuccessToast from "../components/SuccessToast";
import { createWorkOrder, getWorkOrders, getWorkOrderTimeline } from "../../../api/ai5rClient";
import {
  mapFormToCreatePayload,
  mapTimelineRecord,
  mapWorkOrderRecord,
  withResolvedArea,
} from "../utils/workOrderMapping";
import "./WorkOrder.css";

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
  const [selectedId, setSelectedId] = useState(null);
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

  const filteredWorkOrders = useMemo(
    () =>
      workOrders.filter(
        (workOrder) =>
          matchesSearch(workOrder, search) &&
          (statusFilter === "ALL" || workOrder.status === statusFilter)
      ),
    [workOrders, search, statusFilter]
  );

  const selectedWorkOrder =
    filteredWorkOrders.find((workOrder) => workOrder.id === selectedId) ?? null;

  function selectWorkOrder(id) {
    setSelectedId(id);

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
    <div>
      <PageHeader
        title="Work Order Workspace"
        subtitle="LTSA Engineering — Work Order Registry"
        actions={<Button onClick={() => setIsCreateModalOpen(true)}>+ Create Work Order</Button>}
      />

      <SuccessToast message={successMessage} onDismiss={() => setSuccessMessage(null)} />

      {creating ? (
        <Panel>
          <p>Creating work order...</p>
        </Panel>
      ) : null}

      {createError ? (
        <Panel>
          <p role="alert">{createError}</p>
        </Panel>
      ) : null}

      <WorkOrderFilterBar
        searchValue={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statusOptions={statusOptions}
      />

      {loading ? (
        <Panel>
          <p>Loading work orders...</p>
        </Panel>
      ) : listError ? (
        <Panel>
          <p role="alert">{listError}</p>
        </Panel>
      ) : (
        <div className="workorder-workspace-layout">
          <div className="workorder-workspace-registry">
            <WorkOrderRegistryTable
              workOrders={filteredWorkOrders}
              selectedId={selectedId}
              onSelect={selectWorkOrder}
            />
          </div>

          <div className="workorder-workspace-detail">
            <WorkOrderDetailPanel
              workOrder={selectedWorkOrder}
              onOpenPMWorkspace={
                selectedWorkOrder
                  ? () => onNavigate?.("pm-workspace", { workOrderId: selectedWorkOrder.id })
                  : undefined
              }
            />
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
