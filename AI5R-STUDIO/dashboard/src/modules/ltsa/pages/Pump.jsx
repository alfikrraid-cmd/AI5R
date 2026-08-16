import { useEffect, useMemo, useState } from "react";
import { EmptyState, PageHeader, Panel } from "../../../design-system";
import PumpFilterBar from "../components/PumpFilterBar";
import PumpRegistryTable from "../components/PumpRegistryTable";
import PumpOpenDesignView from "../components/PumpOpenDesignView";
import CreatePMScheduleModal from "../components/CreatePMScheduleModal";
import CreateCMReportModal from "../components/CreateCMReportModal";
import { getPumps, getPumpLifecycle, getSeals, getSealCompatibility, postEngineeringAI } from "../../../api/ai5rClient";
import { mapPumpRecord, withResolvedOpenWO } from "../utils/pumpMapping";
import { mapPumpLifecycleRecord } from "../utils/pumpLifecycleMapping";
import { buildSealInventoryGroups } from "../utils/sealMapping";
import generateTraceId from "../utils/generateTraceId";
import { resolveEngineeringObject } from "../workspace/EngineeringObjectResolver";
import "./Pump.css";
import "./LTSAOpenDesign.css";

// Engineering AI: Pump Workspace is a pure consumer, exactly like
// FailureAnalysisWorkspace (the Golden Reference). It builds an
// EngineeringAIRequest-shaped payload and calls postEngineeringAI() (HTTP
// transport only, ai5rClient.js) -- it never builds a prompt, never
// builds engineering context, never constructs an AI client, and never
// calls a Router or provider directly. Reuses the existing "summary"
// intent/prompt_type (EngineeringPromptBuilder.build_summary_prompt is
// already pump-status-shaped: asset/PM status/CM condition/open work
// orders/seal stock) -- no new intent was invented or required.
// Rendering of EngineeringAIResponse content is delegated entirely to
// PumpDetailPanel, which uses only the packaged Engineering AI UI
// components, exactly like the Golden Reference.

function matchesSearch(pump, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    (pump.tag || "").toLowerCase().includes(term) ||
    (pump.name || "").toLowerCase().includes(term) ||
    (pump.manufacturer || "").toLowerCase().includes(term)
  );
}

