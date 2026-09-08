import { useEffect, useMemo, useState } from "react";
import { Button, PageHeader, Panel, Tabs } from "../../../design-system";
import ConditionMonitoringScheduleFilterBar from "../components/ConditionMonitoringScheduleFilterBar";
import ConditionMonitoringScheduleTable from "../components/ConditionMonitoringScheduleTable";
import ConditionMonitoringScheduleDetailPanel from "../components/ConditionMonitoringScheduleDetailPanel";
import ConditionMonitoringReadingFilterBar from "../components/ConditionMonitoringReadingFilterBar";
import ConditionMonitoringReadingTable from "../components/ConditionMonitoringReadingTable";
import ConditionMonitoringReadingDetailPanel from "../components/ConditionMonitoringReadingDetailPanel";
import CreateConditionMonitoringReadingModal from "../components/CreateConditionMonitoringReadingModal";
import CreateAdHocConditionMonitoringReadingModal from "../components/CreateAdHocConditionMonitoringReadingModal";
import BulkCMONReadingEditor from "../components/BulkCMONReadingEditor";
import CMONExcelImportPanel from "../components/CMONExcelImportPanel";
import CreateConditionMonitoringScheduleModal from "../components/CreateConditionMonitoringScheduleModal";
import EditConditionMonitoringScheduleModal from "../components/EditConditionMonitoringScheduleModal";
import SuccessToast from "../components/SuccessToast";
import {
  getConditionMonitoringReadings, getConditionMonitoringSchedules, createConditionMonitoringReading,
  createAdHocConditionMonitoringReading,
  updateConditionMonitoringReadingDraft, submitConditionMonitoringReading,
  adminReviewConditionMonitoringReading, technicalReviewConditionMonitoringReading,
  deleteConditionMonitoringReading,
  deleteConditionMonitoringSchedule,
  createConditionMonitoringSchedule,
  updateConditionMonitoringSchedule,
} from "../../../api/ai5rClient";
import {
  mapConditionMonitoringReadingRecord,
  mapConditionMonitoringScheduleRecord,
  withResolvedArea,
} from "../utils/conditionMonitoringMapping";
import { useOptionalAuth } from "../auth/AuthContext";
import { can, PERMISSIONS } from "../auth/permissions";
import "./ConditionMonitoring.css";

const VIEWS = [
  { key: "schedules", label: "Schedules" },
  { key: "readings", label: "Readings" },
];

function matchesScheduleSearch(schedule, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    (schedule.id || "").toLowerCase().includes(term) ||
    (schedule.equipmentTag || "").toLowerCase().includes(term)
  );
}

function matchesReadingSearch(reading, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    (reading.id || "").toLowerCase().includes(term) ||
    (reading.equipmentTag || "").toLowerCase().includes(term)
  );
}

/**
 * The canonical Condition Monitoring workspace (APP-CMON-001, per
 * ADR-CONDITION-MONITORING-001). Frontend-only: reuses
 * ConditionMonitoringScheduleGateway/ConditionMonitoringReadingGateway's
 * already-real list/detail routes (WO-CMON-001/WO-CMON-002) -- no new
 * backend, no schema change. Schedule detail is full CRUD-capable on the
 * gateway, but this MWO only requested list/detail/create-Reading, so no
 * Schedule create/edit UI is built here.
 *
 * Two internal views (Schedules / Readings), each with the same registry-
 * table + detail-panel layout every other LTSA workspace already uses --
 * reused, not reinvented. `navContext.selectId` (from Asset 360's Active
 * Plans panel) pre-selects a Schedule and switches to the Schedules view.
 */
