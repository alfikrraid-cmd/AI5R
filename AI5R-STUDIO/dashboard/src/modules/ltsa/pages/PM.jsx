import { useMemo, useState } from "react";
import { Button, PageHeader } from "../../../design-system";
import PMFilterBar from "../components/PMFilterBar";
import PMScheduleTable from "../components/PMScheduleTable";
import PMDetailPanel from "../components/PMDetailPanel";
import CreatePMScheduleModal from "../components/CreatePMScheduleModal";
import SuccessToast from "../components/SuccessToast";
import samplePMSchedules from "../data/samplePMSchedules";
import "./PM.css";

function matchesSearch(pm, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    pm.id.toLowerCase().includes(term) ||
    pm.procedure.toLowerCase().includes(term) ||
    pm.equipmentTag.toLowerCase().includes(term)
  );
}

function nextPMId(pmSchedules) {
  const maxNumber = pmSchedules.reduce((max, pm) => {
    const number = Number.parseInt(pm.id.replace("PM-", ""), 10);
    return Number.isNaN(number) ? max : Math.max(max, number);
  }, 2000);

  return `PM-${maxNumber + 1}`;
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function procedureFromChecklistTemplate(checklistTemplate) {
  return checklistTemplate.replace(/ Checklist$/, "");
}

export default function PM() {
  const [pmSchedules, setPmSchedules] = useState(samplePMSchedules);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedId, setSelectedId] = useState(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);

  const statusOptions = useMemo(
    () => [...new Set(pmSchedules.map((pm) => pm.status))],
    [pmSchedules]
  );

  const filteredPMSchedules = useMemo(
    () =>
      pmSchedules.filter(
        (pm) => matchesSearch(pm, search) && (statusFilter === "ALL" || pm.status === statusFilter)
      ),
    [pmSchedules, search, statusFilter]
  );

  const selectedPM = filteredPMSchedules.find((pm) => pm.id === selectedId) ?? null;

  function handleCreate(formValues) {
    const createdDate = todayIsoDate();

    const newPM = {
      id: nextPMId(pmSchedules),
      equipmentTag: formValues.equipmentTag,
      procedure: procedureFromChecklistTemplate(formValues.checklistTemplate),
      frequency: formValues.frequency,
      triggerType: formValues.triggerType,
      checklist: formValues.checklist,
      lastPerformed: null,
      nextDue: formValues.startDate || createdDate,
      assignedTechnician: formValues.assignedTechnician,
      estimatedDurationHours: formValues.estimatedDurationHours,
      relatedWorkOrders: [],
      status: "ACTIVE",
      timeline: [{ date: createdDate, event: "PM schedule created" }],
    };

    setPmSchedules((current) => [...current, newPM]);
    setIsCreateModalOpen(false);
    setSelectedId(newPM.id);
    setSuccessMessage(`PM Schedule ${newPM.id} created.`);
  }

  return (
    <div>
      <PageHeader
        title="Preventive Maintenance Workspace"
        subtitle="LTSA Engineering — PM Schedule Registry"
        actions={<Button onClick={() => setIsCreateModalOpen(true)}>+ Create PM Schedule</Button>}
      />

      <SuccessToast message={successMessage} onDismiss={() => setSuccessMessage(null)} />

      <PMFilterBar
        searchValue={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statusOptions={statusOptions}
      />

      <div className="pm-workspace-layout">
        <div className="pm-workspace-registry">
          <PMScheduleTable
            pmSchedules={filteredPMSchedules}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>

        <div className="pm-workspace-detail">
          <PMDetailPanel pm={selectedPM} />
        </div>
      </div>

      <CreatePMScheduleModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreate}
      />
    </div>
  );
}
