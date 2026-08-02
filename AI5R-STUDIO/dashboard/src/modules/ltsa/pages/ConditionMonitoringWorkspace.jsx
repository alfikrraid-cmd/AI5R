import { useCallback, useEffect, useMemo, useState } from "react";
import AssetSelector from "../components/AssetSelector";
import PumpWorkspaceCommandPalette from "../components/PumpWorkspaceCommandPalette";
import PumpWorkspaceComingSoon from "../components/PumpWorkspaceComingSoon";
import PumpWorkspaceDrawer from "../components/PumpWorkspaceDrawer";
import PumpWorkspaceTimeline from "../components/PumpWorkspaceTimeline";
import { IconAlert, IconBox, IconHistory, IconMoon, IconSearch, IconSun, IconWrench } from "../components/PumpWorkspaceIcons";
import { getConditionMonitoringReadings, getConditionMonitoringSchedules, getPumps } from "../../../api/ai5rClient";
import { mapPumpRecord } from "../utils/pumpMapping";
import { mapConditionMonitoringReadingRecord, mapConditionMonitoringScheduleRecord } from "../utils/conditionMonitoringMapping";
import "./MaintenanceHistory.css";
import "./ConditionMonitoringWorkspace.css";
import WorkspaceShell from "../workspace/WorkspaceShell";
import { useWorkspaceTheme } from "../workspace/WorkspaceTheme";
import { useWorkspaceShortcuts } from "../workspace/WorkspaceShortcuts";
import { useWorkspaceDrawer } from "../workspace/WorkspaceDrawer";

const unavailable = (label) => <PumpWorkspaceComingSoon label={label} />;
const fmt = (value, suffix = "") => value == null || value === "" ? "Unavailable" : `${value}${suffix}`;

function readingItems(reading) {
  if (!reading) return [];
  return [
    ["Flushing temperature DE", reading.flushingTempDe, " C"], ["Flushing temperature NDE", reading.flushingTempNde, " C"],
    ["Mechanical seal temperature DE", reading.mechsealTempDe, " C"], ["Mechanical seal temperature NDE", reading.mechsealTempNde, " C"],
    ["Suction temperature", reading.suctionTemp, " C"], ["Discharge temperature", reading.dischargeTemp, " C"],
    ["Leakage DE", reading.leakDe == null ? null : reading.leakDe ? "Observed" : "Not observed", ""],
    ["Leakage NDE", reading.leakNde == null ? null : reading.leakNde ? "Observed" : "Not observed", ""],
  ];
}

