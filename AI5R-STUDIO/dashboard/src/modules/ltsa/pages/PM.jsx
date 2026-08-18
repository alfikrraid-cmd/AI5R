import { useEffect, useMemo, useState } from "react";
import { Button, EmptyState, PageHeader, Panel } from "../../../design-system";
import PMFilterBar from "../components/PMFilterBar";
import PMScheduleTable from "../components/PMScheduleTable";
import PMOpenDesignView from "../components/PMOpenDesignView";
import CreatePMScheduleModal from "../components/CreatePMScheduleModal";
import SuccessToast from "../components/SuccessToast";
import { getPMSchedules, getCMReports } from "../../../api/ai5rClient";
import { mapPMScheduleRecord, withResolvedArea } from "../utils/pmMapping";
import { mapCMReportRecord } from "../utils/cmMapping";
import "./PM.css";
import "./LTSAOpenDesign.css";

function matchesSearch(pm, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    (pm.id || "").toLowerCase().includes(term) ||
    (pm.procedure || "").toLowerCase().includes(term) ||
    (pm.equipmentTag || "").toLowerCase().includes(term)
  );
}

function nextPMId(pmSchedules) {
  const maxNumber = pmSchedules.reduce((max, pm) => {
    const number = Number.parseInt((pm.id || "").replace("PM-", ""), 10);
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

export default function PM({ onNavigate, navContext }) {
  const [pmSchedules, setPmSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedId, setSelectedId] = useState(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);
  // MWO-LTSA-053 -- Related CM Reports, resolved the same "fetch once,
  // derive many client-side" way Pump.jsx/Seal.jsx already resolve their
  // own Related Engineering groups (getCMReports is the same already-wired
  // endpoint, nothing new).
  const [cmReports, setCmReports] = useState([]);

  useEffect(() => {
    let active = true;

    getPMSchedules()
      .then((records) => Promise.all(records.map(mapPMScheduleRecord).map(withResolvedArea)))
      .then((resolved) => {
        if (active) {
          setPmSchedules(resolved);
          setListError(null);
        }
      })
      .catch(() => {
        if (active) {
          setListError("PM schedules could not be loaded.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    getCMReports()
      .then((records) => { if (active) setCmReports(records.map(mapCMReportRecord)); })
      .catch(() => { if (active) setCmReports([]); });

    return () => {
      active = false;
    };
  }, []);

  // Deep-link entry point (APP-ASSET360-001, per ADR-ASSET360-001):
  // cross-domain links elsewhere (e.g. Asset 360's PM Occurrence detail
  // card) navigate here with { selectId } to pre-select this schedule.
  //
  // MWO-LTSA-053 -- { assetTag } added: DrawingNavigationPanel.jsx/
  // DocumentNavigationPanel.jsx already send onNavigate("pm", { assetTag })
  // (the "Preserve navigation chain" requirement), but this effect
  // previously only ever reacted to { selectId }, silently dropping that
  // context. Gated on the PM list being loaded (mirrors Pump.jsx's own
  // navContext.selectId-while-!loading precedent) since resolving an
  // assetTag requires pmSchedules to already be populated.
  useEffect(() => {
    if (navContext?.selectId) {
      setSelectedId(navContext.selectId);
    } else if (navContext?.assetTag && !loading) {
      const match = pmSchedules.find((pm) => pm.equipmentTag === navContext.assetTag);
      if (match) {
        setSelectedId(match.id);
      }
    }
  }, [navContext, loading, pmSchedules]);

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

  // MWO-LTSA-053 -- Related PM: other schedules sharing this one's
  // equipmentTag, excluding itself. Derived from the already-fetched
  // pmSchedules list -- no new fetch, mirrors relatedGroups' own
  // "filter the already-loaded list" pattern in PumpOpenDesignView.jsx.
  const relatedPMRecords = selectedPM
    ? pmSchedules.filter((pm) => pm.id !== selectedPM.id && pm.equipmentTag === selectedPM.equipmentTag)
    : [];

  const relatedCMRecords = selectedPM
    ? cmReports.filter((cm) => cm.equipmentTag === selectedPM.equipmentTag)
    : [];

  // MWO-LTSA-053 -- Open Pump / Open Drawing reuse the exact same
  // onNavigate(key, context) mechanism Seal.jsx/Pump.jsx already use for
  // cross-workspace navigation. equipmentTag is already the real asset
  // tag directly (pmMapping.js: equipmentTag <- asset_code), no
  // resolution layer needed.
  function handleOpenPump(equipmentTag) {
    onNavigate?.("pump", { selectId: equipmentTag });
  }
  function handleOpenDrawing() {
    onNavigate?.("drawing", { assetTag: selectedPM?.equipmentTag });
  }

  // Backend create/update routes for pm_schedule were not built by
  // WO-PM-001/WO-PM-002 (list/detail only) -- handleCreate remains
  // client-state-only, the same as it was before this migration and the
  // same as Pump's own Create PM/Create CM stubs.
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

      {loading ? (
        <Panel>
          <p>Loading PM schedules...</p>
        </Panel>
      ) : listError ? (
        <Panel>
          <p role="alert">{listError}</p>
        </Panel>
      ) : (
        <div className="pm-workspace-layout">
          <div className="pm-workspace-registry">
            <PMScheduleTable
              pmSchedules={filteredPMSchedules}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>

          <div className="pm-workspace-detail">
            {selectedPM ? (
              <PMOpenDesignView
                pm={selectedPM}
                relatedPMRecords={relatedPMRecords}
                cmRecords={relatedCMRecords}
                onOpenPump={handleOpenPump}
                onOpenDrawing={handleOpenDrawing}
                onCreatePM={() => setIsCreateModalOpen(true)}
              />
            ) : (
              <EmptyState
                title="No PM schedule selected"
                description="Select a PM schedule from the list to view its details."
              />
            )}
          </div>
        </div>
      )}

      <CreatePMScheduleModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreate}
      />
    </div>
  );
}
