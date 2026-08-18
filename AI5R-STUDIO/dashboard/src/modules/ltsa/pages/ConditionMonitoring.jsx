import { useEffect, useMemo, useState } from "react";
import { Button, PageHeader, Panel, Tabs } from "../../../design-system";
import ConditionMonitoringScheduleFilterBar from "../components/ConditionMonitoringScheduleFilterBar";
import ConditionMonitoringScheduleTable from "../components/ConditionMonitoringScheduleTable";
import ConditionMonitoringScheduleDetailPanel from "../components/ConditionMonitoringScheduleDetailPanel";
import ConditionMonitoringReadingFilterBar from "../components/ConditionMonitoringReadingFilterBar";
import ConditionMonitoringReadingTable from "../components/ConditionMonitoringReadingTable";
import ConditionMonitoringReadingDetailPanel from "../components/ConditionMonitoringReadingDetailPanel";
import CreateConditionMonitoringReadingModal from "../components/CreateConditionMonitoringReadingModal";
import SuccessToast from "../components/SuccessToast";
import {
  getConditionMonitoringReadings, getConditionMonitoringSchedules, createConditionMonitoringReading,
} from "../../../api/ai5rClient";
import {
  mapConditionMonitoringReadingRecord,
  mapConditionMonitoringScheduleRecord,
  withResolvedArea,
} from "../utils/conditionMonitoringMapping";
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
  const [successMessage, setSuccessMessage] = useState(null);

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
  useEffect(() => {
    if (navContext?.selectId) {
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
      const result = await createConditionMonitoringReading({
        conditionMonitoringScheduleCode: formValues.scheduleCode,
        assetCode: formValues.equipmentTag,
        readingDate: formValues.readingDate || null,
        measurements: {
          mechseal_temp_de: formValues.mechsealTempDe,
          mechseal_temp_nde: formValues.mechsealTempNde,
          mechanical_seal_leak_de: formValues.leakDe,
          mechanical_seal_leak_nde: formValues.leakNde,
          suction_temp: formValues.suctionTemp,
          discharge_temp: formValues.dischargeTemp,
          pump_operating_state: formValues.pumpOperatingState,
        },
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

  return (
    <div>
      <PageHeader
        title="Condition Monitoring"
        subtitle="LTSA Engineering — Condition Monitoring Registry"
        actions={<Button onClick={() => setIsCreateModalOpen(true)}>+ Create Reading</Button>}
      />

      <SuccessToast message={successMessage} onDismiss={() => setSuccessMessage(null)} />
      {createError && (
        <p className="confidence-label" style={{ color: "var(--color-danger, #d33)" }} data-testid="cmon-create-error">
          {createError}
        </p>
      )}

      <Tabs items={VIEWS} activeKey={view} onChange={setView} />

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
    </div>
  );
}