export default function ConditionMonitoring({ onNavigate, navContext }) {
  const [view, setView] = useState("schedules");

  const [schedules, setSchedules] = useState([]);
  const [schedulesLoading, setSchedulesLoading] = useState(true);
  const [schedulesError, setSchedulesError] = useState(null);
  const [scheduleSearch, setScheduleSearch] = useState("");
  // MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- status filter, mirroring
  // PM.jsx's own statusFilter state exactly.
  const [scheduleStatusFilter, setScheduleStatusFilter] = useState("ALL");
  const [selectedScheduleId, setSelectedScheduleId] = useState(null);

  const [readings, setReadings] = useState([]);
  const [readingsLoading, setReadingsLoading] = useState(true);
  const [readingsError, setReadingsError] = useState(null);
  const [readingSearch, setReadingSearch] = useState("");
  const [readingLeakFilter, setReadingLeakFilter] = useState("ALL");
  const [selectedReadingId, setSelectedReadingId] = useState(null);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isAdHocCreateModalOpen, setIsAdHocCreateModalOpen] = useState(false);
  const [isBulkEditorOpen, setIsBulkEditorOpen] = useState(false);
  const [bulkEditorInitialRows, setBulkEditorInitialRows] = useState([]);
  const [isExcelImportOpen, setIsExcelImportOpen] = useState(false);
  const [isCreateScheduleModalOpen, setIsCreateScheduleModalOpen] = useState(false);
  // MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- editingSchedule holds the real
  // schedule record being edited (not just an id), so the modal can
  // prefill from it directly without a second lookup.
  const [editingSchedule, setEditingSchedule] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 6/7/8 -- role-gated review action
  // visibility, the same useOptionalAuth()/can() pattern PM.jsx/Seal.jsx
  // already use. useOptionalAuth() never throws with no AuthProvider, so
  // every existing bare-render test (<ConditionMonitoring />) keeps
  // working unchanged; can(null, ...) degrades to false.
  const authContext = useOptionalAuth();
  const canWriteMaintenance = can(authContext?.session, PERMISSIONS.MAINTENANCE_WRITE);
  const canAdminReviewMaintenance = can(authContext?.session, PERMISSIONS.MAINTENANCE_ADMIN_REVIEW);
  const canTechnicalReviewMaintenance = can(authContext?.session, PERMISSIONS.MAINTENANCE_TECHNICAL_REVIEW);
  const canDeleteRecords = authContext?.session?.role === "SUPERUSER";

  useEffect(() => {
    let active = true;

    getConditionMonitoringSchedules()
      .then((records) => Promise.all(records.map(mapConditionMonitoringScheduleRecord).map(withResolvedArea)))
      .then((resolved) => {
        if (active) {
          setSchedules(resolved);
          setSchedulesError(null);
        }
      })
      .catch(() => {
        if (active) {
          setSchedulesError("Condition Monitoring schedules could not be loaded.");
        }
      })
      .finally(() => {
        if (active) {
          setSchedulesLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    getConditionMonitoringReadings()
      .then((records) => Promise.all(records.map(mapConditionMonitoringReadingRecord).map(withResolvedArea)))
      .then((resolved) => {
        if (active) {
          setReadings(resolved);
          setReadingsError(null);
        }
      })
      .catch(() => {
        if (active) {
          setReadingsError("Condition Monitoring readings could not be loaded.");
        }
      })
      .finally(() => {
        if (active) {
          setReadingsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  // Deep-link entry point (per this MWO's "Navigation from Asset 360
  // Active Plans" requirement): ActivePlansPanel navigates here with
  // { selectId: scheduleCode }.
  //
  // MWO-LTSA-ASSET360-PM-CMON-TRACEABILITY-001 -- { readingSelectId } is a
  // separate, distinct contract: Asset 360's INSPECTION Timeline events
  // select a real condition_monitoring_reading directly, landing on the
  // Readings view/tab (already keyed by reading id, never nested behind a
  // schedule selection -- unlike PM.jsx, no restructuring was needed here
  // for the Readings view itself).
  useEffect(() => {
    if (navContext?.readingSelectId) {
      setView("readings");
      setSelectedReadingId(navContext.readingSelectId);
    } else if (navContext?.selectId) {
      setView("schedules");
      setSelectedScheduleId(navContext.selectId);
    }
  }, [navContext]);

  // MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- statusOptions/
  // TERMINAL_SCHEDULE_STATUSES/filteredSchedules mirror PM.jsx's own
  // identical logic exactly: "ALL" means the active work queue (every
  // status except Completed/Cancelled), not literally every row.
  const scheduleStatusOptions = useMemo(
    () => [...new Set(schedules.map((schedule) => schedule.status))],
    [schedules]
  );
  const TERMINAL_SCHEDULE_STATUSES = new Set(["COMPLETED", "CANCELLED"]);

  const filteredSchedules = useMemo(
    () =>
      schedules.filter(
        (schedule) =>
          matchesScheduleSearch(schedule, scheduleSearch) &&
          (scheduleStatusFilter === "ALL"
            ? !TERMINAL_SCHEDULE_STATUSES.has(schedule.status)
            : schedule.status === scheduleStatusFilter)
      ),
    [schedules, scheduleSearch, scheduleStatusFilter]
  );
  const selectedSchedule = filteredSchedules.find((schedule) => schedule.id === selectedScheduleId) ?? null;

  const filteredReadings = useMemo(
    () =>
      readings.filter((reading) => {
        if (!matchesReadingSearch(reading, readingSearch)) {
          return false;
        }

        const leakDetected = reading.leakDe || reading.leakNde;
        if (readingLeakFilter === "LEAK" && !leakDetected) {
          return false;
        }
        if (readingLeakFilter === "NORMAL" && leakDetected) {
          return false;
        }

        return true;
      }),
    [readings, readingSearch, readingLeakFilter]
  );
  const selectedReading = filteredReadings.find((reading) => reading.id === selectedReadingId) ?? null;

  function handleViewAsset360(assetTag) {
    if (assetTag) {
      onNavigate?.("history", { assetTag });
    }
  }

  function handleViewSchedule(scheduleCode) {
    setView("schedules");
    setSelectedScheduleId(scheduleCode);
  }

  async function handleCreateSchedule(formValues) {
    try {
      const result = await createConditionMonitoringSchedule({
        condition_monitoring_schedule_code: formValues.code,
        asset_code: formValues.equipmentTag,
        monitoring_type: formValues.monitoringType,
        measurement_point: formValues.measurementPoint || null,
        frequency: formValues.frequency || null,
        interval_unit: formValues.intervalUnit || null,
        effective_date: formValues.effectiveDate || null,
        // MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- the single
        // "Effective Date" field drives both columns, the exact same
        // convention PM.jsx's own handleCreate already established
        // (formValues.startDate -> both effective_date and next_due).
        next_due: formValues.effectiveDate || null,
      });
      const schedule = mapConditionMonitoringScheduleRecord(result.data);
      setSchedules((current) => [...current, schedule]);
      setIsCreateScheduleModalOpen(false);
      setSelectedScheduleId(schedule.id);
      setSuccessMessage(`Condition Monitoring Schedule ${schedule.id} created.`);
    } catch (error) {
      setSchedulesError(error.message);
    }
  }

  // MWO-LTSA-PM-CM-INTAKE-001 -- real persistence: POST /api/ltsa/
  // condition-monitoring-readings (condition_monitoring_reading_
  // repository.py, bypassing the deliberately append-only Reading
  // gateway -- see that repository's own header). The response is run
  // through the exact same mapConditionMonitoringReadingRecord() the
  // real getConditionMonitoringReadings() fetch path already uses, so
  // the newly-created reading renders identically to one loaded from a
  // page reload -- not a separately-shaped local object.
  const [createError, setCreateError] = useState(null);

  async function handleCreateReading(formValues) {
    setCreateError(null);
    try {
      // MWO-LTSA-PM-CM-REVIEW-PRE-PUSH-CLOSURE-001 -- formValues.measurements
      // is already the complete, correctly-null-coerced snake_case payload
      // (built by CreateConditionMonitoringReadingModal.jsx via the shared
      // buildMeasurementsPayload() helper, conditionMonitoringMeasurementFields.js)
      // covering every canonical migration-014 field, not just the 7-field
      // subset this handler previously hand-mapped.
      const result = await createConditionMonitoringReading({
        conditionMonitoringScheduleCode: formValues.scheduleCode,
        assetCode: formValues.equipmentTag,
        readingDate: formValues.readingDate || null,
        measurements: formValues.measurements,
      });
      const newReading = mapConditionMonitoringReadingRecord(result.data);
      setReadings((current) => [...current, newReading]);
      setIsCreateModalOpen(false);
      setView("readings");
      setSelectedReadingId(newReading.id);
      setSuccessMessage(`Condition Monitoring reading ${newReading.id} created (DRAFT).`);
    } catch (err) {
      // Verbatim backend detail (e.g. a 403 if permissions changed
      // mid-session) -- never a generic "failed" message.
      setCreateError(err.message);
    }
  }

  // MWO-LTSA-CMON-ADHOC-ENTRY-001 -- the schedule-free sibling of
  // handleCreateReading above: no condition_monitoring_schedule_code is
  // ever sent, matching CreateAdHocConditionMonitoringReadingModal's own
  // payload exactly. Never touches `schedules` or the schedule-required
  // create path -- that flow (handleCreateReading, isCreateModalOpen)
  // stays completely unmodified.
  //
  // AI5R-CMON-UX-PHASE1B -- this stays the ONLY place performing the real
  // create call, for both the modal's "Save Reading" and "Save & Add
  // Another" actions. It returns the created (mapped) record on success so
  // the modal can decide what happens next, and re-throws on failure
  // (after recording it in createError) rather than converting a failed
  // request into a false success -- closing/selecting/navigating on
  // success is no longer this function's decision; see
  // handleAdHocReadingSaved below, invoked only for "Save Reading".
  async function handleCreateAdHocReading(formValues) {
    setCreateError(null);
    try {
      const result = await createAdHocConditionMonitoringReading({
        assetCode: formValues.assetCode,
        readingDate: formValues.readingDate,
        measurements: formValues.measurements,
        finding: formValues.finding,
      });
      const newReading = mapConditionMonitoringReadingRecord(result.data);
      setReadings((current) => [...current, newReading]);
      return newReading;
    } catch (err) {
      setCreateError(err.message);
      throw err;
    }
  }

  // AI5R-CMON-UX-PHASE1B -- fired by the modal only after its own normal
  // "Save Reading" action resolves successfully; "Save & Add Another"
  // never calls this, so the modal stays open and the workspace stays on
  // its current view/selection in that case.
  function handleAdHocReadingSaved(newReading) {
    setIsAdHocCreateModalOpen(false);
    setView("readings");
    setSelectedReadingId(newReading.id);
    setSuccessMessage(`Condition Monitoring reading ${newReading.id} created (DRAFT).`);
  }

  // MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001 -- the bulk create already
  // succeeded atomically server-side by the time this fires (Bulk
  // CMONReadingEditor.jsx only calls onCreated after a 200 response);
  // this only closes the editor, surfaces the count, and refreshes the
  // readings list, mirroring PM.jsx's own handleBulkCreated exactly.
  async function handleBulkReadingsCreated(createdRows) {
    setIsBulkEditorOpen(false);
    setBulkEditorInitialRows([]);
    setSuccessMessage(`${createdRows.length} Condition Monitoring reading${createdRows.length === 1 ? "" : "s"} created.`);
    setView("readings");
    try {
      const records = await getConditionMonitoringReadings();
      const resolved = await Promise.all(records.map(mapConditionMonitoringReadingRecord).map(withResolvedArea));
      setReadings(resolved);
      setReadingsError(null);
    } catch {
      // The bulk create itself already succeeded (this only refreshes
      // the list) -- a transient refetch failure here is surfaced
      // through the existing readingsError path, never treated as a
      // create failure.
      setReadingsError("Condition Monitoring readings could not be reloaded after bulk create.");
    }
  }

  function upsertReading(rawRecord) {
    const mapped = mapConditionMonitoringReadingRecord(rawRecord);
    setReadings((current) => {
      const exists = current.some((reading) => reading.id === mapped.id);
      return exists ? current.map((reading) => (reading.id === mapped.id ? mapped : reading)) : [...current, mapped];
    });
    return mapped;
  }

  // MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 6/7/8/9 -- draft edit/submit/
  // admin-review/technical-review handlers, mirroring PM.jsx's own
  // handleSaveOccurrenceDraft/handleSubmitOccurrence/etc. exactly (same
  // shared pm_cm_workflow_service.py state machine, Phase 10). Errors are
  // re-thrown so ConditionMonitoringReadingDetailPanel's own per-action
  // error state (never a fake success) can display them verbatim.
  async function handleSaveReadingDraft(code, payload) {
    const result = await updateConditionMonitoringReadingDraft(code, payload);
    upsertReading(result.data);
    setSuccessMessage(`Condition Monitoring reading ${code} saved.`);
  }

  async function handleSubmitReading(code) {
    const result = await submitConditionMonitoringReading(code);
    upsertReading(result.data);
    setSuccessMessage(`Condition Monitoring reading ${code} submitted for review.`);
  }

  async function handleAdminReturnReading(code, returnReason) {
    const result = await adminReviewConditionMonitoringReading(code, returnReason);
    upsertReading(result.data);
    setSuccessMessage(`Condition Monitoring reading ${code} returned for correction.`);
  }

  async function handleTechnicalReviewReading(code, payload) {
    const result = await technicalReviewConditionMonitoringReading(code, payload);
    upsertReading(result.data);
    setSuccessMessage(`Condition Monitoring reading ${code} technical review recorded.`);
  }

  async function handleDeleteReading(code, reason) {
    await deleteConditionMonitoringReading(code, reason);
    setReadings((current) => current.filter((reading) => reading.id !== code));
    setSelectedReadingId(null);
    setSuccessMessage(`Condition Monitoring reading ${code} soft-deleted.`);
  }

  async function handleDeleteSchedule(code, reason) {
    await deleteConditionMonitoringSchedule(code, reason);
    setSchedules((current) => current.filter((schedule) => schedule.id !== code));
    setSelectedScheduleId(null);
    setSuccessMessage(`Condition Monitoring Schedule ${code} deactivated.`);
  }

  // MWO-LTSA-PM-CMON-OPERATIONAL-UI-014C -- uses the already-real PATCH
  // endpoint (updateConditionMonitoringSchedule); reconciles local state
  // from the RETURNING response, never from a locally-fabricated guess --
  // the same "server response is truth" convention every other handler in
  // this file already follows.
  async function handleUpdateSchedule(code, payload) {
    const result = await updateConditionMonitoringSchedule(code, payload);
    const updated = mapConditionMonitoringScheduleRecord(result.data);
    setSchedules((current) => current.map((schedule) => (schedule.id === code ? updated : schedule)));
    setSuccessMessage(`Condition Monitoring Schedule ${code} updated.`);
  }

  // MWO-LTSA-CMON-EXCEL-IMPORT-001 -- checked BEFORE the bulk editor
  // below, same ordering as PM.jsx: "Review in Bulk Editor" closes this
  // panel and opens the editor with the parsed rows, in one transition.
  if (isExcelImportOpen) {
    return (
      <CMONExcelImportPanel
        onClose={() => setIsExcelImportOpen(false)}
        onReviewInBulkEditor={(rows) => {
          setBulkEditorInitialRows(rows);
          setIsExcelImportOpen(false);
          setIsBulkEditorOpen(true);
        }}
      />
    );
  }

  // MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001 -- a dedicated full-width view
  // (not a modal), same convention as PM.jsx's own BulkPMScheduleEditor
  // early return -- practical for the ~10-100 row scale this editor
  // targets.
  if (isBulkEditorOpen) {
    return (
      <BulkCMONReadingEditor
        onClose={() => {
          setIsBulkEditorOpen(false);
          setBulkEditorInitialRows([]);
        }}
        onCreated={handleBulkReadingsCreated}
        initialRows={bulkEditorInitialRows}
      />
    );
  }

  return (
    <div>
      <PageHeader
        title="Condition Monitoring"
        subtitle="LTSA Engineering — Condition Monitoring Registry"
        actions={
          // MWO-LTSA-PM-CM-REVIEW-UI-001, Phase 6/13 -- previously
          // ungated (any authenticated role could open the create-reading
          // modal); Pertamina must never see a write control. Gated on
          // the same MAINTENANCE_WRITE capability the resulting create
          // call requires server-side.
          <>
            {canWriteMaintenance && view === "schedules" && <Button onClick={() => setIsCreateScheduleModalOpen(true)}>+ Create Schedule</Button>}
            {canWriteMaintenance && schedules.length > 0 && <Button onClick={() => setIsCreateModalOpen(true)}>+ Create Reading</Button>}
            {/* MWO-LTSA-CMON-ADHOC-ENTRY-001 -- always available, unlike
                "+ Create Reading" above, which stays gated on an existing
                active schedule (unchanged). This is the fix for the real
                gap: a pump with zero schedules had no way to record a
                reading at all. */}
            {canWriteMaintenance && <Button onClick={() => setIsAdHocCreateModalOpen(true)}>+ Add Reading</Button>}
            {/* MWO-LTSA-CMON-BULK-ADHOC-ENTRY-001 -- also always
                available, same reasoning as "+ Add Reading" above: no
                schedule is required for any row in the bulk editor
                either. */}
            {canWriteMaintenance && <Button onClick={() => setIsBulkEditorOpen(true)}>Bulk Reading</Button>}
            {/* MWO-LTSA-CMON-EXCEL-IMPORT-001 -- its only exit into the
                Bulk Editor is onReviewInBulkEditor above, never a direct
                create -- Excel upload cannot create a reading by itself. */}
            {canWriteMaintenance && <Button onClick={() => setIsExcelImportOpen(true)}>Import Excel</Button>}
          </>
        }
      />

      <SuccessToast message={successMessage} onDismiss={() => setSuccessMessage(null)} />
      {createError && (
        <p className="confidence-label" style={{ color: "var(--color-danger, #d33)" }} data-testid="cmon-create-error">
          {createError}
        </p>
      )}

      <Tabs items={VIEWS} activeKey={view} onChange={setView} />

      {view === "readings" && schedules.length === 0 && !schedulesLoading && (
        <Panel><p>No active Condition Monitoring Schedule is available for this pump.</p></Panel>
      )}

      {view === "schedules" ? (
        <>
          <ConditionMonitoringScheduleFilterBar
            searchValue={scheduleSearch}
            onSearchChange={setScheduleSearch}
            statusFilter={scheduleStatusFilter}
            onStatusFilterChange={setScheduleStatusFilter}
            statusOptions={scheduleStatusOptions}
          />

          {schedulesLoading ? (
            <Panel>
              <p>Loading Condition Monitoring schedules...</p>
            </Panel>
          ) : schedulesError ? (
            <Panel>
              <p role="alert">{schedulesError}</p>
            </Panel>
          ) : (
            <div className="condition-monitoring-workspace-layout">
              <div className="condition-monitoring-workspace-registry">
                <ConditionMonitoringScheduleTable
                  schedules={filteredSchedules}
                  selectedId={selectedScheduleId}
                  onSelect={setSelectedScheduleId}
                />
              </div>

              <div className="condition-monitoring-workspace-detail">
                <ConditionMonitoringScheduleDetailPanel
                  schedule={selectedSchedule}
                  onViewAsset360={handleViewAsset360}
                  canDelete={canDeleteRecords}
                  onDelete={handleDeleteSchedule}
                  canEdit={canWriteMaintenance}
                  onEdit={setEditingSchedule}
                />
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          <ConditionMonitoringReadingFilterBar
            searchValue={readingSearch}
            onSearchChange={setReadingSearch}
            leakFilter={readingLeakFilter}
            onLeakFilterChange={setReadingLeakFilter}
          />

          {readingsLoading ? (
            <Panel>
              <p>Loading Condition Monitoring readings...</p>
            </Panel>
          ) : readingsError ? (
            <Panel>
              <p role="alert">{readingsError}</p>
            </Panel>
          ) : (
            <div className="condition-monitoring-workspace-layout">
              <div className="condition-monitoring-workspace-registry">
                <ConditionMonitoringReadingTable
                  readings={filteredReadings}
                  selectedId={selectedReadingId}
                  onSelect={setSelectedReadingId}
                />
              </div>

              <div className="condition-monitoring-workspace-detail">
                <ConditionMonitoringReadingDetailPanel
                  reading={selectedReading}
                  onViewAsset360={handleViewAsset360}
                  onViewSchedule={handleViewSchedule}
                  canWrite={canWriteMaintenance}
                  canAdminReview={canAdminReviewMaintenance}
                  canTechnicalReview={canTechnicalReviewMaintenance}
                      canDelete={canDeleteRecords}
                      onDelete={handleDeleteReading}
                  onSaveDraft={handleSaveReadingDraft}
                  onSubmit={handleSubmitReading}
                  onAdminReturn={handleAdminReturnReading}
                  onTechnicalReview={handleTechnicalReviewReading}
                />
              </div>
            </div>
          )}
        </>
      )}

      <CreateConditionMonitoringReadingModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreateReading}
        schedules={schedules}
      />
      <CreateAdHocConditionMonitoringReadingModal
        isOpen={isAdHocCreateModalOpen}
        onClose={() => setIsAdHocCreateModalOpen(false)}
        onCreate={handleCreateAdHocReading}
        onSaved={handleAdHocReadingSaved}
      />
      <CreateConditionMonitoringScheduleModal
        isOpen={isCreateScheduleModalOpen}
        onClose={() => setIsCreateScheduleModalOpen(false)}
        onCreate={handleCreateSchedule}
      />
      <EditConditionMonitoringScheduleModal
        isOpen={Boolean(editingSchedule)}
        onClose={() => setEditingSchedule(null)}
        onSave={handleUpdateSchedule}
        schedule={editingSchedule}
      />
    </div>
  );
}
