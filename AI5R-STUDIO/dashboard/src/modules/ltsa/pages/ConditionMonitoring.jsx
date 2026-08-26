import { useEffect, useMemo, useState } from "react";
import { Button, PageHeader, Panel, Tabs } from "../../../design-system";
import ConditionMonitoringScheduleFilterBar from "../components/ConditionMonitoringScheduleFilterBar";
import ConditionMonitoringScheduleTable from "../components/ConditionMonitoringScheduleTable";
import ConditionMonitoringScheduleDetailPanel from "../components/ConditionMonitoringScheduleDetailPanel";
import ConditionMonitoringReadingFilterBar from "../components/ConditionMonitoringReadingFilterBar";
import ConditionMonitoringReadingTable from "../components/ConditionMonitoringReadingTable";
import ConditionMonitoringReadingDetailPanel from "../components/ConditionMonitoringReadingDetailPanel";
import CreateConditionMonitoringReadingModal from "../components/CreateConditionMonitoringReadingModal";
import CreateConditionMonitoringScheduleModal from "../components/CreateConditionMonitoringScheduleModal";
import SuccessToast from "../components/SuccessToast";
import {
  getConditionMonitoringReadings, getConditionMonitoringSchedules, createConditionMonitoringReading,
  updateConditionMonitoringReadingDraft, submitConditionMonitoringReading,
  adminReviewConditionMonitoringReading, technicalReviewConditionMonitoringReading,
  deleteConditionMonitoringReading,
  deleteConditionMonitoringSchedule,
  createConditionMonitoringSchedule,
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
  const [selectedScheduleId, setSelectedScheduleId] = useState(null);

  const [readings, setReadings] = useState([]);
  const [readingsLoading, setReadingsLoading] = useState(true);
  const [readingsError, setReadingsError] = useState(null);
  const [readingSearch, setReadingSearch] = useState("");
  const [readingLeakFilter, setReadingLeakFilter] = useState("ALL");
  const [selectedReadingId, setSelectedReadingId] = useState(null);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isCreateScheduleModalOpen, setIsCreateScheduleModalOpen] = useState(false);
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

  const filteredSchedules = useMemo(
    () => schedules.filter((schedule) => matchesScheduleSearch(schedule, scheduleSearch)),
    [schedules, scheduleSearch]
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
      <CreateConditionMonitoringScheduleModal
        isOpen={isCreateScheduleModalOpen}
        onClose={() => setIsCreateScheduleModalOpen(false)}
        onCreate={handleCreateSchedule}
      />
    </div>
  );
}
