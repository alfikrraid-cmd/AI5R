import { useCallback, useEffect, useMemo, useState } from "react";
import AssetSelector from "../components/AssetSelector";
import PumpWorkspaceCommandPalette from "../components/PumpWorkspaceCommandPalette";
import PumpWorkspaceComingSoon from "../components/PumpWorkspaceComingSoon";
import PumpWorkspaceDrawer from "../components/PumpWorkspaceDrawer";
import PumpWorkspaceTimeline from "../components/PumpWorkspaceTimeline";
import { IconAlert, IconBox, IconHistory, IconMoon, IconSearch, IconSun, IconWrench } from "../components/PumpWorkspaceIcons";
import {
  getConditionMonitoringReadings, getConditionMonitoringReadingsPage, getConditionMonitoringSchedules, getPumps, postEngineeringAI,
  getPMSchedules, getCMReports,
} from "../../../api/ai5rClient";
import {
  EngineeringAIStatus,
  EngineeringAISummary,
  EngineeringAIProviderInfo,
  EngineeringAIConfidence,
  EngineeringAIRisk,
  EngineeringAIRemainingLife,
  EngineeringAIFindings,
  EngineeringAIEvidence,
  EngineeringAIRecommendation,
  EngineeringAISourceReferences,
} from "../components/engineering-ai";
import { mapPumpRecord } from "../utils/pumpMapping";
import { mapConditionMonitoringReadingRecord, mapConditionMonitoringScheduleRecord } from "../utils/conditionMonitoringMapping";
import { mapPMScheduleRecord } from "../utils/pmMapping";
import { mapCMReportRecord } from "../utils/cmMapping";
import generateTraceId from "../utils/generateTraceId";
import "./MaintenanceHistory.css";
import "./ConditionMonitoringWorkspace.css";
import WorkspaceShell from "../workspace/WorkspaceShell";
import { useWorkspaceTheme } from "../workspace/WorkspaceTheme";
import { useWorkspaceShortcuts } from "../workspace/WorkspaceShortcuts";
import { useWorkspaceDrawer } from "../workspace/WorkspaceDrawer";
import { WORKSPACE_KEYS } from "../workspace/WorkspaceRegistry";

const unavailable = (label) => <PumpWorkspaceComingSoon label={label} />;
const fmt = (value, suffix = "") => value == null || value === "" ? "Unavailable" : `${value}${suffix}`;

// MWO-LTSA-061 -- extended to surface every canonical
// condition_monitoring_reading dimension conditionMonitoringMapping.js
// already maps (quench/flushing-in/flushing-out/cooling-water/water-
// jacket DE-NDE pairs, pump operating state), not just the six fields
// this workspace originally rendered. No new reading table, no new
// mapping field -- every value here already existed in
// mapConditionMonitoringReadingRecord's output.
function readingItems(reading) {
  if (!reading) return [];
  return [
    ["Flushing temperature DE", reading.flushingTempDe, " C"], ["Flushing temperature NDE", reading.flushingTempNde, " C"],
    ["Quench temperature DE", reading.quenchTempDe, " C"], ["Quench temperature NDE", reading.quenchTempNde, " C"],
    ["Mechanical seal temperature DE", reading.mechsealTempDe, " C"], ["Mechanical seal temperature NDE", reading.mechsealTempNde, " C"],
    ["Suction temperature", reading.suctionTemp, " C"], ["Discharge temperature", reading.dischargeTemp, " C"],
    ["Leakage DE", reading.leakDe == null ? null : reading.leakDe ? "Observed" : "Not observed", ""],
    ["Leakage NDE", reading.leakNde == null ? null : reading.leakNde ? "Observed" : "Not observed", ""],
    ["Flushing in temperature DE", reading.flushingInTempDe, " C"], ["Flushing in temperature NDE", reading.flushingInTempNde, " C"],
    ["Flushing out temperature DE", reading.flushingOutTempDe, " C"], ["Flushing out temperature NDE", reading.flushingOutTempNde, " C"],
    ["Cooling water in temperature DE", reading.coolingWaterInTempDe, " C"], ["Cooling water in temperature NDE", reading.coolingWaterInTempNde, " C"],
    ["Cooling water out temperature DE", reading.coolingWaterOutTempDe, " C"], ["Cooling water out temperature NDE", reading.coolingWaterOutTempNde, " C"],
    ["Water jacket temperature DE", reading.waterJacketTempDe, " C"], ["Water jacket temperature NDE", reading.waterJacketTempNde, " C"],
    ["Pump operating state", reading.pumpOperatingState, ""],
  ];
}

