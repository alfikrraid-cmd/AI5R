import { useEffect, useMemo, useState } from "react";
import { EmptyState, Panel, PageHeader } from "../../../design-system";
import SealFilterBar from "../components/SealFilterBar";
import SealRegistryTable from "../components/SealRegistryTable";
import SealOpenDesignView from "../components/SealOpenDesignView";
import PhysicalSealWorkspace from "../components/PhysicalSealWorkspace";
import samplePumps from "../data/samplePumps";
import {
  getSeals, getSealCompatibility, getSealStock, postEngineeringAI,
  getPMSchedules, getCMReports, getWorkOrders, updateSealIdentifiers,
} from "../../../api/ai5rClient";
import { mapSealRecord, resolveCompatiblePumps, resolveStock } from "../utils/sealMapping";
import { useOptionalAuth } from "../auth/AuthContext";
import { can, PERMISSIONS } from "../auth/permissions";
import { mapPMScheduleRecord } from "../utils/pmMapping";
import { mapCMReportRecord } from "../utils/cmMapping";
import { mapWorkOrderRecord } from "../utils/workOrderMapping";
import generateTraceId from "../utils/generateTraceId";
import "./Seal.css";
import "./MaintenanceHistory.css";
import "./LTSAOpenDesign.css";

// Engineering AI: Mechanical Seal Workspace is the fifth consumer of the
// canonical Engineering AI platform (Golden Reference:
// FailureAnalysisWorkspace.jsx; pattern also already reused by
// Pump.jsx). Pure consumer -- builds an EngineeringAIRequest-shaped
// payload and calls postEngineeringAI() (HTTP transport only,
// ai5rClient.js). Never builds a prompt, never builds engineering
// context, never constructs an AI client, and never calls a Router or
// provider directly. Reuses the existing "summary" intent/prompt_type
// (EngineeringContextEngine already exposes seal_summary/
// inventory_summary) -- no new intent invented, no backend change.
//
// EngineeringContextEngine.build(tag_number) resolves context for a
// PUMP asset_code, not a seal code -- a seal itself has no asset_code.
// asset_code is therefore resolved via the seal's first compatible pump
// (seal.compatiblePumps[0]) cross-referenced to that pump's `tag` field,
// exactly as sampleSeals.js's own header comment documents
// ("compatiblePumps codes match samplePumps.js's own code field"). A
// seal with no compatible pump (or no matching pump record) has no
// resolvable asset_code, so no AI request is made for it -- mirroring
// the Golden Reference's "no selection -> skip" guard.
//
// MWO-LTSA-042 -- the real backend path (getSealCompatibility(), via
// resolveCompatiblePumps in sealMapping.js) populates compatiblePumps
// with the real seal_pump_compatibility.pump_tag_number column, which is
// already a real pump tag, not a samplePumps "code" needing translation.
// samplePumps lookup is tried FIRST (unchanged, preserves every existing
// test's fixture-data behavior, sampleSeals.js's "PMP-xxx" codes still
// resolve exactly as before) -- if no match is found there, the value is
// used as-is, since it is then coming from the real endpoint and is
// already a tag, not a fabrication.
function resolveAssetCode(seal) {
  const pumpCode = seal?.compatiblePumps?.[0];
  if (!pumpCode) return null;
  const pump = samplePumps.find((candidate) => candidate.code === pumpCode);
  return pump?.tag ?? pumpCode;
}

// MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 Phase 11 -- extended to KIMAP
// Pertamina, GPN John Crane, and compatible Pump Tag. Client-side is the
// correct place for this: seal.py has no backend search/filter query
// param today (GET /api/ltsa/seals is a full-list endpoint only, per the
// Phase 0 architecture audit), so extending the existing mechanism is
// additive, not a new search layer invented ahead of a real need.
// kimapPertamina/gpnJohnCrane are nullable (Hard Rule 6: missing
// identifiers must not block operations) -- `?? ""` before lowercasing
// avoids crashing search on every not-yet-completed seal.
function matchesSearch(seal, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    seal.name.toLowerCase().includes(term) ||
    seal.type.toLowerCase().includes(term) ||
    seal.manufacturer.toLowerCase().includes(term) ||
    (seal.kimapPertamina ?? "").toLowerCase().includes(term) ||
    (seal.gpnJohnCrane ?? "").toLowerCase().includes(term) ||
    seal.compatiblePumps.some((tag) => tag.toLowerCase().includes(term))
  );
}