export default function ConditionMonitoringWorkspace({ navContext, onNavigate }) {
  const [pumps, setPumps] = useState([]);
  const [selectedTag, setSelectedTag] = useState(navContext?.assetTag ?? null);
  const [readings, setReadings] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [paletteOpen, setPaletteOpen] = useWorkspaceShortcuts();
  const { drawer, openDrawer: setDrawer } = useWorkspaceDrawer();
  const [theme, setTheme] = useWorkspaceTheme();
  useEffect(() => {
    let active = true;
    Promise.all([
      getPumps().then((items) => items.map(mapPumpRecord)).catch(() => []),
      getConditionMonitoringReadings().then((items) => items.map(mapConditionMonitoringReadingRecord)).catch(() => []),
      getConditionMonitoringSchedules().then((items) => items.map(mapConditionMonitoringScheduleRecord)).catch(() => []),
    ]).then(([pumpItems, readingItems, scheduleItems]) => {
      if (!active) return;
      setPumps(pumpItems); setReadings(readingItems); setSchedules(scheduleItems); setLoading(false);
      if (!selectedTag && pumpItems.length === 1) setSelectedTag(pumpItems[0].tag);
    });
    return () => { active = false; };
  }, []);

  const pump = pumps.find((item) => item.tag === selectedTag) ?? null;
  const pumpReadings = useMemo(() => readings.filter((item) => item.equipmentTag === selectedTag).sort((a, b) => String(b.readingDate).localeCompare(String(a.readingDate))), [readings, selectedTag]);
  const latest = pumpReadings[0] ?? null;
  const schedule = schedules.find((item) => item.equipmentTag === selectedTag) ?? null;
  const timeline = useMemo(() => pumpReadings.map((item) => ({ id: item.id, tier: item.leakDe || item.leakNde ? "attention" : "normal", tag: "Reading", title: `Condition monitoring reading ${item.id}`, date: item.readingDate })), [pumpReadings]);
  const showDrawer = useCallback((label) => setDrawer(label), []);
  const actions = useMemo(() => [
    { id: "timeline", label: "View measurement timeline", hint: "Observation", icon: IconHistory, run: () => document.getElementById("timeline-section")?.scrollIntoView({ behavior: "smooth" }) },
    { id: "thresholds", label: "View thresholds", hint: "Unavailable", icon: IconAlert, run: () => showDrawer("Thresholds") },
    { id: "evidence", label: "View evidence", hint: "Unavailable", icon: IconBox, run: () => showDrawer("Evidence") },
    { id: "recommendation", label: "View recommendation", hint: "Unavailable", icon: IconWrench, run: () => showDrawer("Recommendation") },
  ], [showDrawer]);

  return <WorkspaceShell className="cmon-workspace-root" theme={theme}>
    <header className="chrome-bar"><div className="chrome-inner"><div className="crumb"><span>LTSA</span><span className="sep">/</span><span>Condition Monitoring</span><span className="sep">/</span><b>{pump?.tag ?? "Observation"}</b></div><div className="chrome-right"><button type="button" className="cmdk-trigger" onClick={() => setPaletteOpen(true)}><IconSearch width="14" height="14" /> Actions <kbd>Ctrl K</kbd></button><button type="button" className="icon-btn" onClick={() => setTheme(theme === "light" ? "dark" : "light")} aria-label="Toggle theme">{theme === "light" ? <IconMoon width="16" height="16" /> : <IconSun width="16" height="16" />}</button></div></div></header>
    <div className="workspace-shell"><AssetSelector assets={pumps} selectedTag={selectedTag} onSelect={setSelectedTag} />
      {loading ? <div className="workspace-empty">Loading condition monitoring data...</div> : !selectedTag ? <div className="workspace-empty">Select a pump to observe its condition.</div> : <>
        <section className="cmon-identity"><span className="eyebrow">Observation workspace</span><h1>{pump?.name ?? selectedTag}</h1><p>{pump?.area ?? "Area unavailable"} - latest capture: {latest?.readingDate ?? "Unavailable"}</p></section>
        <section className="cmon-health-grid"><article className="cmon-health-card"><span className="eyebrow">Overall health</span><strong>Unavailable</strong><span>Health score service is not available.</span></article><article className="cmon-health-card"><span className="eyebrow">Current status</span><strong>{latest ? "Observed" : "Unavailable"}</strong><span>{latest ? "Latest reading available" : "No reading available"}</span></article><article className="cmon-health-card"><span className="eyebrow">Monitoring status</span><strong>{schedule?.frequency ?? "Unavailable"}</strong><span>{schedule ? "Schedule available" : "No schedule available"}</span></article><article className="cmon-health-card"><span className="eyebrow">Intervention</span><strong>Unavailable</strong><span>Recommendation service is not available.</span></article></section>
        <div className="workspace-grid"><main className="main-column"><section className="assessment-section"><div className="section-head"><div><span className="eyebrow">Measurements</span><h2>Latest readings</h2></div><span className="status-signal neutral">Read-only evidence</span></div>{latest ? <div className="cmon-reading-grid">{readingItems(latest).map(([label, value, suffix]) => <div className="cmon-reading" key={label}><span>{label}</span><b className="tabular">{fmt(value, suffix)}</b></div>)}<div className="cmon-reading"><span>Vibration</span><b>Unavailable</b></div><div className="cmon-reading"><span>Pressure</span><b>Unavailable</b></div><div className="cmon-reading"><span>Flow</span><b>Unavailable</b></div><div className="cmon-reading"><span>Oil condition</span><b>Unavailable</b></div><div className="cmon-reading"><span>Bearing condition</span><b>Unavailable</b></div></div> : unavailable("Latest readings")}</section>
        <section className="assessment-section"><div className="section-head"><div><span className="eyebrow">Trend</span><h2>Trend charts</h2></div></div>{unavailable("Trend charts")}</section>
        <section className="assessment-section"><div className="section-head"><div><span className="eyebrow">Alerts</span><h2>Alerts and alarm history</h2></div></div>{unavailable("Alerts and alarm history")}</section>
        <section className="assessment-section"><PumpWorkspaceTimeline items={timeline} /></section>
        <section className="assessment-section"><div className="section-head"><div><span className="eyebrow">Evidence</span><h2>Evidence strip</h2></div></div>{unavailable("Evidence")}</section></main>
        <aside className="inspector-rail"><section className="rail-section"><h3>Sensor information</h3><div className="info-row"><span className="k">Schedule</span><span className="v">{schedule?.id ?? "Unavailable"}</span></div><div className="info-row"><span className="k">Parameters</span><span className="v">{schedule?.applicableParameters?.join(", ") || "Unavailable"}</span></div></section><section className="rail-section"><h3>Thresholds</h3>{unavailable("Thresholds")}</section><section className="rail-section"><h3>Related PM</h3>{unavailable("Related PM")}</section><section className="rail-section"><h3>Related Failure Analysis</h3>{unavailable("Related Failure Analysis")}</section><section className="rail-section"><h3>Related Mechanical Seal</h3>{unavailable("Related Mechanical Seal")}</section><section className="rail-section"><h3>Observation notes</h3>{unavailable("Observation notes")}</section></aside></div>
      </>}</div>
    <div className="action-bar"><div className="action-bar-inner"><div className="action-bar-status"><span className="label">Observation is read-only</span><span className="meta">Recommendations and intervention actions are unavailable.</span></div><div className="action-bar-actions"><button className="btn-link" type="button" onClick={() => showDrawer("Evidence")}>View evidence</button><button className="btn-primary" type="button" disabled>Review recommendation</button></div></div></div>
    <PumpWorkspaceCommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} actions={actions} pumpTag={selectedTag ?? "pump"} /><PumpWorkspaceDrawer open={Boolean(drawer)} onClose={() => setDrawer(null)} title={drawer ?? "Unavailable"}>{unavailable(drawer ?? "This capability")}</PumpWorkspaceDrawer>
  </WorkspaceShell>;
}