// MWO-LTSA-061 -- honest threshold discipline: condition_monitoring_reading
// has no threshold/limit column anywhere in the canonical schema
// (conditionMonitoringMapping.js, condition_monitoring_reading_gateway.py).
// The only real, canonical abnormal-condition signal that exists is the
// mechanical seal leak flag (mechanical_seal_leak_de/nde). "Alerts" below
// are derived from that real boolean, never from an invented numeric
// limit -- per this MWO's explicit "do not fabricate thresholds" rule.
function leakLabel(reading) {
  if (reading.leakDe && reading.leakNde) return "Mechanical seal leak observed — DE and NDE";
  if (reading.leakDe) return "Mechanical seal leak observed — DE";
  if (reading.leakNde) return "Mechanical seal leak observed — NDE";
  return null;
}

export default function ConditionMonitoringWorkspace({ navContext, onNavigate }) {
  const [pumps, setPumps] = useState([]);
  const [selectedTag, setSelectedTag] = useState(navContext?.assetTag ?? null);
  const [readings, setReadings] = useState([]);
  const [readingsTotal, setReadingsTotal] = useState(0);
  const [readingsOffset, setReadingsOffset] = useState(0);
  const [readingsError, setReadingsError] = useState(null);
  const readingsLimit = 25;
  const [schedules, setSchedules] = useState([]);
  // MWO-LTSA-061 -- Related PM / Related Failure Analysis, reusing
  // getPMSchedules()/getCMReports() and mapPMScheduleRecord/
  // mapCMReportRecord exactly as Pump.jsx/Seal.jsx/PM.jsx/WorkOrder.jsx
  // already do -- no new endpoint, no new mapping. cmReports here IS
  // Corrective Maintenance (`cm`) report data, read-only, filtered
  // client-side by equipmentTag -- the same real backend
  // FailureAnalysisWorkspace.jsx itself already renders under the
  // "failure-analysis-workspace" key (FailureAnalysisWorkspace.jsx:
  // getCMReports()/mapCMReportRecord is its own, only data source). This
  // is the one existing, real "Related Failure Analysis" data available
  // anywhere in the platform, not a fabricated relationship and not a
  // cm/cmon domain mix-up: cmon (this file) only ever reads cm_report
  // data for display, never writes it, never imports a cmon-specific
  // object into the cm domain or vice versa.
  const [pmSchedules, setPmSchedules] = useState([]);
  const [failureAnalysisReports, setFailureAnalysisReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [paletteOpen, setPaletteOpen] = useWorkspaceShortcuts();
  const { drawer, openDrawer: setDrawer } = useWorkspaceDrawer();
  const [theme, setTheme] = useWorkspaceTheme();
  const [aiResponse, setAiResponse] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(null);
  useEffect(() => {
    let active = true;
    const readPage = typeof getConditionMonitoringReadingsPage === "function"
      ? getConditionMonitoringReadingsPage({ limit: readingsLimit, offset: readingsOffset })
      : getConditionMonitoringReadings().then((items) => ({ items, total: items.length, limit: items.length, offset: 0 }));

    setReadingsError(null);
    readPage.then(({ items, total }) => {
      if (!active) return;
      const readingItems = items.map(mapConditionMonitoringReadingRecord);
      setReadings(readingItems);
      setReadingsTotal(total);
      setLoading(false);
      if (!selectedTag && readingItems.length > 0) setSelectedTag(readingItems[0].equipmentTag);
    }).catch(() => {
      if (active) {
        setReadingsError("Condition Monitoring readings could not be loaded.");
        setLoading(false);
      }
    });

    return () => { active = false; };
  }, [readingsOffset]);

  useEffect(() => {
    let active = true;
    Promise.all([
      getPumps().then((items) => items.map(mapPumpRecord)).catch(() => []),
      getConditionMonitoringSchedules().then((items) => items.map(mapConditionMonitoringScheduleRecord)).catch(() => []),
      getPMSchedules().then((items) => items.map(mapPMScheduleRecord)).catch(() => []),
      getCMReports().then((items) => items.map(mapCMReportRecord)).catch(() => []),
    ]).then(([pumpItems, scheduleItems, pmItems, cmReportItems]) => {
      if (!active) return;
      setPumps(pumpItems); setSchedules(scheduleItems);
      setPmSchedules(pmItems); setFailureAnalysisReports(cmReportItems);
      if (!selectedTag && pumpItems.length === 1) setSelectedTag(pumpItems[0].tag);
    });
    return () => { active = false; };
  }, []);

  const pump = pumps.find((item) => item.tag === selectedTag) ?? null;
  const pumpReadings = useMemo(() => readings.filter((item) => item.equipmentTag === selectedTag).sort((a, b) => String(b.readingDate).localeCompare(String(a.readingDate))), [readings, selectedTag]);
  const latest = pumpReadings[0] ?? null;
  const schedule = schedules.find((item) => item.equipmentTag === selectedTag) ?? null;
  const abnormalReadings = useMemo(() => pumpReadings.filter((item) => item.leakDe || item.leakNde), [pumpReadings]);
  const relatedPM = useMemo(() => pmSchedules.filter((item) => item.equipmentTag === selectedTag), [pmSchedules, selectedTag]);
  const relatedFailureAnalysis = useMemo(() => failureAnalysisReports.filter((item) => item.equipmentTag === selectedTag), [failureAnalysisReports, selectedTag]);

  // Engineering AI: Condition Monitoring Workspace is a pure consumer,
  // exactly like FailureAnalysisWorkspace (Golden Reference) and
  // PMWorkOrderWorkspace (implementation reference). It builds an
  // EngineeringAIRequest-shaped payload and calls postEngineeringAI() --
  // it never builds a prompt, never builds engineering context, never
  // constructs an AI client, and never calls a Router or provider
  // directly. Reuses the existing "cm_review" intent/prompt_type
  // (EngineeringPromptBuilder.build_cm_review_prompt is already
  // condition-monitoring-and-seal-health-shaped) -- no new intent was
  // invented or required. selected_record_id reuses the already-supported
  // field (demonstrated by Failure Analysis and PM) for the latest
  // reading currently displayed, when one exists.
  useEffect(() => {
    if (!selectedTag) {
      setAiResponse(null);
      setAiError(null);
      setAiLoading(false);
      return;
    }
    let active = true;
    setAiLoading(true);
    setAiError(null);
    setAiResponse(null);
    postEngineeringAI({
      asset_code: selectedTag,
      intent: "cm_review",
      prompt_type: "cm_review",
      trace_id: generateTraceId(),
      selected_record_id: latest?.id,
      workspace: WORKSPACE_KEYS.CONDITION_MONITORING,
    })
      .then((response) => { if (active) setAiResponse(response); })
      .catch((error) => { if (active) setAiError(error?.message || "Engineering AI request failed"); })
      .finally(() => active && setAiLoading(false));
    return () => { active = false; };
  }, [selectedTag, latest?.id]);

  const aiBusinessError = aiResponse?.error ?? null;
  const aiReady = !aiLoading && !aiError && !!aiResponse && !aiBusinessError;
  const aiStatusText = aiLoading ? "Generating condition review…" : (aiError || aiBusinessError || "Engineering AI has not run for this pump yet.");
  const aiStatusVariant = aiLoading ? "neutral" : (aiError || aiBusinessError) ? "critical" : aiReady ? (aiResponse.execution_status === "SUCCESS" ? "normal" : "attention") : "unavailable";
  const aiStatusLabel = aiLoading ? "Generating…" : (aiError || aiBusinessError) ? "Error" : aiReady ? aiResponse.execution_status : "Unavailable";
  const timeline = useMemo(() => pumpReadings.map((item) => ({ id: item.id, tier: item.leakDe || item.leakNde ? "attention" : "normal", tag: "Reading", title: `Condition monitoring reading ${item.id}`, date: item.readingDate })), [pumpReadings]);
  const showDrawer = useCallback((label) => setDrawer(label), []);
  const scrollTo = useCallback((id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }), []);
  // MWO-LTSA-061 -- "thresholds"/"recommendation" now scroll to real,
  // already-rendered sections (Thresholds rail section; the Engineering
  // AI section, where EngineeringAIRecommendation already renders live
  // recommendations when aiReady) instead of opening a permanently
  // "Unavailable" Drawer. "evidence" is unchanged -- Evidence is not in
  // MWO-LTSA-061's scope.
  const actions = useMemo(() => [
    { id: "timeline", label: "View measurement timeline", hint: "Observation", icon: IconHistory, run: () => scrollTo("timeline-section") },
    { id: "thresholds", label: "View thresholds", hint: "Interpretation", icon: IconAlert, run: () => scrollTo("thresholds-section") },
    { id: "evidence", label: "View evidence", hint: "Unavailable", icon: IconBox, run: () => showDrawer("Evidence") },
    { id: "recommendation", label: "View recommendation", hint: aiReady ? "Engineering AI" : "Unavailable", icon: IconWrench, run: () => scrollTo("engineering-ai-section") },
  ], [showDrawer, scrollTo, aiReady]);

  return <WorkspaceShell className="cmon-workspace-root" theme={theme}>
    <header className="chrome-bar"><div className="chrome-inner"><div className="crumb"><span>LTSA</span><span className="sep">/</span><span>Condition Monitoring</span><span className="sep">/</span><b>{pump?.tag ?? "Observation"}</b></div><div className="chrome-right"><button type="button" className="cmdk-trigger" onClick={() => setPaletteOpen(true)}><IconSearch width="14" height="14" /> Actions <kbd>Ctrl K</kbd></button><button type="button" className="icon-btn" onClick={() => setTheme(theme === "light" ? "dark" : "light")} aria-label="Toggle theme">{theme === "light" ? <IconMoon width="16" height="16" /> : <IconSun width="16" height="16" />}</button></div></div></header>
    <div className="workspace-shell"><AssetSelector assets={pumps} selectedTag={selectedTag} onSelect={setSelectedTag} />
      {loading ? <div className="workspace-empty">Loading condition monitoring data...</div> : readingsError ? <div className="workspace-empty" role="alert">{readingsError}</div> : !selectedTag ? <div className="workspace-empty">Select a pump to observe its condition.</div> : <>
        <section className="cmon-identity"><span className="eyebrow">Observation workspace</span><h1>{pump?.name ?? selectedTag}</h1><p>{pump?.area ?? "Area unavailable"} - latest capture: {latest?.readingDate ?? "Unavailable"}</p></section>
        <section className="cmon-health-grid"><article className="cmon-health-card"><span className="eyebrow">Overall health</span><strong>Unavailable</strong><span>Health score service is not available.</span></article><article className="cmon-health-card"><span className="eyebrow">Current status</span><strong>{latest ? "Observed" : "Unavailable"}</strong><span>{latest ? "Latest reading available" : "No reading available"}</span></article><article className="cmon-health-card"><span className="eyebrow">Monitoring status</span><strong>{schedule?.frequency ?? "Unavailable"}</strong><span>{schedule ? "Schedule available" : "No schedule available"}</span></article><article className="cmon-health-card"><span className="eyebrow">Intervention</span><strong>Unavailable</strong><span>Recommendation service is not available.</span></article></section>
        <div className="workspace-grid"><main className="main-column"><section className="assessment-section"><div className="section-head"><div><span className="eyebrow">Measurements</span><h2>Latest readings</h2></div><span className="status-signal neutral">Read-only evidence</span></div>{latest ? <div className="cmon-reading-grid">{readingItems(latest).map(([label, value, suffix]) => <div className="cmon-reading" key={label}><span>{label}</span><b className="tabular">{fmt(value, suffix)}</b></div>)}<div className="cmon-reading"><span>Vibration</span><b>Unavailable</b></div><div className="cmon-reading"><span>Pressure</span><b>Unavailable</b></div><div className="cmon-reading"><span>Flow</span><b>Unavailable</b></div><div className="cmon-reading"><span>Oil condition</span><b>Unavailable</b></div><div className="cmon-reading"><span>Bearing condition</span><b>Unavailable</b></div></div> : unavailable("Latest readings")}</section>

        {/* MWO-LTSA-061 -- Measurement history: every readings.filter(equipmentTag)
            entry (pumpReadings, already computed above), not just the latest.
            Real data only -- an honest "no readings" empty state when a pump has
            none, never a fabricated row. */}
        <section className="assessment-section" id="history-section" data-testid="measurement-history">
          <div className="section-head">
            <div><span className="eyebrow">History</span><h2>Measurement history</h2></div>
            <span className="status-signal neutral">{readingsTotal} reading{readingsTotal === 1 ? "" : "s"}</span>
          </div>
          {pumpReadings.length === 0 ? unavailable("Measurement history") : pumpReadings.map((item) => (
            <div className="info-row" key={item.id}>
              <span className="k tabular">{item.readingDate ?? "Unknown date"}</span>
              <span className="v">
                {[
                  item.flushingTempDe != null ? `Flushing DE ${item.flushingTempDe} C` : null,
                  item.flushingTempNde != null ? `NDE ${item.flushingTempNde} C` : null,
                  item.mechsealTempDe != null ? `Mech seal DE ${item.mechsealTempDe} C` : null,
                  item.mechsealTempNde != null ? `NDE ${item.mechsealTempNde} C` : null,
                  item.suctionTemp != null ? `Suction ${item.suctionTemp} C` : null,
                  item.dischargeTemp != null ? `Discharge ${item.dischargeTemp} C` : null,
                  leakLabel(item),
                ].filter(Boolean).join(" · ") || "No measurement values recorded"}
              </span>
            </div>
          ))}
          <div className="section-head">
            <span className="status-signal neutral">
              {readingsTotal === 0 ? "0–0 of 0" : `${readingsOffset + 1}–${Math.min(readingsOffset + readings.length, readingsTotal)} of ${readingsTotal}`}
            </span>
            <div>
              <button type="button" className="btn-link" disabled={readingsOffset === 0} onClick={() => setReadingsOffset((offset) => Math.max(0, offset - readingsLimit))}>Previous</button>
              <button type="button" className="btn-link" disabled={readingsOffset + readingsLimit >= readingsTotal} onClick={() => setReadingsOffset((offset) => offset + readingsLimit)}>Next</button>
            </div>
          </div>
        </section>

        <section className="assessment-section" id="engineering-ai-section" data-testid="ai-summary">
          <div className="section-head">
            <div><span className="eyebrow">Engineering AI</span><h2>Condition Review</h2></div>
            {aiReady ? <EngineeringAIStatus response={aiResponse} /> : <span className={`status-signal ${aiStatusVariant}`}>{aiStatusLabel}</span>}
          </div>
          {aiReady ? (
            <>
              <EngineeringAISummary response={aiResponse} />
              <EngineeringAIProviderInfo response={aiResponse} />
              <EngineeringAIConfidence response={aiResponse} />
              <EngineeringAIRisk response={aiResponse} />
              <EngineeringAIRemainingLife response={aiResponse} />
            </>
          ) : (
            <p className="v">{aiStatusText}</p>
          )}
        </section>
        {aiReady && <EngineeringAIFindings response={aiResponse} />}
        {aiReady && <EngineeringAIEvidence response={aiResponse} />}
        {aiReady && <EngineeringAIRecommendation response={aiResponse} />}

        <section className="assessment-section"><div className="section-head"><div><span className="eyebrow">Trend</span><h2>Trend charts</h2></div></div>{unavailable("Trend charts")}</section>
        {/* MWO-LTSA-061 -- Alerts and threshold interpretation, merged
            honestly: condition_monitoring_reading has no threshold/limit
            column anywhere in the canonical schema, so no NORMAL/WARNING/
            CRITICAL tier is computed for temperature values (that would be
            hardcoding an engineering limit this MWO explicitly forbids).
            The one real, canonical abnormal-condition signal is the
            mechanical seal leak flag (leakDe/leakNde) -- abnormalReadings
            (derived above from the already-fetched pumpReadings) lists
            exactly that, nothing invented. */}
        <section className="assessment-section" id="alerts-section" data-testid="alerts-section"><div className="section-head"><div><span className="eyebrow">Alerts</span><h2>Alerts and alarm history</h2></div></div><p className="v">No canonical threshold is defined for temperature measurements; alerts below reflect only the mechanical seal leak flags, the one real abnormal-condition signal currently available.</p>{abnormalReadings.length === 0 ? unavailable("Alerts and alarm history") : abnormalReadings.map((item) => <div className="info-row" key={item.id}><span className="k tabular">{item.readingDate ?? "Unknown date"}</span><span className="v">{leakLabel(item)}</span></div>)}</section>
        <section className="assessment-section"><PumpWorkspaceTimeline items={timeline} /></section>
        <section className="assessment-section"><div className="section-head"><div><span className="eyebrow">Evidence</span><h2>Evidence strip</h2></div></div>{unavailable("Evidence")}</section></main>
        <aside className="inspector-rail"><section className="rail-section"><h3>Sensor information</h3><div className="info-row"><span className="k">Schedule</span><span className="v">{schedule?.id ?? "Unavailable"}</span></div><div className="info-row"><span className="k">Parameters</span><span className="v">{schedule?.applicableParameters?.join(", ") || "Unavailable"}</span></div></section>
          {/* MWO-LTSA-061 -- honest threshold interpretation: no canonical
              limit column exists, so this reports the real leak-flag signal
              (the only real abnormal-condition fact available) rather than
              a fabricated NORMAL/WARNING tier. */}
          <section className="rail-section" id="thresholds-section"><h3>Thresholds</h3><p className="field-unavailable">No canonical threshold defined for temperature measurements.</p><div className="info-row"><span className="k">Leak DE</span><span className="v">{latest ? (latest.leakDe ? "Observed" : "Not observed") : "Unavailable"}</span></div><div className="info-row"><span className="k">Leak NDE</span><span className="v">{latest ? (latest.leakNde ? "Observed" : "Not observed") : "Unavailable"}</span></div></section>
          {/* Related PM: getPMSchedules()/mapPMScheduleRecord, same
              already-wired call Pump.jsx/Seal.jsx/PM.jsx use, filtered by
              this pump's own tag (canonical Pump identity, selectedTag). */}
          <section className="rail-section"><h3>Related PM</h3>{relatedPM.length === 0 ? <p className="field-unavailable">No PM schedules matched to this asset.</p> : relatedPM.map((item) => <div className="info-row" key={item.id}><span className="k">{item.id}</span><span className="v">{item.nextDue ? `Due ${item.nextDue}` : item.procedure ?? "—"}</span></div>)}</section>
          {/* Related Failure Analysis: cm_report data, the same real
              backend FailureAnalysisWorkspace.jsx itself renders under the
              failure-analysis-workspace key -- see relatedFailureAnalysis's
              own definition above for why this is not a cm/cmon domain
              mix-up. Filtered by canonical Pump identity (selectedTag). */}
          <section className="rail-section"><h3>Related Failure Analysis</h3>{relatedFailureAnalysis.length === 0 ? <p className="field-unavailable">No failure analysis records matched to this asset.</p> : relatedFailureAnalysis.map((item) => <div className="info-row" key={item.id}><span className="k">{item.id}</span><span className="v">{item.failureDescription ?? "—"}</span></div>)}</section>
          <section className="rail-section"><h3>Related Mechanical Seal</h3>{unavailable("Related Mechanical Seal")}</section><section className="rail-section"><h3>Observation notes</h3>{unavailable("Observation notes")}</section>{aiReady ? <EngineeringAISourceReferences response={aiResponse} /> : <section className="rail-section" data-testid="ai-source-references"><h3>Source References</h3><p className="v">{aiStatusText}</p></section>}</aside></div>
      </>}</div>
    <div className="action-bar"><div className="action-bar-inner"><div className="action-bar-status"><span className="label">Observation is read-only</span><span className="meta">Intervention actions are unavailable; recommendations are Engineering AI-derived, not editable here.</span></div><div className="action-bar-actions"><button className="btn-link" type="button" onClick={() => showDrawer("Evidence")}>View evidence</button><button className="btn-primary" type="button" disabled={!aiReady} onClick={() => scrollTo("engineering-ai-section")}>Review recommendation</button></div></div></div>
    <PumpWorkspaceCommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} actions={actions} pumpTag={selectedTag ?? "pump"} /><PumpWorkspaceDrawer open={Boolean(drawer)} onClose={() => setDrawer(null)} title={drawer ?? "Unavailable"}>{unavailable(drawer ?? "This capability")}</PumpWorkspaceDrawer>
  </WorkspaceShell>;
}