import { useMemo, useState } from "react";
import { Button, PageHeader } from "../../../design-system";
import WorkOrderFilterBar from "../components/WorkOrderFilterBar";
import WorkOrderRegistryTable from "../components/WorkOrderRegistryTable";
import WorkOrderDetailPanel from "../components/WorkOrderDetailPanel";
import CreateWorkOrderModal from "../components/CreateWorkOrderModal";
import SuccessToast from "../components/SuccessToast";
import sampleWorkOrders from "../data/sampleWorkOrders";
import "./WorkOrder.css";

function matchesSearch(workOrder, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    workOrder.id.toLowerCase().includes(term) ||
    workOrder.title.toLowerCase().includes(term) ||
    workOrder.equipmentTag.toLowerCase().includes(term)
  );
}

function nextWorkOrderId(workOrders) {
  const maxNumber = workOrders.reduce((max, workOrder) => {
    const number = Number.parseInt(workOrder.id.replace("WO-", ""), 10);
    return Number.isNaN(number) ? max : Math.max(max, number);
  }, 1000);

  return `WO-${maxNumber + 1}`;
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

export default function WorkOrder() {
  const [workOrders, setWorkOrders] = useState(sampleWorkOrders);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedId, setSelectedId] = useState(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);

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

  function handleCreate(formValues) {
    const createdDate = todayIsoDate();

    const newWorkOrder = {
      ...formValues,
      id: nextWorkOrderId(workOrders),
      status: "OPEN",
      createdDate,
      timeline: [{ date: createdDate, event: "Work order created" }],
    };

    setWorkOrders((current) => [...current, newWorkOrder]);
    setIsCreateModalOpen(false);
    setSelectedId(newWorkOrder.id);
    setSuccessMessage(`Work Order ${newWorkOrder.id} created.`);
  }

  return (
    <div>
      <PageHeader
        title="Work Order Workspace"
        subtitle="LTSA Engineering — Work Order Registry"
        actions={<Button onClick={() => setIsCreateModalOpen(true)}>+ Create Work Order</Button>}
      />

      <SuccessToast message={successMessage} onDismiss={() => setSuccessMessage(null)} />

      <WorkOrderFilterBar
        searchValue={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statusOptions={statusOptions}
      />

      <div className="workorder-workspace-layout">
        <div className="workorder-workspace-registry">
          <WorkOrderRegistryTable
            workOrders={filteredWorkOrders}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>

        <div className="workorder-workspace-detail">
          <WorkOrderDetailPanel workOrder={selectedWorkOrder} />
        </div>
      </div>

      <CreateWorkOrderModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreate}
      />
    </div>
  );
}
