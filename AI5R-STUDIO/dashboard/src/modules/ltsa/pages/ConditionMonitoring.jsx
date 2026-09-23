import { useEffect, useMemo, useState } from "react";
import ConditionMonitoringScheduleFilterBar from "../components/ConditionMonitoringScheduleFilterBar";
import ConditionMonitoringScheduleTable from "../components/ConditionMonitoringScheduleTable";
import ConditionMonitoringScheduleDetailPanel from "../components/ConditionMonitoringScheduleDetailPanel";
import ConditionMonitoringReadingFilterBar from "../components/ConditionMonitoringReadingFilterBar";
import ConditionMonitoringReadingTable from "../components/ConditionMonitoringReadingTable";
import ConditionMonitoringReadingDetailPanel from "../components/ConditionMonitoringReadingDetailPanel";
import ConditionMonitoringOpenDesignView from "../components/ConditionMonitoringOpenDesignView";
import ConditionMonitoringReportMeasuring from "../components/ConditionMonitoringReportMeasuring";
import CreateConditionMonitoringReadingModal from "../components/CreateConditionMonitoringReadingModal";
import CreateAdHocConditionMonitoringReadingModal from "../components/CreateAdHocConditionMonitoringReadingModal";
import BulkCMONReadingEditor from "../components/BulkCMONReadingEditor";
import CMONExcelImportPanel from "../components/CMONExcelImportPanel";
import CreateConditionMonitoringScheduleModal from "../components/CreateConditionMonitoringScheduleModal";
import EditConditionMonitoringScheduleModal from "../components/EditConditionMonitoringScheduleModal";
import SuccessToast from "../components/SuccessToast";
import { KpiStrip } from "../components/open-design";
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
import "./LTSAOpenDesign.css";

const VIEWS = [
  { key: "readings", label: "Readings" },
  { key: "schedules", label: "Schedules" },
];

const TERMINAL_SCHEDULE_STATUSES = new Set(["COMPLETED", "CANCELLED"]);

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
 * UI-D2C -- the canonical Condition Monitoring workspace (APP-CMON-001,
 * per ADR-CONDITION-MONITORING-001), migrated from the pre-UI-D1.2 old
 * dark design-system chrome (PageHeader/Panel/Tabs) to Chief's approved
 * light Open Design reference, following the exact pattern UI-D2A.1/
 * UI-D2B established for Work Order/PM. Frontend-only: reuses the
 * already-real list/detail/create/review routes -- no new backend, no
 * schema change, no data/recovery-path change.
 *
 * Unlike Work Order/PM, this page is CONDITION-CENTRIC (mission section
 * 4): Readings is now the default view (previously Schedules), and
 * Readings receives the full AssetIdentityHeader + WorkspaceTabStrip
 * treatment (ConditionMonitoringOpenDesignView) plus the mobile table/
 * card-list/collapsed-summary pattern UI-D2A.1 established. Schedules
 * stays a supporting view -- a visual-parity restyle only (still its own
 * dense desktop table, no mobile card treatment), consistent with this
 * page's own condition-centric framing.
 *
 * The full 35-field measurement set, the DRAFT/SUBMITTED/RETURNED_FOR_
 * CORRECTION/FINALIZED review workflow, and Evidence upload remain in the
 * existing, completely untouched ConditionMonitoringReadingDetailPanel.jsx/
 * ConditionMonitoringScheduleDetailPanel.jsx -- same "frozen complex
 * sub-workflow stays frozen" precedent as PMOccurrenceDetailPanel.jsx.
 *
 * No severity/condition/status/alert column exists on
 * condition_monitoring_reading (this session's own discovery of
 * condition_monitoring_reading_repository.py) -- every KPI/badge below is
 * derived only from real, proven fields: workflow_status (DRAFT/
 * SUBMITTED/RETURNED_FOR_CORRECTION/FINALIZED) and the two leak booleans
 * (mechanical_seal_leak_de/nde). ALERT_SOURCE=leak booleans,
 * ALERT_MODEL=DERIVED (deterministic: leakDe===true || leakNde===true) --
 * never a fabricated alert/health/severity subsystem.
 */
