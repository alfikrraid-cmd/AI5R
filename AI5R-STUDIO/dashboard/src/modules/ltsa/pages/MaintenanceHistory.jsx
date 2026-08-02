import { useCallback, useEffect, useMemo, useState } from "react";
import { EmptyState, PageHeader, Panel } from "../../../design-system";
import AssetSelector from "../components/AssetSelector";
import PumpWorkspaceTimeline from "../components/PumpWorkspaceTimeline";
import PumpWorkspaceCommandPalette from "../components/PumpWorkspaceCommandPalette";
import PumpWorkspaceDrawer from "../components/PumpWorkspaceDrawer";
import PumpWorkspaceComingSoon from "../components/PumpWorkspaceComingSoon";
import { IconAlert, IconBox, IconCheck, IconDrawing, IconHistory, IconMoon, IconSearch, IconSun, IconWrench } from "../components/PumpWorkspaceIcons";
import {
  getCMReports,
  getConditionMonitoringReadings,
  getConditionMonitoringSchedules,
  getMaintenanceHistory,
  getPMOccurrences,
  getPMSchedules,
  getPumpConditionMonitoringFlag,
  getPumpLastCM,
  getPumpLastPM,
  getPumpOpenWorkOrders,
  getPumpSpareParts,
  getPumps,
  getWorkOrders,
} from "../../../api/ai5rClient";
import { mapPumpRecord } from "../utils/pumpMapping";
import { mapPMScheduleRecord } from "../utils/pmMapping";
import { mapWorkOrderRecord } from "../utils/workOrderMapping";
import { mapSparePartRecord } from "../utils/inventoryContextMapping";
import {
  buildAssetEventStream,
  mapCMReportToEvent,
  mapConditionMonitoringReadingToEvent,
  mapMaintenanceHistoryToEvent,
  mapPMOccurrenceToEvent,
  mapWorkOrderToEvent,
} from "../utils/maintenanceHistory";
import { toWorkspaceTimelineItem } from "../utils/pumpWorkspaceEventTaxonomy";
import "./MaintenanceHistory.css";

const RUNNING_LABEL = {
  RUNNING: "Running",
  STANDBY: "Standby",
  MAINTENANCE: "In Maintenance",
  FAULT: "Fault",
};

// Best-effort per source: one gateway being unavailable should not block
// the rest of the page, the same resilience convention
// MWO-MAINTINT-001's get_pump_last_pm() already established server-side.
function safeList(promise) {
  return promise.catch(() => []);
}

function safeValue(promise) {
  return promise.catch(() => null);
}

function stockFlag(part) {
  if (part.availability == null) {
    return { className: "unknown", label: "Unknown" };
  }
  if (part.availability <= 0) {
    return { className: "low", label: "Stok Habis" };
  }
  return { className: "ok", label: `Qty ${part.availability}` };
}

/**
 * The Pump Workspace (ITD-Frontend, Phase 1 -- approved with modification):
 * implements DESIGN/LTSA/PUMP_WORKSPACE/pump-workspace.html exactly for
 * every capability with a real backend, and an explicit "Coming Soon" empty
 * state (never fabricated data) for AI Assessment, Drawing/P&ID, and CM
 * manual submission, none of which have a backend yet. Data layer is
 * unchanged from the prior Asset 360 view (APP-ASSET360-001, per
 * ADR-ASSET360-001): same APIs, same event stream composition. `navContext`
 * (from LTSAWorkspace's extended onNavigate) still pre-selects an asset via
 * `{ assetTag }`.
 */
