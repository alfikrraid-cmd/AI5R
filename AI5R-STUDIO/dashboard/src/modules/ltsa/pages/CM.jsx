import { useEffect, useMemo, useState } from "react";
import { Button, EmptyState, PageHeader, Panel } from "../../../design-system";
import CMFilterBar from "../components/CMFilterBar";
import CMReportTable from "../components/CMReportTable";
import CMOpenDesignView from "../components/CMOpenDesignView";
import CreateCMReportModal from "../components/CreateCMReportModal";
import SuccessToast from "../components/SuccessToast";
import { getCMReports, getPMSchedules } from "../../../api/ai5rClient";
import { mapCMReportRecord, withResolvedArea } from "../utils/cmMapping";
import { mapPMScheduleRecord } from "../utils/pmMapping";
import "./CM.css";
import "./LTSAOpenDesign.css";

function matchesSearch(cm, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    (cm.id || "").toLowerCase().includes(term) ||
    (cm.failureDescription || "").toLowerCase().includes(term) ||
    (cm.equipmentTag || "").toLowerCase().includes(term)
  );
}

function nextCMId(cmReports) {
  const maxNumber = cmReports.reduce((max, cm) => {
    const number = Number.parseInt((cm.id || "").replace("CM-", ""), 10);
    return Number.isNaN(number) ? max : Math.max(max, number);
  }, 3000);

  return `CM-${maxNumber + 1}`;
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

export default function CM({ onNavigate, navContext }) {
  const [cmReports, setCmReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedId, setSelectedId] = useState(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);
  // MWO-LTSA-054 -- Related PM, resolved the same "fetch once, derive many
  // client-side" way Pump.jsx/PM.jsx already resolve their own Related
  // Engineering groups (getPMSchedules is the same already-wired endpoint,
  // nothing new).
  const [pmSchedules, setPmSchedules] = useState([]);

  useEffect(() => {
    let active = true;

    getCMReports()
      .then((records) => Promise.all(records.map(mapCMReportRecord).map(withResolvedArea)))
      .then((resolved) => {
        if (active) {
          setCmReports(resolved);
          setListError(null);
        }
      })
      .catch(() => {
        if (active) {
          setListError("CM reports could not be loaded.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    getPMSchedules()
      .then((records) => { if (active) setPmSchedules(records.map(mapPMScheduleRecord)); })
      .catch(() => { if (active) setPmSchedules([]); });

    return () => {
      active = false;
    };
  }, []);

  // Deep-link entry point (APP-ASSET360-001, per ADR-ASSET360-001):
  // cross-domain links elsewhere (e.g. Asset 360's CM detail card)
  // navigate here with { selectId } to pre-select this report.
  //
  // MWO-LTSA-054 -- { assetTag } added: DrawingNavigationPanel.jsx already
  // sends onNavigate("cm", { assetTag }) (the "Preserve navigation chain"
  // requirement), but this effect previously only ever reacted to
  // { selectId }, silently dropping that context -- the same gap
  // MWO-LTSA-053 fixed for PM.jsx. Gated on the CM list being loaded,
  // mirroring PM.jsx's own precedent.
  useEffect(() => {
    if (navContext?.selectId) {
      setSelectedId(navContext.selectId);
    } else if (navContext?.assetTag && !loading) {
      const match = cmReports.find((cm) => cm.equipmentTag === navContext.assetTag);
      if (match) {
        setSelectedId(match.id);
      }
    }
  }, [navContext, loading, cmReports]);

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

  // MWO-LTSA-054 -- Related PM: PM schedules sharing this report's
  // equipmentTag, derived from the already-fetched pmSchedules list -- no
  // new fetch beyond the one getPMSchedules() call above.
  const relatedPMRecords = selectedCM
    ? pmSchedules.filter((pm) => pm.equipmentTag === selectedCM.equipmentTag)
    : [];

  // Related CM Reports: sibling reports sharing this one's equipmentTag,
  // excluding itself -- same "filter the already-loaded list" pattern PM's
  // own Related PM derivation uses.
  const relatedCMRecords = selectedCM
    ? cmReports.filter((cm) => cm.id !== selectedCM.id && cm.equipmentTag === selectedCM.equipmentTag)
    : [];

  // MWO-LTSA-054 -- Open Pump / Open Drawing reuse the exact same
  // onNavigate(key, context) mechanism Seal.jsx/Pump.jsx/PM.jsx already
  // use for cross-workspace navigation. equipmentTag is already the real
  // asset tag directly (cmMapping.js: equipmentTag <- asset_code), no
  // resolution layer needed.
  function handleOpenPump(equipmentTag) {
    onNavigate?.("pump", { selectId: equipmentTag });
  }
  function handleOpenDrawing() {
    onNavigate?.("drawing", { assetTag: selectedCM?.equipmentTag });
  }

  // Backend create/update routes for cm_report were not built by
  // WO-CM-001/WO-CM-002 (list/detail only) -- handleCreate remains
  // client-state-only, the same as it was before this migration and the
  // same as PM Schedule's own handleCreate under APP-PM-001.
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

      {loading ? (
        <Panel>
          <p>Loading CM reports...</p>
        </Panel>
      ) : listError ? (
        <Panel>
          <p role="alert">{listError}</p>
        </Panel>
      ) : (
        <div className="cm-workspace-layout">
          <div className="cm-workspace-registry">
            <CMReportTable cmReports={filteredCMReports} selectedId={selectedId} onSelect={setSelectedId} />
          </div>

          <div className="cm-workspace-detail">
            {selectedCM ? (
              <CMOpenDesignView
                cm={selectedCM}
                relatedPMRecords={relatedPMRecords}
                relatedCMRecords={relatedCMRecords}
                onOpenPump={handleOpenPump}
                onOpenDrawing={handleOpenDrawing}
                onCreateCM={() => setIsCreateModalOpen(true)}
              />
            ) : (
              <EmptyState
                title="No corrective maintenance report selected"
                description="Select a report from the list to view its details."
              />
            )}
          </div>
        </div>
      )}

      <CreateCMReportModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreate}
      />
    </div>
  );
}