export default function ConditionMonitoring({ onNavigate, navContext }) {
  const [view, setView] = useState("readings");

  const [schedules, setSchedules] = useState([]);
  const [schedulesLoading, setSchedulesLoading] = useState(true);
  const [schedulesError, setSchedulesError] = useState(null);
  const [scheduleSearch, setScheduleSearch] = useState("");
  const [scheduleStatusFilter, setScheduleStatusFilter] = useState("ALL");
  const [selectedScheduleId, setSelectedScheduleId] = useState(null);

  const [readings, setReadings] = useState([]);
  const [readingsLoading, setReadingsLoading] = useState(true);
  const [readingsError, setReadingsError] = useState(null);
  const [readingSearch, setReadingSearch] = useState("");
  const [readingStatusFilter, setReadingStatusFilter] = useState("ALL");
  const [readingLeakFilter, setReadingLeakFilter] = useState("ALL");
  const [readingAreaFilter, setReadingAreaFilter] = useState("ALL");
  const [selectedReadingId, setSelectedReadingId] = useState(null);
  const [reportReading, setReportReading] = useState(null);
  // UI-D2C -- auto-collapse the mobile registry once a reading is
  // selected (CSS-gated to the mobile breakpoint only, ConditionMonitoring.css;
  // no effect on desktop, which always shows the full dense table) -- same
  // pattern UI-D2A.1/UI-D2B established for Work Order/PM.
  const [mobileRegistryCollapsed, setMobileRegistryCollapsed] = useState(false);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isAdHocCreateModalOpen, setIsAdHocCreateModalOpen] = useState(false);
  const [isBulkEditorOpen, setIsBulkEditorOpen] = useState(false);
  const [bulkEditorInitialRows, setBulkEditorInitialRows] = useState([]);
  const [isExcelImportOpen, setIsExcelImportOpen] = useState(false);
  const [isCreateScheduleModalOpen, setIsCreateScheduleModalOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

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
  // Readings view, already keyed by reading id.
  useEffect(() => {
    if (navContext?.readingSelectId) {
      setView("readings");
      setSelectedReadingId(navContext.readingSelectId);
      setMobileRegistryCollapsed(true);
    } else if (navContext?.selectId) {
      setView("schedules");
      setSelectedScheduleId(navContext.selectId);
    }
  }, [navContext]);

  const scheduleStatusOptions = useMemo(
    () => [...new Set(schedules.map((schedule) => schedule.status))],
    [schedules]
  );

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

  // UI-D2C -- Area filter, reusing the same already-real, already-resolved
  // field (reading.area, withResolvedArea) the table already displays;
  // options derived from whatever is actually present in the loaded data,
  // never a hardcoded enum guess (same pattern PMFilterBar.jsx's own
  // areaOptions established).
  const readingAreaOptions = useMemo(
    () => [...new Set(readings.map((reading) => reading.area).filter(Boolean))],
    [readings]
  );

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

        if (readingStatusFilter !== "ALL" && reading.workflowStatus !== readingStatusFilter) {
          return false;
        }

        if (readingAreaFilter !== "ALL" && reading.area !== readingAreaFilter) {
          return false;
        }

        return true;
      }),
    [readings, readingSearch, readingLeakFilter, readingStatusFilter, readingAreaFilter]
  );
  const selectedReading = filteredReadings.find((reading) => reading.id === selectedReadingId) ?? null;

  // Other readings for the same asset as the selected one, and the full
  // per-asset series for the Trend tab -- both derived from the already-
  // fetched (unfiltered) `readings` list, the same "filter, don't
  // re-fetch" convention PM.jsx's own relatedPMRecords establishes.
  const relatedReadingsForSelected = selectedReading
    ? readings.filter((reading) => reading.id !== selectedReading.id && reading.equipmentTag === selectedReading.equipmentTag)
    : [];
  const assetReadingsForSelected = selectedReading
    ? readings.filter((reading) => reading.equipmentTag === selectedReading.equipmentTag)
    : [];

  // UI-D3.2 -- KPI strip: Total Readings, Assets Monitored, Leak Detected, In Review
  // Derived only from real loaded data, never fabricated.
  const distinctAssetsCount = useMemo(
    () => new Set(readings.map((r) => r.equipmentTag).filter(Boolean)).size,
    [readings]
  );
  const leakDetectedCount = useMemo(
    () => readings.filter((r) => r.leakDe || r.leakNde).length,
    [readings]
  );
  const inReviewCount = useMemo(
    () => readings.filter((r) => r.workflowStatus === "SUBMITTED").length,
    [readings]
  );

  const kpiItems = useMemo(
    () => [
      { label: "Loaded Readings", value: readings.length },
      { label: "Assets Monitored (Loaded)", value: distinctAssetsCount },
      {
        label: "Leak Detected (Loaded)",
        value: leakDetectedCount,
        tone: leakDetectedCount > 0 ? "critical" : "normal",
      },
      { label: "In Review (Loaded)", value: inReviewCount },
    ],
    [readings.length, distinctAssetsCount, leakDetectedCount, inReviewCount]
  );

  function handleClearReadingFilters() {
    setReadingSearch("");
    setReadingStatusFilter("ALL");
    setReadingLeakFilter("ALL");
    setReadingAreaFilter("ALL");
  }

  function handleViewAsset360(assetTag) {
    if (assetTag) {
      onNavigate?.("history", { assetTag });
    }
  }

  function handleViewSchedule(scheduleCode) {
    setView("schedules");
    setSelectedScheduleId(scheduleCode);
  }

  function selectReading(id) {
    setSelectedReadingId(id);
    setMobileRegistryCollapsed(true);
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
  // condition-monitoring-readings. The response is run through the exact
  // same mapConditionMonitoringReadingRecord() the real
  // getConditionMonitoringReadings() fetch path already uses.
  const [createError, setCreateError] = useState(null);

  async function handleCreateReading(formValues) {
    setCreateError(null);
    try {
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
      selectReading(newReading.id);
      setSuccessMessage(`Condition Monitoring reading ${newReading.id} created (DRAFT).`);
    } catch (err) {
      setCreateError(err.message);
    }
  }

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

  function handleAdHocReadingSaved(newReading) {
    setIsAdHocCreateModalOpen(false);
    setView("readings");
    selectReading(newReading.id);
    setSuccessMessage(`Condition Monitoring reading ${newReading.id} created (DRAFT).`);
  }

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

  async function handleUpdateSchedule(code, payload) {
    const result = await updateConditionMonitoringSchedule(code, payload);
    const updated = mapConditionMonitoringScheduleRecord(result.data);
    setSchedules((current) => current.map((schedule) => (schedule.id === code ? updated : schedule)));
    setSuccessMessage(`Condition Monitoring Schedule ${code} updated.`);
  }

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
    <div className="ltsa-open-design">
      <div className="cmon-page-header">
        <div>
          <h1 className="cmon-page-title">CONDITION MONITORING</h1>
          <p className="cmon-page-subtitle">Asset condition, readings, alerts and trend workspace</p>
        </div>
        <div className="cmon-page-actions">
          {canWriteMaintenance && view === "schedules" && (
            <button type="button" className="cmon-action-btn-secondary" onClick={() => setIsCreateScheduleModalOpen(true)}>
              + Create Schedule
            </button>
          )}
          {canWriteMaintenance && schedules.length > 0 && (
            <button type="button" className="cmon-action-btn-secondary" onClick={() => setIsCreateModalOpen(true)}>
              + Create Reading
            </button>
          )}
          {canWriteMaintenance && (
            <button type="button" className="cmon-action-btn-secondary" onClick={() => setIsAdHocCreateModalOpen(true)}>
              + Add Reading
            </button>
          )}
          {canWriteMaintenance && (
            <button type="button" className="cmon-action-btn-secondary" onClick={() => setIsBulkEditorOpen(true)}>
              Bulk Reading
            </button>
          )}
          {canWriteMaintenance && (
            <button type="button" className="cmon-action-btn-secondary" onClick={() => setIsExcelImportOpen(true)}>
              Import Excel
            </button>
          )}
        </div>
      </div>

      {!readingsLoading && !readingsError && <KpiStrip items={kpiItems} />}

      <div style={{ maxWidth: 1240, margin: "0 auto", padding: "0 32px" }}>
        <SuccessToast message={successMessage} onDismiss={() => setSuccessMessage(null)} />
      </div>
      {createError && (
        <p className="cmon-status-panel" role="alert" data-testid="cmon-create-error">
          {createError}
        </p>
      )}

      <div className="cmon-view-tabs" role="tablist">
        {VIEWS.map((item) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={item.key === view}
            className="cmon-view-tab"
            onClick={() => setView(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {view === "readings" && schedules.length === 0 && !schedulesLoading && (
        <p className="cmon-empty-banner">No active Condition Monitoring Schedule is available for this pump.</p>
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
            <p className="cmon-status-panel">Loading Condition Monitoring schedules...</p>
          ) : schedulesError ? (
            <p className="cmon-status-panel" role="alert">{schedulesError}</p>
          ) : (
            <div className="cmon-workspace-layout">
              <div className="cmon-workspace-registry">
                <ConditionMonitoringScheduleTable
                  schedules={filteredSchedules}
                  selectedId={selectedScheduleId}
                  onSelect={setSelectedScheduleId}
                />
              </div>

              <div className="cmon-workspace-detail">
                {selectedSchedule ? (
                  <>
                    <p className="cmon-selected-label">Selected Condition Monitoring Schedule</p>
                    <div className="cmon-detail-section">
                      <ConditionMonitoringScheduleDetailPanel
                        schedule={selectedSchedule}
                        onViewAsset360={handleViewAsset360}
                        canDelete={canDeleteRecords}
                        onDelete={handleDeleteSchedule}
                        canEdit={canWriteMaintenance}
                        onEdit={setEditingSchedule}
                      />
                    </div>
                  </>
                ) : (
                  // UI-D2C -- rendered here (not delegated to the frozen
                  // ConditionMonitoringScheduleDetailPanel.jsx's own dark
                  // EmptyState) so the "nothing selected" state matches
                  // this page's now-light surroundings, same pattern
                  // PM.jsx already establishes for its own empty state.
                  <div className="cmon-empty-state">
                    <p className="cmon-empty-title">No Condition Monitoring schedule selected</p>
                    <p className="cmon-empty-description">Select a schedule from the list to view its details.</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          <ConditionMonitoringReadingFilterBar
            searchValue={readingSearch}
            onSearchChange={setReadingSearch}
            statusFilter={readingStatusFilter}
            onStatusFilterChange={setReadingStatusFilter}
            leakFilter={readingLeakFilter}
            onLeakFilterChange={setReadingLeakFilter}
            areaFilter={readingAreaFilter}
            onAreaFilterChange={setReadingAreaFilter}
            areaOptions={readingAreaOptions}
            onClear={handleClearReadingFilters}
          />

          {readingsLoading ? (
            <p className="cmon-status-panel">Loading Condition Monitoring readings...</p>
          ) : readingsError ? (
            <p className="cmon-status-panel" role="alert">{readingsError}</p>
          ) : (
            <div className="cmon-workspace-layout">
              <div className="cmon-workspace-registry">
                <ConditionMonitoringReadingTable
                  readings={filteredReadings}
                  selectedId={selectedReadingId}
                  onSelect={selectReading}
                  mobileCollapsed={mobileRegistryCollapsed}
                  onExpand={() => setMobileRegistryCollapsed(false)}
                />
              </div>

              <div className="cmon-workspace-detail">
                {selectedReading ? (
                  <>
                    <p className="cmon-selected-label">Selected Condition Monitoring Reading</p>
                    <ConditionMonitoringOpenDesignView
                      reading={selectedReading}
                      relatedReadings={relatedReadingsForSelected}
                      assetReadings={assetReadingsForSelected}
                      onOpenAsset360={handleViewAsset360}
                      onViewSchedule={handleViewSchedule}
                      onBack={() => onNavigate?.("dashboard")}
                      onReportMeasuring={() => setReportReading(selectedReading)}
                    />
                    {reportReading?.id === selectedReading.id && (
                      <ConditionMonitoringReportMeasuring reading={reportReading} onClose={() => setReportReading(null)} />
                    )}

                    {/* Full measurement set + review workflow + Evidence --
                        ConditionMonitoringReadingDetailPanel.jsx itself is
                        untouched (same "complex RBAC review workflow stays
                        frozen" precedent as PMOccurrenceDetailPanel.jsx),
                        just given a light wrapper. Rendered only once a
                        reading is selected -- see the empty-state branch
                        below for why, same reasoning as the Schedules
                        view's own empty state fix. */}
                    <div className="cmon-detail-section">
                      <h3 className="cmon-detail-heading">Reading Detail</h3>
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
                  </>
                ) : (
                  // UI-D2C -- rendered here (not delegated to the frozen
                  // ConditionMonitoringReadingDetailPanel.jsx's own dark
                  // EmptyState) so the "nothing selected" state matches
                  // this page's now-light surroundings, same pattern
                  // PM.jsx already establishes for its own empty state.
                  <div className="cmon-empty-state">
                    <p className="cmon-empty-title">No Condition Monitoring reading selected</p>
                    <p className="cmon-empty-description">Select a reading from the list to view its details.</p>
                  </div>
                )}
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