// MWO-LTSA-041: Seal Registry now has a real backend, reached via
// GET /api/ltsa/seals (per MWO-LTSA-040's archaeology). `seals` remains an
// optional override prop -- when a caller passes it explicitly (every
// test in this file's "with injected data" block and the entire
// Seal.engineeringAI.test.jsx suite already do, neither mocking
// getSeals()), it is used directly and no fetch is triggered, preserving
// that existing coverage unchanged. When omitted (LTSAWorkspace.jsx
// renders <Seal /> with no prop, unchanged), this component fetches via
// getSeals() itself, mirroring Pump.jsx's loading/error/list pattern
// exactly, and maps each raw seal_registry record through mapSealRecord
// (utils/sealMapping.js) into the shape SealRegistryTable/SealDetailPanel
// already expect -- neither of those components changed.
export default function Seal({ seals: sealsProp, onNavigate }) {
  const [fetchedSeals, setFetchedSeals] = useState([]);
  const [listLoading, setListLoading] = useState(sealsProp === undefined);
  const [listError, setListError] = useState(null);
  // MWO-LTSA-042 -- Compatible Pumps and Stock, resolved from the real
  // seal-compatibility/seal-stock endpoints (MWO-LTSA-041 already wired
  // getSealCompatibility()/getSealStock() into ai5rClient.js; nothing
  // there changed). Fetched once, alongside getSeals() -- both are
  // full-list endpoints with no per-seal filter on the backend, so
  // fetching once and deriving per-seal client-side (resolveCompatiblePumps/
  // resolveStock, sealMapping.js) avoids an N-seal-times refetch, the same
  // "resolve once, derive many" shape filteredSeals' own useMemo already
  // uses below. Empty by default and only ever populated on the fetched
  // path (never for sealsProp, see the seals/stock derivations below) --
  // so every existing "with injected data" test, which supplies its own
  // compatiblePumps directly via sampleSeals.js, is unaffected.
  const [compatibilityRecords, setCompatibilityRecords] = useState([]);
  const [stockRecords, setStockRecords] = useState([]);

  useEffect(() => {
    if (sealsProp !== undefined) {
      return;
    }
    let active = true;
    Promise.all([getSeals(), getSealCompatibility().catch(() => []), getSealStock().catch(() => [])])
      .then(([records, compatibility, stock]) => {
        if (active) {
          setFetchedSeals(records.map(mapSealRecord));
          setCompatibilityRecords(compatibility);
          setStockRecords(stock);
          setListError(null);
        }
      })
      .catch(() => {
        if (active) {
          setListError("Seals could not be loaded.");
        }
      })
      .finally(() => {
        if (active) {
          setListLoading(false);
        }
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Compatible Pumps merged only into the fetched path -- sealsProp
  // (every test's fixture data) keeps its own compatiblePumps values
  // exactly as supplied, never overwritten by the (empty, in that path)
  // compatibilityRecords state.
  const mergedFetchedSeals = useMemo(
    () =>
      fetchedSeals.map((seal) => ({
        ...seal,
        compatiblePumps: resolveCompatiblePumps(seal.code, compatibilityRecords),
      })),
    [fetchedSeals, compatibilityRecords]
  );

  // MWO-LTSA-SEAL-INVENTORY-IDENTIFIERS-001 -- a successful manual
  // KIMAP/GPN edit is merged in here, on top of either data source
  // (sealsProp or the fetched path), so the UI reflects it immediately
  // without a full refetch. Keyed by seal code; empty by default, so
  // this is a pure no-op until an edit actually succeeds.
  const [identifierOverrides, setIdentifierOverrides] = useState({});

  const seals = useMemo(() => {
    const base = sealsProp !== undefined ? sealsProp : mergedFetchedSeals;
    if (Object.keys(identifierOverrides).length === 0) return base;
    return base.map((seal) =>
      identifierOverrides[seal.code] ? { ...seal, ...identifierOverrides[seal.code] } : seal
    );
  }, [sealsProp, mergedFetchedSeals, identifierOverrides]);

  // Session read via context, not a prop: LTSAWorkspace.jsx (confirmed
  // unrelated in-progress WIP, see useOptionalAuth's own header comment)
  // does not pass capabilities/session through to tab pages today, and
  // must not be edited here. useOptionalAuth() never throws when no
  // AuthProvider wraps this component (every existing "with injected
  // data" test renders <Seal seals={...} /> bare) -- can(undefined, ...)
  // already returns false in that case, so canEditIdentifiers is simply
  // false, matching this component's pre-existing behavior exactly.
  const authContext = useOptionalAuth();
  const canEditIdentifiers = can(authContext?.session, PERMISSIONS.MASTER_EDIT);

  async function handleUpdateIdentifiers(sealCode, { kimapPertamina, gpnJohnCrane }) {
    const result = await updateSealIdentifiers(sealCode, { kimapPertamina, gpnJohnCrane });
    const updated = result?.data;
    if (updated) {
      setIdentifierOverrides((prev) => ({
        ...prev,
        [sealCode]: {
          kimapPertamina: updated.kimap_pertamina ?? null,
          gpnJohnCrane: updated.gpn_john_crane ?? null,
          updatedBy: updated.updated_by ?? null,
          updatedAt: updated.updated_at ?? null,
        },
      }));
    }
    return updated;
  }

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedCode, setSelectedCode] = useState(null);

  const statusOptions = useMemo(
    () => [...new Set(seals.map((seal) => seal.status))],
    [seals]
  );

  const filteredSeals = useMemo(
    () =>
      seals.filter(
        (seal) =>
          matchesSearch(seal, search) &&
          (statusFilter === "ALL" || seal.status === statusFilter)
      ),
    [seals, search, statusFilter]
  );

  const selectedSeal = filteredSeals.find((seal) => seal.code === selectedCode) ?? null;
  const resolvedAssetCode = resolveAssetCode(selectedSeal);

  // MWO-LTSA-042 -- Stock, resolved the same way as Compatible Pumps
  // above: derived from the once-fetched stockRecords, never re-fetched
  // per selection. null (not a zeroed object) when the selected seal has
  // no seal_stock row, or when there is no selection yet -- resolveStock
  // itself already encodes "no row = unknown, never fabricated as zero".
  const selectedStock = selectedSeal ? resolveStock(selectedSeal.code, stockRecords) : null;

  // MWO-LTSA-042A -- "Terpasang di {pump} sejak {date}" (Open Design
  // Identity section) uses the real seal_pump_compatibility.created_at
  // for this exact seal/pump pair -- when the row's own compatibility
  // record was created, the only real "since" fact available. Not the
  // Open Design mockup's specific "12 Mar 2024" installation date (that
  // is illustrative placeholder content, per the spec's own Section 5),
  // and not seal_registry.createdAt either (that is the seal's own
  // registration date, a different fact from a specific pump pairing).
  const installedSince = useMemo(() => {
    if (!selectedSeal || !resolvedAssetCode) return null;
    const record = compatibilityRecords.find(
      (item) => item.seal_code === selectedSeal.code && item.pump_tag_number === resolvedAssetCode
    );
    return record?.created_at ? String(record.created_at).slice(0, 10) : null;
  }, [selectedSeal, resolvedAssetCode, compatibilityRecords]);

  // MWO-LTSA-042A -- Related Engineering (PM/CM/Work Orders), reusing
  // getPMSchedules()/getCMReports()/getWorkOrders() and
  // mapPMScheduleRecord/mapCMReportRecord/mapWorkOrderRecord exactly as
  // PM.jsx/CM.jsx/WorkOrder.jsx already do -- no new endpoint, no new
  // mapping. Filtered client-side by equipmentTag === resolvedAssetCode,
  // the same field every one of those mappers already derives from
  // asset_code. Never throws -- a failed fetch leaves the group empty
  // (rendered as an honest "no data" state by SealOpenDesignView), same
  // "degrade, never fabricate" discipline as the rest of this file.
  const [relatedPM, setRelatedPM] = useState([]);
  const [relatedCM, setRelatedCM] = useState([]);
  const [relatedWorkOrders, setRelatedWorkOrders] = useState([]);

  useEffect(() => {
    if (!resolvedAssetCode) {
      setRelatedPM([]); setRelatedCM([]); setRelatedWorkOrders([]);
      return undefined;
    }
    let active = true;
    Promise.all([
      getPMSchedules().catch(() => []),
      getCMReports().catch(() => []),
      getWorkOrders().catch(() => []),
    ]).then(([pm, cm, wo]) => {
      if (!active) return;
      setRelatedPM(pm.map(mapPMScheduleRecord).filter((item) => item.equipmentTag === resolvedAssetCode));
      setRelatedCM(cm.map(mapCMReportRecord).filter((item) => item.equipmentTag === resolvedAssetCode));
      setRelatedWorkOrders(wo.map(mapWorkOrderRecord).filter((item) => item.equipmentTag === resolvedAssetCode));
    });
    return () => { active = false; };
  }, [resolvedAssetCode]);

  // MWO-LTSA-042/042A -- Open Pump / Open Drawing reuse the exact same
  // onNavigate(key, context) mechanism every other cross-workspace link
  // in this codebase already uses (CMDetailPanel's "Related Pump":
  // onNavigate("pump", {selectId})). No new navigation pattern, no new
  // route -- these are the same "pump"/"drawing" tab keys
  // LTSAWorkspace.jsx already registers. Per-record PM/CM/Work Order
  // links (the standalone "PM History"/"CM History" Quick Actions
  // buttons MWO-LTSA-042 added) are superseded by the Open Design's own
  // Related Engineering reference-row groups (real per-record data,
  // rendered inline) -- not carried forward as separate buttons, since
  // the Open Design's own component hierarchy has no such buttons.
  function handleOpenPump(pumpTag) {
    onNavigate?.("pump", { selectId: pumpTag });
  }
  // MWO-LTSA-051A -- was onNavigate("drawing", {}), an incomplete cross
  // reference: Drawing Workspace's own real-data wiring needs
  // navContext.assetTag to know which pump's drawings to fetch (via the
  // existing getPumpKnowledge() path). resolvedAssetCode is the same
  // real, already-resolved pump tag handleOpenPump already uses -- no
  // new resolution logic, just passed through under the assetTag key
  // Drawing Workspace/DrawingNavigationPanel already use for this exact
  // navContext shape.
  function handleOpenDrawing() {
    onNavigate?.("drawing", { assetTag: resolvedAssetCode });
  }

  const [aiResponse, setAiResponse] = useState(null), [aiLoading, setAiLoading] = useState(false), [aiError, setAiError] = useState(null);

  useEffect(() => {
    if (!resolvedAssetCode) { setAiResponse(null); setAiError(null); setAiLoading(false); return; }
    let active = true;
    setAiLoading(true); setAiError(null); setAiResponse(null);
    postEngineeringAI({
      asset_code: resolvedAssetCode,
      intent: "summary",
      prompt_type: "summary",
      trace_id: generateTraceId(),
      workspace: "seal",
    })
      .then((response) => { if (active) setAiResponse(response); })
      .catch((error) => { if (active) setAiError(error?.message || "Engineering AI request failed"); })
      .finally(() => active && setAiLoading(false));
    return () => { active = false; };
  }, [resolvedAssetCode]);

  const aiBusinessError = aiResponse?.error ?? null;
  const aiReady = !aiLoading && !aiError && !!aiResponse && !aiBusinessError;
  // MWO-LTSA-044 P1 -- engineer-facing wording, same underlying meaning
  // (no resolvable LTSA-covered asset -> no AI request is made, unchanged
  // logic above): ties this message to the same "LTSA-covered asset"
  // language the new Contract Coverage card uses, instead of the more
  // technical "no compatible pump on record" phrasing.
  const aiStatusText = aiLoading
    ? "Generating seal summary…"
    : (aiError || aiBusinessError || (selectedSeal && !resolvedAssetCode
        ? "AI Recommendation is unavailable because this seal has not yet been associated with an LTSA-covered asset."
        : "Engineering AI has not run for this seal yet."));
  const aiStatusVariant = aiLoading ? "neutral" : (aiError || aiBusinessError) ? "critical" : aiReady ? (aiResponse.execution_status === "SUCCESS" ? "normal" : "attention") : "unavailable";
  const aiStatusLabel = aiLoading ? "Generating…" : (aiError || aiBusinessError) ? "Error" : aiReady ? aiResponse.execution_status : "Unavailable";

  return (
    <div>
      <PageHeader title="Seal Workspace" subtitle="LTSA Engineering — Mechanical Seal Registry" />

      <SealFilterBar
        searchValue={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statusOptions={statusOptions}
      />

      <div className="seal-workspace-layout">
        <div className="seal-workspace-registry">
          {listLoading ? (
            <Panel>
              <p>Loading seals...</p>
            </Panel>
          ) : listError ? (
            <Panel>
              <p role="alert">{listError}</p>
            </Panel>
          ) : seals.length === 0 ? (
            <EmptyState
              title="No seals available"
              description="The Seal Registry has no backend data source yet."
            />
          ) : (
            <SealRegistryTable
              seals={filteredSeals}
              selectedCode={selectedCode}
              onSelect={setSelectedCode}
            />
          )}
        </div>

        <div className="seal-workspace-detail">
          {selectedSeal ? (
            <SealOpenDesignView
              seal={selectedSeal}
              stock={selectedStock}
              resolvedAssetCode={resolvedAssetCode}
              installedSince={installedSince}
              pmRecords={relatedPM}
              cmRecords={relatedCM}
              workOrderRecords={relatedWorkOrders}
              canEditIdentifiers={canEditIdentifiers}
              onUpdateIdentifiers={handleUpdateIdentifiers}
              onOpenPump={handleOpenPump}
              onOpenDrawing={handleOpenDrawing}
              aiResponse={aiResponse}
              aiReady={aiReady}
              aiStatusText={aiStatusText}
              aiStatusVariant={aiStatusVariant}
              aiStatusLabel={aiStatusLabel}
            />
          ) : (
            <EmptyState
              title="No seal selected"
              description="Select a seal from the registry table to view its details."
            />
          )}
        </div>
      </div>

      <PhysicalSealWorkspace sealTypes={seals} />
    </div>
  );
}