export default function Pump({ onNavigate, navContext }) {
  const [pumps, setPumps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedCode, setSelectedCode] = useState(null);
  const [isCreatePMOpen, setIsCreatePMOpen] = useState(false);
  const [isCreateCMOpen, setIsCreateCMOpen] = useState(false);
  const [aiResponse, setAiResponse] = useState(null), [aiLoading, setAiLoading] = useState(false), [aiError, setAiError] = useState(null);

  useEffect(() => {
    let active = true;

    getPumps()
      .then((records) => Promise.all(records.map(mapPumpRecord).map(withResolvedOpenWO)))
      .then((resolved) => {
        if (active) {
          setPumps(resolved);
          setListError(null);
        }
      })
      .catch(() => {
        if (active) {
          setListError("Pumps could not be loaded.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  // Deep-link entry point (APP-ASSET360-001, per ADR-ASSET360-001):
  // cross-domain links elsewhere (e.g. CMDetailPanel's "Related Pump")
  // navigate here with { selectId: tag } to pre-select this pump. Gated
  // on `!loading`: selectedPump is derived from `pumps`, so selecting
  // before the list has loaded would resolve to no pump at all. Re-fires
  // once loading flips to false.
  useEffect(() => {
    if (navContext?.selectId && !loading) {
      selectPump(navContext.selectId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navContext, loading]);

  const statusOptions = useMemo(() => [...new Set(pumps.map((pump) => pump.status))], [pumps]);

  const filteredPumps = useMemo(
    () =>
      pumps.filter(
        (pump) => matchesSearch(pump, search) && (statusFilter === "ALL" || pump.status === statusFilter)
      ),
    [pumps, search, statusFilter]
  );

  const selectedPump = filteredPumps.find((pump) => pump.code === selectedCode) ?? null;

  // MWO-LTSA-065 -- Pump Workspace's detail view is driven by ONE fetch:
  // GET /api/ltsa/pumps/{tag}/lifecycle (EquipmentTimelineService.
  // build_lifecycle(), MWO-LTSA-064A). This replaces the three separate
  // fetches Related Engineering used to make here (getPMSchedules()/
  // getCMReports()/getWorkOrders(), each filtered client-side) -- the
  // lifecycle endpoint already returns pm_schedules/cm_reports/work_orders
  // (plus drawings/documents/inventory, not previously fetched at all)
  // pre-filtered to this pump server-side. No client-side filtering, no
  // re-aggregation -- pumpLifecycleMapping.js only renames snake_case
  // keys to camelCase, nothing is recomputed. Never throws -- a failed
  // fetch leaves lifecycle null (rendered as an honest "no data" state by
  // PumpOpenDesignView), same "degrade, never fabricate" discipline as
  // the rest of this file.
  const [lifecycle, setLifecycle] = useState(null);
  const [lifecycleLoading, setLifecycleLoading] = useState(false);

  useEffect(() => {
    if (!selectedPump) {
      setLifecycle(null);
      setLifecycleLoading(false);
      return undefined;
    }
    let active = true;
    setLifecycleLoading(true);
    getPumpLifecycle(selectedPump.tag)
      .then((payload) => {
        if (active) setLifecycle(mapPumpLifecycleRecord(payload));
      })
      .catch(() => {
        if (active) setLifecycle(null);
      })
      .finally(() => {
        if (active) setLifecycleLoading(false);
      });
    return () => { active = false; };
  }, [selectedPump?.tag]);

  // MWO-LTSA-UI-V2-001 -- Seal & Inventory: two global reference lists
  // (every seal's Type/Size; every seal_pump_compatibility row), fetched
  // once on mount -- not per pump, not re-fetched on selection -- mirroring
  // Seal.jsx's own identical "resolve once, derive many" pattern for the
  // exact same two already-existing endpoints (getSeals()/
  // getSealCompatibility(), no new backend route). A failure here degrades
  // to an empty list rather than fabricating data or blocking the rest of
  // the page.
  const [seals, setSeals] = useState([]);
  const [compatibilityRecords, setCompatibilityRecords] = useState([]);

  useEffect(() => {
    let active = true;
    Promise.all([getSeals().catch(() => []), getSealCompatibility().catch(() => [])]).then(
      ([sealRecords, compatibility]) => {
        if (active) {
          setSeals(sealRecords);
          setCompatibilityRecords(compatibility);
        }
      }
    );
    return () => { active = false; };
  }, []);

  // Enriches lifecycle.relatedEngineering.inventory (seal_code/quantity_on_
  // hand/location only, MWO-LTSA-065) with each seal's real Type/Size and
  // full compatible-pump list -- pure derivation over already-fetched data,
  // computed once per lifecycle/seals/compatibility change, never inside
  // the view (PumpOpenDesignView stays a "display lifecycle values only"
  // component, per its own existing header rule).
  const sealInventoryGroups = useMemo(
    () => buildSealInventoryGroups(lifecycle?.relatedEngineering?.inventory ?? [], seals, compatibilityRecords),
    [lifecycle, seals, compatibilityRecords]
  );

  // MWO-LTSA-050 -- Documents' "Buka Drawing" reuses the exact same
  // onNavigate(key, context) mechanism Seal.jsx's handleOpenDrawing already
  // uses -- the same "drawing" tab key LTSAWorkspace.jsx already registers,
  // not pump-specific in any way.
  function handleOpenDrawing() {
    onNavigate?.("drawing", {});
  }

  // MWO-LTSA-070 -- Engineering Navigation: every engineering object shown
  // in Pump Workspace (lifecycle.timeline events and
  // lifecycle.relatedEngineering items) becomes clickable, reusing the
  // exact same onNavigate(key, context) mechanism and the exact same
  // LTSAWorkspace.jsx PAGES keys/navContext contracts every other
  // workspace's own cross-navigation already relies on -- no new route,
  // no new page, no duplicate data (every navigated-to field is already
  // real, already on the clicked object's own payload/record).
  //
  // MWO-LTSA-071 -- the "which workspace + which navContext" decision
  // this switch used to make inline now delegates to the canonical
  // EngineeringObjectResolver (workspace/EngineeringObjectResolver.js) --
  // this function's own remaining job is only Pump-Timeline-specific:
  // extracting entityId/assetTag from each event type's own real payload
  // shape (pm_occurrence.pm_schedule_code, cm_report_code, etc. -- shapes
  // that are particular to Pump Workspace's Timeline/Related-Engineering
  // data, not part of the resolver's generic contract). See that module's
  // own header comment for the full, evidence-cited per-type rules
  // (INSTALLATION/PM/CM/WORK_ORDER/DRAWING/PUMP), which are unchanged
  // from what this function previously did inline.
  //
  // FAILURE and REPLACEMENT are not in the resolver's supported-type list
  // (no Failure/Replacement workspace exists to send them to) and stay a
  // deliberate no-op here, same as before -- filtered out before ever
  // reaching the resolver, so an unsupported Timeline event type still
  // never throws.
  function handleOpenEngineeringObject(eventType, payload) {
    if (!payload) {
      return;
    }

    let entityId;
    let assetTag;

    switch (eventType) {
      case "INSTALLATION":
        entityId = payload.installation_code;
        break;
      case "PM":
        entityId = payload.pm_schedule_code;
        assetTag = payload.asset_code ?? payload.plant_equip_no;
        break;
      case "CM":
        entityId = payload.cm_report_code;
        break;
      case "WORK_ORDER":
        entityId = payload.work_order_code;
        break;
      case "DRAWING":
        assetTag = selectedPump?.tag;
        break;
      case "PUMP":
      case "LIFECYCLE":
        entityId = payload.tag_number ?? payload.asset_code ?? payload.plant_equip_no ?? payload.tag;
        break;
      default:
        return;
    }

    if (!entityId && !assetTag) {
      return;
    }

    const entityType = eventType === "LIFECYCLE" ? "PUMP" : eventType;
    const { workspace, navigationContext } = resolveEngineeringObject({ entityType, entityId, assetTag });
    onNavigate?.(workspace, navigationContext);
  }

  useEffect(() => {
    if (!selectedPump) { setAiResponse(null); setAiError(null); setAiLoading(false); return; }
    let active = true;
    setAiLoading(true); setAiError(null); setAiResponse(null);
    postEngineeringAI({
      asset_code: selectedPump.tag,
      intent: "summary",
      prompt_type: "summary",
      trace_id: generateTraceId(),
      workspace: "pump",
    })
      .then((response) => { if (active) setAiResponse(response); })
      .catch((error) => { if (active) setAiError(error?.message || "Engineering AI request failed"); })
      .finally(() => active && setAiLoading(false));
    return () => { active = false; };
  }, [selectedPump?.code]);

  const aiBusinessError = aiResponse?.error ?? null;
  const aiReady = !aiLoading && !aiError && !!aiResponse && !aiBusinessError;
  const aiStatusText = aiLoading ? "Generating pump summary…" : (aiError || aiBusinessError || "Engineering AI has not run for this pump yet.");
  const aiStatusVariant = aiLoading ? "neutral" : (aiError || aiBusinessError) ? "critical" : aiReady ? (aiResponse.execution_status === "SUCCESS" ? "normal" : "attention") : "unavailable";
  const aiStatusLabel = aiLoading ? "Generating…" : (aiError || aiBusinessError) ? "Error" : aiReady ? aiResponse.execution_status : "Unavailable";

  // MWO-LTSA-065 -- lastPM and spareParts were the two per-pump resolvers
  // this function used to merge back onto the selected row (withResolvedLastPM/
  // withResolvedSpareParts, both removed above). Both are now lifecycle
  // fields (current_state.last_pm, related_engineering.inventory) fetched
  // by the effect above -- selection itself is now just selection.
  function selectPump(code) {
    setSelectedCode(code);
  }

  return (
    <div>
      <PageHeader title="Pump Workspace" subtitle="LTSA Engineering — Pump Registry" />

      <PumpFilterBar
        searchValue={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statusOptions={statusOptions}
      />

      {loading ? (
        <Panel>
          <p>Loading pumps...</p>
        </Panel>
      ) : listError ? (
        <Panel>
          <p role="alert">{listError}</p>
        </Panel>
      ) : (
        <div className="pump-workspace-layout">
          <div className="pump-workspace-registry">
            <PumpRegistryTable
              pumps={filteredPumps}
              selectedCode={selectedCode}
              onSelect={selectPump}
            />
          </div>

          <div className="pump-workspace-detail">
            {selectedPump ? (
              <PumpOpenDesignView
                pump={selectedPump}
                lifecycle={lifecycle}
                lifecycleLoading={lifecycleLoading}
                sealInventoryGroups={sealInventoryGroups}
                onOpenDrawing={handleOpenDrawing}
                onOpenEngineeringObject={handleOpenEngineeringObject}
                onCreatePM={() => setIsCreatePMOpen(true)}
                onCreateCM={() => setIsCreateCMOpen(true)}
                onViewHistory={() => onNavigate?.("history", { assetTag: selectedPump.tag })}
                aiResponse={aiResponse}
                aiReady={aiReady}
                aiStatusText={aiStatusText}
                aiStatusVariant={aiStatusVariant}
                aiStatusLabel={aiStatusLabel}
              />
            ) : (
              <EmptyState
                title="No pump selected"
                description="Select a pump from the registry table to view its details."
              />
            )}
          </div>
        </div>
      )}

      <CreatePMScheduleModal
        isOpen={isCreatePMOpen}
        onClose={() => setIsCreatePMOpen(false)}
        onCreate={() => setIsCreatePMOpen(false)}
      />

      <CreateCMReportModal
        isOpen={isCreateCMOpen}
        onClose={() => setIsCreateCMOpen(false)}
        onCreate={() => setIsCreateCMOpen(false)}
      />
    </div>
  );
}
