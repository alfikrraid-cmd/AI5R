import { useCallback, useEffect, useMemo, useState } from "react";
import { EmptyState, Panel } from "../../../design-system";
import PumpWorkspaceCommandPalette from "../components/PumpWorkspaceCommandPalette";
import PumpWorkspaceDrawer from "../components/PumpWorkspaceDrawer";
import PumpWorkspaceComingSoon from "../components/PumpWorkspaceComingSoon";
import {
  IconAlert,
  IconBox,
  IconCamera,
  IconCheck,
  IconClipboard,
  IconMoon,
  IconPen,
  IconSearch,
  IconShield,
  IconSun,
} from "../components/PumpWorkspaceIcons";
import {
  getPMOccurrences,
  getPMSchedules,
  getPump,
  getPumpSpareParts,
  getWorkOrder,
} from "../../../api/ai5rClient";
import { mapPMScheduleRecord } from "../utils/pmMapping";
import { mapWorkOrderRecord } from "../utils/workOrderMapping";
import { mapSparePartRecord } from "../utils/inventoryContextMapping";
import { statusLabel as woStatusLabel } from "../utils/workOrderStatus";
import "./MaintenanceHistory.css";
import WorkspaceShell from "../workspace/WorkspaceShell";
import { useWorkspaceTheme } from "../workspace/WorkspaceTheme";
import { useWorkspaceShortcuts } from "../workspace/WorkspaceShortcuts";
import "./PMWorkOrderWorkspace.css";

function safeList(promise) {
  return promise.catch(() => []);
}

function safeValue(promise) {
  return promise.catch(() => null);
}

// Real WorkOrder status vocabulary (OPEN/IN_PROGRESS/ON_HOLD/COMPLETED/
// CANCELLED, per workOrderStatus.js) mapped onto the approved design's
// 4-step lifecycle. There is no backend concept of "Menunggu Sign-Off"
// (Pending Sign-Off) at all -- no real event ever produces that state,
// consistent with the Design Review's own finding that Sign-Off/Approval
// has no backend yet. ON_HOLD/CANCELLED don't fit the 4 steps cleanly;
// both fall back to the nearest step with the real status label shown
// alongside it, never hidden.
const STEPS = ["OPEN", "IN_PROGRESS", "PENDING_SIGNOFF", "COMPLETED"];
const STEP_LABEL = {
  OPEN: "Dijadwalkan",
  IN_PROGRESS: "Sedang Dikerjakan",
  PENDING_SIGNOFF: "Menunggu Sign-Off",
  COMPLETED: "Selesai",
};

function stepIndexForStatus(status) {
  if (status === "COMPLETED") return 3;
  if (status === "IN_PROGRESS" || status === "ON_HOLD") return 1;
  return 0;
}

function statusSignalTier(status) {
  if (status === "COMPLETED") return "normal";
  if (status === "IN_PROGRESS" || status === "ON_HOLD") return "attention";
  return "neutral";
}