export default function MaintenanceHistory({ onNavigate, navContext }) {
  const [pumps, setPumps] = useState([]);
  const [pumpsLoading, setPumpsLoading] = useState(true);

  const [selectedTag, setSelectedTag] = useState(null);
  const [assetLoading, setAssetLoading] = useState(false);
  const [assetError, setAssetError] = useState(null);

  const [eventStream, setEventStream] = useState([]);
  const [spareParts, setSpareParts] = useState([]);
  const [summary, setSummary] = useState(null);

  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem("ltsa-theme") || "light";
    } catch {
      return "light";
    }
  });
  const [drawerMode, setDrawerMode] = useState(null);
  const [toast, setToast] = useState(null);
  const [cmReason, setCmReason] = useState("");
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem("ltsa-theme", theme);
    } catch {
      // localStorage unavailable (e.g. private browsing) -- theme still
      // applies for this session via the data-theme attribute below.
    }
  }, [theme]);

  const showToast = useCallback((message) => {
    setToast(message);
    setTimeout(() => setToast(null), 2600);
  }, []);

  const showComingSoon = useCallback(
    (label) => showToast(`${label} is not yet available.`),
    [showToast]
  );

  const scrollToId = useCallback((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    const y = el.getBoundingClientRect().top + window.pageYOffset - 84;
    window.scrollTo({ top: y, behavior: "smooth" });
  }, []);

  useEffect(() => {
    let active = true;

    getPumps()
      .then((records) => records.map(mapPumpRecord))
      .then((mapped) => {
        if (active) {
          setPumps(mapped);
        }
      })
      .catch(() => {
        if (active) {
          setPumps([]);
        }
      })
      .finally(() => {
        if (active) {
          setPumpsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  function handleSelectAsset(tag) {
    setSelectedTag(tag);
  }

  // Deep-link entry point: PumpDetailPanel's "View History" and
  // RecentActivityFeed's rows both navigate here with { assetTag }, per
  // ADR-ASSET360-001's Required Frontend Changes. Gated on !pumpsLoading
  // per the same reasoning this page already documented before Phase 1.
  useEffect(() => {
    if (navContext?.assetTag && !pumpsLoading) {
      handleSelectAsset(navContext.assetTag);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navContext, pumpsLoading]);

  useEffect(() => {
    if (!selectedTag) {
      setEventStream([]);
      setSpareParts([]);
      setSummary(null);
      return;
    }

    let active = true;
    setAssetLoading(true);
    setAssetError(null);

    const pump = pumps.find((candidate) => candidate.tag === selectedTag) ?? null;

    Promise.all([
      safeList(getWorkOrders()).then((records) => records.map(mapWorkOrderRecord).map(mapWorkOrderToEvent)),
      safeList(getMaintenanceHistory()).then((records) => records.map(mapMaintenanceHistoryToEvent)),
      safeList(getCMReports()).then((records) => records.map(mapCMReportToEvent)),
      safeList(getPMOccurrences()).then((records) => records.map(mapPMOccurrenceToEvent)),
      safeList(getConditionMonitoringReadings()).then((records) =>
        records.map(mapConditionMonitoringReadingToEvent)
      ),
      safeList(getPMSchedules()).then((records) => records.map(mapPMScheduleRecord)),
      safeList(getConditionMonitoringSchedules()),
      safeValue(getPumpLastPM(selectedTag)),
      safeValue(getPumpLastCM(selectedTag)),
      safeValue(getPumpConditionMonitoringFlag(selectedTag)),
      safeValue(getPumpOpenWorkOrders(selectedTag)),
      safeList(getPumpSpareParts(selectedTag).then((result) => (result?.spare_parts ?? []).map(mapSparePartRecord))),
    ])
      .then(
        ([
          woEvents,
          mhEvents,
          cmEvents,
          pmEvents,
          cmonEvents,
          allPmSchedules,
          allConditionMonitoringSchedules,
          lastPmResult,
          lastCmResult,
          conditionMonitoringFlagResult,
          openWorkOrdersResult,
          resolvedSpareParts,
        ]) => {
          if (!active) {
            return;
          }

          const allEvents = [...woEvents, ...mhEvents, ...cmEvents, ...pmEvents, ...cmonEvents];
          setEventStream(buildAssetEventStream(allEvents, selectedTag));
          setSpareParts(resolvedSpareParts);
          void allPmSchedules;
          void allConditionMonitoringSchedules;

          setSummary({
            pump: pump?.name,
            tag: selectedTag,
            area: pump?.area,
            status: pump?.status,
            sealType: pump?.seal,
            lastPM: lastPmResult?.last_pm ?? null,
            lastCM: lastCmResult?.last_cm ?? null,
            conditionMonitoringFlag: conditionMonitoringFlagResult,
            openWorkOrders: (openWorkOrdersResult?.data ?? []).length,
          });
        }
      )
      .catch(() => {
        if (active) {
          setAssetError("Asset history could not be loaded.");
        }
      })
      .finally(() => {
        if (active) {
          setAssetLoading(false);
        }
      });

    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTag]);

  useEffect(() => {
    function onKeyDown(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(true);
      } else if (event.key === "Escape") {
        setPaletteOpen(false);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const timelineItems = useMemo(() => eventStream.map(toWorkspaceTimelineItem), [eventStream]);

  const actions = useMemo(
    () => [
      { id: "mulai-pm", label: "Mulai PM", hint: "Preventive maintenance", icon: IconWrench, run: () => showComingSoon("Mulai PM") },
      { id: "lihat-riwayat", label: "Lihat Riwayat", hint: "Scroll ke history", icon: IconHistory, run: () => scrollToId("timeline-section") },
      { id: "buka-drawing", label: "Buka Drawing", hint: "P&ID", icon: IconDrawing, run: () => setDrawerMode("drawing") },
      { id: "lihat-spare", label: "Lihat Spare", hint: "Scroll ke inventory", icon: IconBox, run: () => scrollToId("inventory-section") },
      { id: "ajukan-cm", label: "Ajukan CM", hint: "Corrective maintenance", icon: IconAlert, run: () => setDrawerMode("cm") },
    ],
    [showComingSoon, scrollToId]
  );

  return (
    <div className="pump-workspace-root" data-theme={theme}>
      {!selectedTag ? (
        <div className="pump-workspace-picker">
          <PageHeader title="Pump Workspace" subtitle="LTSA Engineering — Asset 360" />
          {pumpsLoading ? (
            <Panel>
              <p>Loading assets...</p>
            </Panel>
          ) : (
            <AssetSelector
              assets={pumps.map((pump) => ({ tag: pump.tag, name: pump.name }))}
              selectedTag={selectedTag}
              onSelect={handleSelectAsset}
            />
          )}
          <EmptyState
            title="No pump selected"
            description="Select a pump above to open its workspace."
          />
        </div>
      ) : (
        <>
          <div className="chrome-bar" data-od-id="chrome-bar">
            <div className="chrome-inner">
              <div className="crumb">
                <span>Pumps</span>
                <span className="sep">›</span>
                <b>{selectedTag}</b>
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

          {assetLoading ? (
            <Panel>
              <p>Loading asset history...</p>
            </Panel>
          ) : assetError ? (
            <Panel>
              <p role="alert">{assetError}</p>
            </Panel>
          ) : (
            <div className="workspace-grid">
              <main className="object-column">
                <section className="identity" data-od-id="identity-section">
                  <h1>{summary?.pump ?? selectedTag}</h1>
                  <div className="identity-meta">
                    <span className="mono">{summary?.tag}</span>
                    {summary?.area ? (
                      <>
                        <span className="dot" />
                        <span>{summary.area}</span>
                      </>
                    ) : null}
                  </div>
                  <div className="identity-status">
                    <span className="status-signal unavailable">
                      <span className="dot-lg" /> Reliability assessment: Coming Soon
                    </span>
                    {summary?.status ? (
                      <span className="running-line">
                        <span className="dot-sm" /> {RUNNING_LABEL[summary.status] ?? summary.status}
                      </span>
                    ) : null}
                  </div>
                </section>

                <section className="assessment-section" data-od-id="assessment-section">
                  <span className="eyebrow">Reliability Assessment</span>
                  <PumpWorkspaceComingSoon label="AI Assessment" />
                  <div className="assessment-footer">
                    <button
                      type="button"
                      className="btn-primary"
                      data-od-id="cta-schedule-inspection"
                      onClick={() => showComingSoon("Jadwalkan Inspeksi")}
                    >
                      <IconCheck width="15" height="15" /> Jadwalkan Inspeksi
                    </button>
                    <button type="button" className="btn-link" data-od-id="cta-ajukan-cm-secondary" onClick={() => setDrawerMode("cm")}>
                      Ajukan CM manual →
                    </button>
                  </div>
                </section>

                <PumpWorkspaceTimeline items={timelineItems} />
              </main>

              <aside className="inspector-rail" data-od-id="inspector-rail">
                <div className="rail-section" data-od-id="seal-section">
                  <h3 className="rail-title">Mechanical Seal</h3>
                  <div className="info-row">
                    <span className="k">Model</span>
                    <span className="v mono">{summary?.sealType || <span className="field-unavailable">Not available</span>}</span>
                  </div>
                  <div className="info-row">
                    <span className="k">Manufacturer</span>
                    <span className="v field-unavailable">Not available</span>
                  </div>
                  <div className="info-row">
                    <span className="k">Material</span>
                    <span className="v field-unavailable">Not available</span>
                  </div>
                  <div className="info-row">
                    <span className="k">Installed</span>
                    <span className="v field-unavailable">Not available</span>
                  </div>
                  <div className="info-row">
                    <span className="k">Operating Hours</span>
                    <span className="v field-unavailable">Not available</span>
                  </div>
                  <div className="info-row">
                    <span className="k">Status</span>
                    <span className="v field-unavailable">Not available</span>
                  </div>
                </div>

                <div className="rail-section" id="inventory-section" data-od-id="inventory-section">
                  <h3 className="rail-title">Related Spare Parts</h3>
                  {spareParts.length === 0 ? (
                    <p className="field-unavailable">No spare parts recorded.</p>
                  ) : (
                    spareParts.map((part) => {
                      const flag = stockFlag(part);
                      return (
                        <div className="part-item" key={`${part.sealCode}-${part.partName}`}>
                          <div className="part-row">
                            <span className="part-name">{part.partName}</span>
                            <span className={`stock-flag ${flag.className}`}>{flag.label}</span>
                          </div>
                          <div className="part-meta">
                            {part.location ?? "—"} · Min. stok {part.minimumStock ?? "—"}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

                <div className="rail-section" data-od-id="drawing-section">
                  <h3 className="rail-title">Drawing</h3>
                  <div className="drawing-thumb">
                    <IconDrawing width="26" height="26" />
                  </div>
                  <PumpWorkspaceComingSoon label="Drawing" />
                  <button type="button" className="btn-link" style={{ marginTop: "8px" }} data-od-id="open-drawing-btn" onClick={() => setDrawerMode("drawing")}>
                    Buka Drawing →
                  </button>
                </div>
              </aside>
            </div>
          )}

          <PumpWorkspaceCommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} actions={actions} pumpTag={selectedTag} />

          <PumpWorkspaceDrawer open={drawerMode === "drawing"} onClose={() => setDrawerMode(null)} title="P&ID Drawing">
            <div className="drawing-thumb" style={{ aspectRatio: "3/4" }}>
              <IconDrawing width="36" height="36" />
            </div>
            <PumpWorkspaceComingSoon label="Drawing" />
          </PumpWorkspaceDrawer>

          <PumpWorkspaceDrawer open={drawerMode === "cm"} onClose={() => setDrawerMode(null)} title="Ajukan Corrective Maintenance">
            <p>Jelaskan kondisi yang ditemukan pada {selectedTag}.</p>
            <textarea
              className="cm-input"
              placeholder="cth. Getaran radial meningkat, suara tidak normal pada sisi DE..."
              value={cmReason}
              onChange={(event) => setCmReason(event.target.value)}
              data-od-id="cm-reason-input"
            />
            <PumpWorkspaceComingSoon label="CM manual submission" />
            <button
              type="button"
              className="btn-primary"
              style={{ marginTop: "12px" }}
              disabled={!cmReason.trim()}
              onClick={() => showComingSoon("Ajukan CM")}
            >
              Kirim Pengajuan
            </button>
          </PumpWorkspaceDrawer>

          <div className="toast" data-open={!!toast} data-od-id="toast">
            <IconCheck width="14" height="14" /> {toast}
          </div>
        </>
      )}
    </div>
  );
}
