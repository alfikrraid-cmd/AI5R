import { useEffect, useMemo, useState } from "react";
import { Button, EmptyState, PageHeader, Panel } from "../../../design-system";
import PMFilterBar from "../components/PMFilterBar";
import PMScheduleTable from "../components/PMScheduleTable";
import PMOpenDesignView from "../components/PMOpenDesignView";
import PMOccurrenceDetailPanel from "../components/PMOccurrenceDetailPanel";
import CreatePMScheduleModal from "../components/CreatePMScheduleModal";
import EditPMScheduleModal from "../components/EditPMScheduleModal";
import CreatePMOccurrenceModal from "../components/CreatePMOccurrenceModal";
import SuccessToast from "../components/SuccessToast";
import {
  getPMSchedules, getCMReports, getPMOccurrences, createPMOccurrence,
  createPMSchedule,
  updatePMSchedule,
  updatePMOccurrenceDraft, submitPMOccurrence, adminReviewPMOccurrence, technicalReviewPMOccurrence,
  deletePMOccurrence,
  deletePMSchedule,
} from "../../../api/ai5rClient";
import { mapPMScheduleRecord, mapPMOccurrenceRecord, withResolvedArea } from "../utils/pmMapping";
import { mapCMReportRecord } from "../utils/cmMapping";
import { useOptionalAuth } from "../auth/AuthContext";
import { can, PERMISSIONS } from "../auth/permissions";
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
  // MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- editingSchedule holds the real
  // schedule record being edited (not just an id), so the modal can
  // prefill from it directly without a second lookup.
  const [editingSchedule, setEditingSchedule] = useState(null);
  // MWO-LTSA-PM-CM-INTAKE-001 -- a real PM Occurrence (an actual field
  // visit: activities/finding/preliminary recommendation), distinct from
  // pm_schedule above (the recurring plan/template this page's own
  // "Create PM Schedule" button already manages -- see
  // CreatePMOccurrenceModal.jsx's own header for why these are two
  // different entities, not the same create flow).
  const [isCreateOccurrenceModalOpen, setIsCreateOccurrenceModalOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);
  // MWO-LTSA-053 -- Related CM Reports, resolved the same "fetch once,
  // derive many client-side" way Pump.jsx/Seal.jsx already resolve their
  // own Related Engineering groups (getCMReports is the same already-wired
  // endpoint, nothing new).
  const [cmReports, setCmReports] = useState([]);
  // MWO-LTSA-PM-CM-REVIEW-UI-001 -- real PM Occurrence listing (the
  // disclosed gap from MWO-LTSA-PM-CM-INTAKE-001's own completion report:
  // occurrences could be created but never displayed anywhere). Same
  // "fetch once, derive many client-side" pattern as cmReports above --
  // getPMOccurrences() has no per-schedule filter, so occurrences for the
  // selected schedule are derived below via pmScheduleCode.
  const [pmOccurrences, setPmOccurrences] = useState([]);
  const [selectedOccurrenceId, setSelectedOccurrenceId] = useState(null);

  // MWO-LTSA-AUTH-003A-FINAL / MWO-LTSA-PM-CM-REVIEW-UI-001 -- role-gated
  // review action visibility (Phase 6/7/8): useOptionalAuth() never
  // throws with no AuthProvider, so every existing bare-render test
  // (<PM />) keeps working unchanged; can(null, ...) degrades to false.
  const authContext = useOptionalAuth();
  const canWriteMaintenance = can(authContext?.session, PERMISSIONS.MAINTENANCE_WRITE);
  const canAdminReviewMaintenance = can(authContext?.session, PERMISSIONS.MAINTENANCE_ADMIN_REVIEW);
  const canTechnicalReviewMaintenance = can(authContext?.session, PERMISSIONS.MAINTENANCE_TECHNICAL_REVIEW);
  const canDeleteRecords = authContext?.session?.role === "SUPERUSER";

  function upsertOccurrence(rawRecord) {
    const mapped = mapPMOccurrenceRecord(rawRecord);
    setPmOccurrences((current) => {
      const exists = current.some((occ) => occ.id === mapped.id);
      return exists ? current.map((occ) => (occ.id === mapped.id ? mapped : occ)) : [...current, mapped];
    });
    return mapped;
  }

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

    getPMOccurrences()
      .then((records) => { if (active) setPmOccurrences(records.map(mapPMOccurrenceRecord)); })
      .catch(() => { if (active) setPmOccurrences([]); });

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
  //
  // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- { occurrenceSelectId }
  // is a distinct contract from { selectId } above (which always means
  // "a pm_schedule_code"): Asset 360's PM Timeline events select a real
  // pm_occurrence directly (see selectedOccurrence below, resolved against
  // the full pmOccurrences list, not gated behind a matching schedule --
  // a historically-imported occurrence's own pm_schedule_code is the
  // shared, non-unique "UNSCHEDULED::<workbook>" placeholder, never a real
  // schedule row).
  useEffect(() => {
    if (navContext?.occurrenceSelectId) {
      setSelectedOccurrenceId(navContext.occurrenceSelectId);
    } else if (navContext?.selectId) {
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

  // MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- "Completed items should NOT
  // remain in default active schedule view... may remain accessible
  // separately." A deny-list (exclude only the two terminal statuses),
  // not an allow-list of the 5-state lifecycle's own 3 non-terminal
  // names -- a pre-existing stored status outside that list (e.g.
  // ON_HOLD) is still legitimately open work and must stay visible by
  // default, never silently hidden just for not matching the new
  // vocabulary. COMPLETED/CANCELLED schedules stay reachable via the SAME
  // filter dropdown (statusOptions above already lists every status
  // actually present) by explicitly selecting them -- the existing
  // "completed schedule catalog" the mission allows to remain a separate,
  // deliberate view rather than a new page.
  const TERMINAL_SCHEDULE_STATUSES = new Set(["COMPLETED", "CANCELLED"]);

  const filteredPMSchedules = useMemo(
    () =>
      pmSchedules.filter(
        (pm) =>
          matchesSearch(pm, search) &&
          (statusFilter === "ALL" ? !TERMINAL_SCHEDULE_STATUSES.has(pm.status) : pm.status === statusFilter)
      ),
    [pmSchedules, search, statusFilter]
  );

  const selectedPM = filteredPMSchedules.find((pm) => pm.id === selectedId) ?? null;

  // MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- distinguishes "arrived scoped
  // to a specific pump (navContext.assetTag) and that pump genuinely has
  // no active PM Schedule" from the generic "nothing picked yet" empty
  // state. AUTO_CREATE_PM_SCHEDULE=NO: this never creates a schedule --
  // it only offers the explicit, separate Create PM Schedule action for
  // an authorized user, prefilled with the pump already being viewed.
  const noScheduleForAssetTag =
    Boolean(navContext?.assetTag) &&
    !loading &&
    !selectedPM &&
    !selectedOccurrenceId &&
    !pmSchedules.some((pm) => pm.equipmentTag === navContext.assetTag);

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

  // MWO-LTSA-PM-CM-REVIEW-UI-001 -- occurrences recorded against the
  // selected schedule, derived from the already-fetched pmOccurrences
  // list the same "filter, don't re-fetch" way relatedPMRecords/
  // relatedCMRecords already do above.
  const occurrencesForSelectedPM = selectedPM
    ? pmOccurrences.filter((occ) => occ.pmScheduleCode === selectedPM.id)
    : [];
  // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- resolved against the
  // full pmOccurrences list, not occurrencesForSelectedPM: a historical
  // occurrence deep-linked from Asset 360 (navContext.occurrenceSelectId
  // above) has no matching pm_schedule row to select first, so
  // selectedPM may legitimately be null while an occurrence is still
  // selected. The existing schedule-nested "click an occurrence button"
  // flow is unaffected -- every occurrence in occurrencesForSelectedPM is
  // also in pmOccurrences, so this lookup still resolves it identically.
  const selectedOccurrence = pmOccurrences.find((occ) => occ.id === selectedOccurrenceId) ?? null;

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
  async function handleCreate(formValues) {
    try {
      const result = await createPMSchedule({
        pm_schedule_code: formValues.scheduleCode,
        asset_code: formValues.equipmentTag,
        procedure: formValues.procedure,
        frequency: formValues.frequency,
        trigger_type: formValues.triggerType,
        interval_unit: formValues.intervalUnit,
        effective_date: formValues.startDate || null,
        next_due: formValues.startDate || null,
        assigned_to: formValues.assignedTechnician || null,
      });
      const created = mapPMScheduleRecord(result.data);
      setPmSchedules((current) => [...current, created]);
      setIsCreateModalOpen(false);
      setSelectedId(created.id);
      setSuccessMessage(`PM Schedule ${created.id} created.`);
    } catch (error) {
      setListError(error.message);
    }
  }

  // MWO-LTSA-PM-CM-INTAKE-001 -- real persistence: POST /api/ltsa/
  // pm-occurrences (pm_occurrence_repository.py, bypassing the
  // deliberately append-only PM Occurrence gateway). Requires an already-
  // selected pm_schedule (pm_occurrence.pm_schedule_code is NOT NULL,
  // matching the real committed schema) -- the button that opens this
  // modal is only rendered once a schedule is selected.
  async function handleRecordOccurrence({ occurrenceDate, activities, remarks }) {
    const result = await createPMOccurrence({
      pmScheduleCode: selectedPM.id,
      assetCode: selectedPM.equipmentTag,
      occurrenceDate,
      activities,
      remarks,
    });
    const newOccurrence = upsertOccurrence(result.data);
    setIsCreateOccurrenceModalOpen(false);
    setSelectedOccurrenceId(newOccurrence.id);
    setSuccessMessage(`PM Occurrence ${newOccurrence.id} recorded (DRAFT).`);
  }

  // MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 6/7/8/9 -- draft edit/submit/
  // admin-review/technical-review handlers. Each calls the already-real
  // backend route (ai5rClient.js, built by MWO-LTSA-PM-CM-INTAKE-001) and
  // reconciles local state from the RETURNING response, never from a
  // locally-fabricated guess -- the same "server response is truth"
  // convention handleRecordOccurrence above and ConditionMonitoring.jsx's
  // handleCreateReading already use. Errors are re-thrown so
  // PMOccurrenceDetailPanel's own per-action error state (never a fake
  // success) can display them verbatim.
  async function handleSaveOccurrenceDraft(code, payload) {
    const result = await updatePMOccurrenceDraft(code, payload);
    upsertOccurrence(result.data);
    setSuccessMessage(`PM Occurrence ${code} saved.`);
  }

  async function handleSubmitOccurrence(code) {
    const result = await submitPMOccurrence(code);
    upsertOccurrence(result.data);
    setSuccessMessage(`PM Occurrence ${code} submitted for review.`);
  }

  async function handleAdminReturnOccurrence(code, returnReason) {
    const result = await adminReviewPMOccurrence(code, returnReason);
    upsertOccurrence(result.data);
    setSuccessMessage(`PM Occurrence ${code} returned for correction.`);
  }

  async function handleTechnicalReviewOccurrence(code, payload) {
    const result = await technicalReviewPMOccurrence(code, payload);
    upsertOccurrence(result.data);
    setSuccessMessage(`PM Occurrence ${code} technical review recorded.`);
  }

  async function handleDeleteOccurrence(code, reason) {
    await deletePMOccurrence(code, reason);
    setPmOccurrences((current) => current.filter((occurrence) => occurrence.id !== code));
    setSelectedOccurrenceId(null);
    setSuccessMessage(`PM Occurrence ${code} soft-deleted.`);
  }

  async function handleDeleteSchedule(code, reason) {
    await deletePMSchedule(code, reason);
    setPmSchedules((current) => current.filter((schedule) => schedule.id !== code));
    setSelectedId(null);
    setSuccessMessage(`PM Schedule ${code} deactivated.`);
  }

  // MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- uses the already-real PATCH
  // endpoint (updatePMSchedule); reconciles local state from the
  // RETURNING response, never from a locally-fabricated guess -- the same
  // "server response is truth" convention every other handler in this
  // file already follows.
  async function handleUpdateSchedule(code, payload) {
    const result = await updatePMSchedule(code, payload);
    const updated = mapPMScheduleRecord(result.data);
    setPmSchedules((current) => current.map((schedule) => (schedule.id === code ? updated : schedule)));
    setSuccessMessage(`PM Schedule ${code} updated.`);
  }

  return (
    <div>
      <PageHeader
        title="Preventive Maintenance Workspace"
        subtitle="LTSA Engineering — PM Schedule Registry"
        actions={
          <span style={{ display: "flex", gap: "var(--space-2)" }}>
            {/* MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 6/13 -- this button was
                previously ungated (any authenticated role could open the
                create-occurrence modal); Pertamina must never see a write
                control. Gated on the same MAINTENANCE_WRITE capability
                the resulting create call requires server-side. */}
            {selectedPM && canWriteMaintenance && (
              <Button onClick={() => setIsCreateOccurrenceModalOpen(true)}>+ Record PM Occurrence</Button>
            )}
            <Button onClick={() => setIsCreateModalOpen(true)}>+ Create PM Schedule</Button>
          </span>
        }
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
            {selectedPM || selectedOccurrence ? (
              <>
                {selectedPM ? (
                  <PMOpenDesignView
                    pm={selectedPM}
                    relatedPMRecords={relatedPMRecords}
                    cmRecords={relatedCMRecords}
                    onOpenPump={handleOpenPump}
                    onOpenDrawing={handleOpenDrawing}
                    onCreatePM={() => setIsCreateModalOpen(true)}
                    canDelete={canDeleteRecords}
                    onDelete={handleDeleteSchedule}
                    canEdit={canWriteMaintenance}
                    onEdit={setEditingSchedule}
                  />
                ) : (
                  // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- a
                  // historically-imported occurrence deep-linked from
                  // Asset 360 has no matching pm_schedule row (its own
                  // pm_schedule_code is the shared UNSCHEDULED::<workbook>
                  // placeholder, not a real schedule) -- disclosed
                  // honestly rather than silently omitted.
                  <EmptyState
                    title="No PM Schedule for this occurrence"
                    description="This is a historically-imported record with no matching PM Schedule -- shown by its own record only."
                  />
                )}

                {/* MWO-LTSA-PM-CM-REVIEW-UI-001 -- real PM Occurrence
                    records for this schedule, the disclosed gap from
                    MWO-LTSA-PM-CM-INTAKE-001's own completion report
                    ("occurrences could be created but never displayed"). */}
                <div style={{ marginTop: "var(--space-4, 24px)" }}>
                  <h3>PM Occurrences</h3>
                  {selectedPM && occurrencesForSelectedPM.length === 0 ? (
                    <Panel>
                      <p>No PM occurrences recorded for this schedule yet.</p>
                    </Panel>
                  ) : selectedPM ? (
                    <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap", marginBottom: "var(--space-3)" }}>
                      {occurrencesForSelectedPM.map((occ) => (
                        <Button key={occ.id} onClick={() => setSelectedOccurrenceId(occ.id)}>
                          {occ.id} ({occ.workflowStatus})
                        </Button>
                      ))}
                    </div>
                  ) : null}

                  {selectedOccurrence && (
                    <PMOccurrenceDetailPanel
                      occurrence={selectedOccurrence}
                      canWrite={canWriteMaintenance}
                      canAdminReview={canAdminReviewMaintenance}
                      canTechnicalReview={canTechnicalReviewMaintenance}
                      canDelete={canDeleteRecords}
                      onDelete={handleDeleteOccurrence}
                      onSaveDraft={handleSaveOccurrenceDraft}
                      onSubmit={handleSubmitOccurrence}
                      onAdminReturn={handleAdminReturnOccurrence}
                      onTechnicalReview={handleTechnicalReviewOccurrence}
                      onOpenPump={handleOpenPump}
                    />
                  )}
                </div>
              </>
            ) : noScheduleForAssetTag ? (
              // MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- exact required
              // message, plus the explicit, separate Create action for an
              // authorized user only. Never auto-creates a schedule --
              // clicking this only opens the existing create form (a
              // second, separate user action), it does not itself create
              // anything.
              <>
                <EmptyState
                  title="No active PM Schedule is available for this pump."
                  description={
                    canWriteMaintenance
                      ? "Create a PM Schedule for this pump before recording a PM occurrence."
                      : "Contact an authorized user to create a PM Schedule for this pump."
                  }
                />
                {canWriteMaintenance && (
                  <div style={{ marginTop: "var(--space-3)" }}>
                    <Button onClick={() => setIsCreateModalOpen(true)}>Create PM Schedule</Button>
                  </div>
                )}
              </>
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
        initialEquipmentTag={noScheduleForAssetTag ? navContext.assetTag : ""}
      />

      <EditPMScheduleModal
        isOpen={Boolean(editingSchedule)}
        onClose={() => setEditingSchedule(null)}
        onSave={handleUpdateSchedule}
        pm={editingSchedule}
      />

      {selectedPM && (
        <CreatePMOccurrenceModal
          isOpen={isCreateOccurrenceModalOpen}
          onClose={() => setIsCreateOccurrenceModalOpen(false)}
          onCreate={handleRecordOccurrence}
          pmScheduleCode={selectedPM.id}
          equipmentTag={selectedPM.equipmentTag}
        />
      )}
    </div>
  );
}