function StatusStepper({ status }) {
  const idx = stepIndexForStatus(status);

  return (
    <div className="stepper" data-od-id="wo-status-stepper">
      {STEPS.map((id, i) => {
        const state = i < idx ? "done" : i === idx ? "current" : "upcoming";
        return (
          <div className="step-item" key={id} data-state={state}>
            <span className="step-dot">{state === "done" ? <IconCheck width="9" height="9" /> : null}</span>
            <div className="step-label">{STEP_LABEL[id]}</div>
            {i === idx && (status === "ON_HOLD" || status === "CANCELLED") ? (
              <div className="step-meta">Actual status: {woStatusLabel(status)}</div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function CheckRow({ item }) {
  // Read-only: checklist completion is read from a real PM Occurrence
  // record, but no write-back API exists yet to toggle it from here (see
  // the Coming Soon note rendered below the list).
  return (
    <div className="check-row" data-checked={item.checked} data-od-id={`check-row-${item.id}`}>
      <span className="check-box" data-checked={item.checked} aria-hidden="true">
        <IconCheck width="12" height="12" />
      </span>
      <div className="check-body">
        <span className="check-title">{item.title}</span>
      </div>
    </div>
  );
}

/**
 * The PM Work Order Workspace (ITD-Frontend, PM Workspace) -- implements
 * DESIGN/LTSA/PM_WORKSPACE/pm-workspace.html for every section with a real
 * backend, and PumpWorkspaceComingSoon for every section without one.
 * Reuses, never duplicates: .pump-workspace-root tokens and every base
 * component class from MaintenanceHistory.css; PumpWorkspaceCommandPalette,
 * PumpWorkspaceDrawer, PumpWorkspaceComingSoon, and the shared icon set
 * (extended, not copied, with PM-specific icons) from the Pump Workspace
 * implementation.
 *
 * Real data composition (no field is fabricated):
 *   WorkOrder (getWorkOrder)            -> identity, status, due date
 *   Pump (getPump, via WorkOrder.equipmentTag) -> pump name/tag/area
 *   PM Occurrence (getPMOccurrences, matched by work_order_code)
 *     -> checklist_completion, pm_schedule_code
 *   PM Schedule (getPMSchedules, matched by pm_schedule_code, falling
 *     back to equipmentTag if no occurrence exists yet)
 *     -> checklist (required items), frequency, lastPerformed, nextDue,
 *        estimatedDurationHours, assignedTechnician
 *   Spare Parts (getPumpSpareParts, via equipmentTag) -> Required Parts
 *
 * No backend exists for: Safety Checklist, per-item measurements,
 * Required Tools, Photos, Attachments, Result, Recommendation, Sign-Off
 * (either party), or any write-back action (marking a checklist item
 * complete, saving a draft, submitting for sign-off) -- all render as
 * PumpWorkspaceComingSoon, never fabricated.
 */
export default function PMWorkOrderWorkspace({ navContext, onNavigate }) {
  const workOrderId = navContext?.workOrderId ?? null;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [workOrder, setWorkOrder] = useState(null);
  const [pump, setPump] = useState(null);
  const [pmSchedule, setPmSchedule] = useState(null);
  const [pmOccurrence, setPmOccurrence] = useState(null);
  const [spareParts, setSpareParts] = useState([]);

  const [theme, setTheme] = useWorkspaceTheme();
  const [drawerMode, setDrawerMode] = useState(null);
  const [toast, setToast] = useState(null);
  const [paletteOpen, setPaletteOpen] = useWorkspaceShortcuts();
  const [procFilter, setProcFilter] = useState("all");

  const showToast = useCallback((message) => {
    setToast(message);
    setTimeout(() => setToast(null), 2600);
  }, []);

  const showComingSoon = useCallback((label) => showToast(`${label} is not yet available.`), [showToast]);

  const scrollToId = useCallback((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    const y = el.getBoundingClientRect().top + window.pageYOffset - 84;
    window.scrollTo({ top: y, behavior: "smooth" });
  }, []);

  useEffect(() => {
    if (!workOrderId) {
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    getWorkOrder(workOrderId)
      .then((record) => mapWorkOrderRecord(record))
      .then((wo) =>
        Promise.all([
          safeValue(getPump(wo.equipmentTag)),
          safeList(getPMOccurrences()),
          safeList(getPMSchedules()).then((records) => records.map(mapPMScheduleRecord)),
          safeList(getPumpSpareParts(wo.equipmentTag).then((result) => (result?.spare_parts ?? []).map(mapSparePartRecord))),
        ]).then(([pumpRecord, occurrences, schedules, resolvedSpareParts]) => {
          if (!active) return;

          const occurrence = occurrences.find((o) => o.work_order_code === wo.id) ?? null;
          const schedule = occurrence
            ? schedules.find((s) => s.id === occurrence.pm_schedule_code) ?? null
            : schedules.find((s) => s.equipmentTag === wo.equipmentTag) ?? null;

          setWorkOrder(wo);
          setPump(pumpRecord);
          setPmOccurrence(occurrence);
          setPmSchedule(schedule);
          setSpareParts(resolvedSpareParts);
        })
      )
      .catch(() => {
        if (active) setError("PM Work Order could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [workOrderId]);

  const procedureItems = useMemo(() => {
    const required = pmSchedule?.checklist ?? [];
    const completed = new Set(pmOccurrence?.checklist_completion ?? []);
    return required.map((title, index) => ({ id: index, title, checked: completed.has(title) }));
  }, [pmSchedule, pmOccurrence]);

  const procDone = procedureItems.filter((i) => i.checked).length;
  const shownProcedure = useMemo(() => {
    if (procFilter === "done") return procedureItems.filter((i) => i.checked);
    if (procFilter === "pending") return procedureItems.filter((i) => !i.checked);
    return procedureItems;
  }, [procedureItems, procFilter]);

  const actions = useMemo(
    () => [
      { id: "tandai-langkah", label: "Tandai Langkah Berikutnya Selesai", hint: "Prosedur", icon: IconClipboard, run: () => showComingSoon("Marking a checklist item complete") },
      { id: "checklist-prosedur", label: "Lihat Checklist Prosedur", hint: "Scroll", icon: IconShield, run: () => scrollToId("procedure-section") },
      { id: "tambah-foto", label: "Tambah Foto", hint: "Dokumentasi", icon: IconCamera, run: () => showComingSoon("Photo capture") },
      { id: "lihat-onderdil", label: "Lihat Onderdil", hint: "Scroll", icon: IconBox, run: () => scrollToId("parts-section") },
      { id: "kirim-signoff", label: "Kirim untuk Sign-Off", hint: "Belum tersedia", icon: IconAlert, run: () => showComingSoon("Sign-off submission") },
    ],
    [showComingSoon, scrollToId]
  );

  if (!workOrderId) {
    return (
      <div className="pump-workspace-root" data-theme={theme}>
        <div className="pump-workspace-picker">
          <EmptyState
            title="No PM Work Order selected"
            description="Open a Preventive Maintenance work order from the Work Order Workspace to view it here."
          />
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="pump-workspace-root" data-theme={theme}>
        <Panel>
          <p>Loading PM Work Order...</p>
        </Panel>
      </div>
    );
  }

  if (error || !workOrder) {
    return (
      <div className="pump-workspace-root" data-theme={theme}>
        <Panel>
          <p role="alert">{error ?? "PM Work Order not found."}</p>
        </Panel>
      </div>
    );
  }

  const tier = statusSignalTier(workOrder.status);

  return (
    <div className="pump-workspace-root" data-theme={theme}>
      <div className="chrome-bar" data-od-id="chrome-bar">
        <div className="chrome-inner">
          <div className="crumb">
            <a
              href="#"
              onClick={(e) => {
                e.preventDefault();
                onNavigate?.("history", { assetTag: workOrder.equipmentTag });
              }}
              data-od-id="crumb-pump-link"
            >
              {workOrder.equipmentTag}
            </a>
            <span className="sep">›</span>
            <b>PM {workOrder.id}</b>
          </div>
          <div className="chrome-right">
            <button type="button" className="cmdk-trigger" data-od-id="cmdk-trigger" onClick={() => setPaletteOpen(true)}>
              <IconSearch width="14" height="14" /> Actions <kbd>⌘K</kbd>
            </button>
            <button
              type="button"
              className="icon-btn"
              data-od-id="theme-toggle"
              aria-label="Toggle theme"
              onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            >
              {theme === "dark" ? <IconSun width="15" height="15" /> : <IconMoon width="15" height="15" />}
            </button>
          </div>
        </div>
      </div>

      <div className="workspace-grid">
        <main className="object-column">
          <section className="identity" data-od-id="identity-section">
            <span className="eyebrow">Preventive Maintenance · {workOrder.id}</span>
            <h1 style={{ marginTop: "10px" }}>{pump?.name ?? workOrder.equipmentTag}</h1>
            <div className="identity-meta">
              <span className="mono">{workOrder.equipmentTag}</span>
              {pump?.area ? (
                <>
                  <span className="dot" />
                  <span>{pump.area}</span>
                </>
              ) : null}
            </div>
            <div className="identity-status">
              <span className={`status-signal ${tier}`}>
                <span className="dot-lg" /> {woStatusLabel(workOrder.status)}
              </span>
              {workOrder.dueDate ? (
                <span className="running-line">
                  <span className="dot-sm" /> Due {workOrder.dueDate}
                </span>
              ) : null}
            </div>
          </section>

          <section className="assessment-section" id="safety-section" data-od-id="safety-section">
            <span className="eyebrow">Checklist Keselamatan</span>
            <PumpWorkspaceComingSoon label="Safety Checklist" />
          </section>

          <section className="assessment-section" id="procedure-section" data-od-id="procedure-section">
            <div className="section-head">
              <span className="eyebrow">Prosedur &amp; Checklist Kerja</span>
              <div className="timeline-filter">
                {[
                  { id: "all", label: "Semua" },
                  { id: "done", label: "Selesai" },
                  { id: "pending", label: "Tertunda" },
                ].map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    className="tf-chip"
                    data-active={procFilter === f.id}
                    onClick={() => setProcFilter(f.id)}
                    data-od-id={`proc-filter-${f.id}`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>
            {procedureItems.length === 0 ? (
              <p className="field-unavailable">No PM Schedule checklist found for this work order.</p>
            ) : (
              <>
                <div className="progress-line" style={{ marginBottom: "var(--space-4)" }}>
                  <b>{procDone}</b> dari {procedureItems.length} langkah selesai
                </div>
                <div className="checklist">
                  {shownProcedure.map((item) => (
                    <CheckRow key={item.id} item={item} />
                  ))}
                </div>
                <PumpWorkspaceComingSoon label="Marking items complete from this screen" />
              </>
            )}
          </section>

          <section className="assessment-section" id="photos-section" data-od-id="photos-section">
            <span className="eyebrow">Foto Dokumentasi</span>
            <PumpWorkspaceComingSoon label="Photos" />
          </section>

          <section className="assessment-section" id="attachments-section" data-od-id="attachments-section">
            <span className="eyebrow">Lampiran</span>
            <PumpWorkspaceComingSoon label="Attachments" />
          </section>

          <section className="assessment-section" id="result-section" data-od-id="result-section">
            <span className="eyebrow">Hasil Pekerjaan</span>
            <PumpWorkspaceComingSoon label="Result" />
          </section>

          <section className="assessment-section" id="recommendation-section" data-od-id="recommendation-section">
            <span className="eyebrow">Rekomendasi</span>
            <PumpWorkspaceComingSoon label="Recommendation" />
          </section>

          <section className="assessment-section" id="signoff-section" data-od-id="signoff-section">
            <span className="eyebrow">Tanda Tangan / Sign Off</span>
            <PumpWorkspaceComingSoon label="Sign-Off" />
          </section>
        </main>

        <aside className="inspector-rail" data-od-id="inspector-rail">
          <div className="rail-section" data-od-id="wo-status-section">
            <h3 className="rail-title">Status Work Order</h3>
            <StatusStepper status={workOrder.status} />
          </div>

          <div className="rail-section" data-od-id="engineer-section">
            <h3 className="rail-title">Teknisi Ditugaskan</h3>
            <div className="info-row">
              <span className="k">Nama</span>
              <span className="v">{workOrder.assignedTechnician || pmSchedule?.assignedTechnician || <span className="field-unavailable">Not available</span>}</span>
            </div>
            <div className="info-row">
              <span className="k">Peran</span>
              <span className="v field-unavailable">Not available</span>
            </div>
            <div className="info-row">
              <span className="k">Sertifikasi</span>
              <span className="v field-unavailable">Not available</span>
            </div>
          </div>

          <div className="rail-section" data-od-id="schedule-section">
            <h3 className="rail-title">Jadwal PM</h3>
            {pmSchedule ? (
              <>
                <div className="info-row">
                  <span className="k">Frekuensi</span>
                  <span className="v">{pmSchedule.frequency}</span>
                </div>
                <div className="info-row">
                  <span className="k">PM Terakhir</span>
                  <span className="v tabular">{pmSchedule.lastPerformed ?? "—"}</span>
                </div>
                <div className="info-row">
                  <span className="k">Jatuh Tempo Berikutnya</span>
                  <span className="v tabular">{pmSchedule.nextDue ?? "—"}</span>
                </div>
                <div className="info-row">
                  <span className="k">Durasi</span>
                  <span className="v">{pmSchedule.estimatedDurationHours ? `${pmSchedule.estimatedDurationHours} jam` : "—"}</span>
                </div>
              </>
            ) : (
              <p className="field-unavailable">No PM Schedule matched to this work order.</p>
            )}
          </div>

          <div className="rail-section" id="parts-section" data-od-id="parts-section">
            <h3 className="rail-title">Onderdil Dibutuhkan</h3>
            {spareParts.length === 0 ? (
              <p className="field-unavailable">No spare parts recorded.</p>
            ) : (
              spareParts.map((part) => (
                <div className="part-item" key={`${part.sealCode}-${part.partName}`}>
                  <div className="part-row">
                    <span className="part-name">{part.partName}</span>
                    <span className={`stock-flag ${part.availability > 0 ? "ok" : "low"}`}>
                      {part.availability != null ? `Qty ${part.availability}` : "Unknown"}
                    </span>
                  </div>
                  <div className="part-meta">{part.location ?? "—"}</div>
                </div>
              ))
            )}
          </div>

          <div className="rail-section" data-od-id="tools-section">
            <h3 className="rail-title">Alat Dibutuhkan</h3>
            <PumpWorkspaceComingSoon label="Required Tools" />
          </div>
        </aside>
      </div>

      <div className="action-bar" data-od-id="action-bar">
        <div className="action-bar-inner">
          <div className="action-bar-status">
            <span className="label">{woStatusLabel(workOrder.status)}</span>
            <span className="meta">{procDone}/{procedureItems.length} prosedur selesai</span>
          </div>
          <div className="action-bar-actions">
            <button type="button" className="btn-link" onClick={() => showComingSoon("Saving a draft")} data-od-id="save-draft-btn">
              Simpan sebagai Draft
            </button>
            <button type="button" className="btn-primary" onClick={() => showComingSoon("Sign-off submission")} data-od-id="submit-signoff-btn">
              <IconPen width="14" height="14" /> Kirim untuk Sign-Off
            </button>
          </div>
        </div>
      </div>

      <PumpWorkspaceCommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} actions={actions} pumpTag={workOrder.id} />

      <PumpWorkspaceDrawer open={drawerMode === "signoff"} onClose={() => setDrawerMode(null)} title="Tanda Tangan Engineer">
        <PumpWorkspaceComingSoon label="Sign-Off" />
      </PumpWorkspaceDrawer>

      <div className="toast" data-open={!!toast} data-od-id="toast">
        <IconCheck width="14" height="14" /> {toast}
      </div>
    </div>
  );
}
