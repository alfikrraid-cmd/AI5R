import { useMemo, useState } from "react";
import { Button, PageHeader } from "../../../design-system";
import CMFilterBar from "../components/CMFilterBar";
import CMReportTable from "../components/CMReportTable";
import CMDetailPanel from "../components/CMDetailPanel";
import CreateCMReportModal from "../components/CreateCMReportModal";
import SuccessToast from "../components/SuccessToast";
import sampleCMReports from "../data/sampleCMReports";
import "./CM.css";

function matchesSearch(cm, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    cm.id.toLowerCase().includes(term) ||
    cm.failureDescription.toLowerCase().includes(term) ||
    cm.equipmentTag.toLowerCase().includes(term)
  );
}

function nextCMId(cmReports) {
  const maxNumber = cmReports.reduce((max, cm) => {
    const number = Number.parseInt(cm.id.replace("CM-", ""), 10);
    return Number.isNaN(number) ? max : Math.max(max, number);
  }, 3000);

  return `CM-${maxNumber + 1}`;
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

export default function CM() {
  const [cmReports, setCmReports] = useState(sampleCMReports);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedId, setSelectedId] = useState(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);

  const statusOptions = useMemo(
    () => [...new Set(cmReports.map((cm) => cm.status))],
    [cmReports]
  );

  const filteredCMReports = useMemo(
    () =>
      cmReports.filter(
        (cm) => matchesSearch(cm, search) && (statusFilter === "ALL" || cm.status === statusFilter)
      ),
    [cmReports, search, statusFilter]
  );

  const selectedCM = filteredCMReports.find((cm) => cm.id === selectedId) ?? null;

  function handleCreate(formValues) {
    const createdDate = todayIsoDate();

    const newCM = {
      id: nextCMId(cmReports),
      equipmentTag: formValues.equipmentTag,
      failureCategory: formValues.failureCategory,
      severity: formValues.severity,
      priority: formValues.priority,
      failureDescription: formValues.failureDescription,
      rootCause: "Pending investigation.",
      immediateAction: formValues.immediateAction,
      correctiveAction: "Not yet determined.",
      downtimeHours: 0,
      assignedTechnician: formValues.assignedTechnician,
      relatedPump: formValues.equipmentTag,
      relatedWorkOrder: null,
      status: "OPEN",
      timeline: [{ date: createdDate, event: "Corrective maintenance report created" }],
    };

    setCmReports((current) => [...current, newCM]);
    setIsCreateModalOpen(false);
    setSelectedId(newCM.id);
    setSuccessMessage(`Corrective Maintenance Report ${newCM.id} created.`);
  }

  return (
    <div>
      <PageHeader
        title="Corrective Maintenance Workspace"
        subtitle="LTSA Engineering — Corrective Maintenance Registry"
        actions={<Button onClick={() => setIsCreateModalOpen(true)}>+ Create CM Report</Button>}
      />

      <SuccessToast message={successMessage} onDismiss={() => setSuccessMessage(null)} />

      <CMFilterBar
        searchValue={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statusOptions={statusOptions}
      />

      <div className="cm-workspace-layout">
        <div className="cm-workspace-registry">
          <CMReportTable cmReports={filteredCMReports} selectedId={selectedId} onSelect={setSelectedId} />
        </div>

        <div className="cm-workspace-detail">
          <CMDetailPanel cm={selectedCM} />
        </div>
      </div>

      <CreateCMReportModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreate}
      />
    </div>
  );
}
