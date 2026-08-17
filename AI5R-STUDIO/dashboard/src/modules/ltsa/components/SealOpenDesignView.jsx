import { useState } from "react";
import PumpWorkspaceDrawer from "./PumpWorkspaceDrawer";
import { Section, InfoRow, StatusSignal, RailSection, ActionBar, RefGroup } from "./open-design";
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
} from "./engineering-ai";

/**
 * MWO-LTSA-042A -- Mechanical Seal Workspace, rebuilt to match the approved
 * Open Design. ChromeBar, Identity/Hero, Compatibility/Related Engineering
 * (RefGroup-based), sticky Inspector Rail, sticky Action Bar, a Drawer
 * (reused from PumpWorkspaceDrawer.jsx), and a Toast.
 *
 * Data discipline (never fabricate): every group/field below either shows
 * real, already-fetched data or an honest empty state -- never the Open
 * Design mockup's own illustrative placeholder content.
 *
 * MWO-LTSA-044/045/046/047/048 -- UX polish + reorg passes: Contract
 * Coverage/LTSA Coverage card, lighter/shorter empty states, denser
 * Hero/rail/section rhythm, Engineering AI in a bordered .info-panel,
 * workflow-oriented section reorder (Current Status card, Hero grouped
 * into Identity/Technical, Engineering Overview promoted, Engineering
 * Recommendation collapse-when-empty, Engineering AI Reason/Required
 * Action), Engineering Context section, RefGroup emptyReason.
 *
 * MWO-LTSA-050 -- Pump Workspace migrated to the same hierarchy
 * (PumpOpenDesignView.jsx), sharing LTSAOpenDesign.css (renamed from
 * Seal.opendesign.css, .seal-open-design -> .ltsa-open-design).
 *
 * MWO-LTSA-050B -- LTSA Open Design Kit: Section/InfoRow/StatusSignal/
 * RailSection/ActionBar/RefGroup extracted to components/open-design/
 * (Priority 1 patterns only, proven identical or near-identical between
 * this file and PumpOpenDesignView.jsx -- see the archaeology report).
 * Every replacement below preserves the exact prior markup/classes/text;
 * this is a refactor, not a redesign -- no visual or behavioral change.
 * RefGroup's own local definition is gone (was byte-identical to
 * Pump's copy); the two group-array `emptyReason` derivations and all
 * seal-specific data/logic are unchanged.
 */

const STATUS_META = {
  ACTIVE: { tier: "normal", label: "Sesuai Spesifikasi" },
  STANDBY: { tier: "attention", label: "Dipantau" },
  MAINTENANCE: { tier: "attention", label: "Dipantau" },
  ALERT: { tier: "high", label: "Mendekati Batas Layanan" },
  FAULT: { tier: "critical", label: "Segera Ganti" },
};

function statusMeta(status) {
  return STATUS_META[status] || { tier: "neutral", label: status || "Tidak Diketahui" };
}

// Lifecycle Stepper stage derived from the same real `status` field --
// a presentation mapping (like statusBadgeVariant/criticalityBadgeVariant
// elsewhere in this codebase), not a new fabricated data point. Seal-only
// (see PumpOpenDesignView.jsx's own header comment for why Pump has none)
// -- stays local, not part of the shared kit.
const LIFECYCLE_STEPS = [
  { id: "installed", label: "Dipasang" },
  { id: "inservice", label: "Masa Pakai Normal" },
  { id: "monitor", label: "Dipantau" },
  { id: "endoflife", label: "Akhir Masa Pakai" },
];

function lifecycleCurrentIndex(status) {
  if (status === "FAULT") return 3;
  if (status === "ALERT" || status === "STANDBY" || status === "MAINTENANCE") return 2;
  return 1;
}

export default function SealOpenDesignView({
  seal,
  stock,
  resolvedAssetCode,
  installedSince,
  pmRecords = [],
  cmRecords = [],
  workOrderRecords = [],
  onOpenPump,
  onOpenDrawing,
  aiResponse,
  aiReady,
  aiStatusText,
  aiStatusVariant,
  aiStatusLabel,
}) {
  const [drawer, setDrawer] = useState(null); // null | "drawing" | "recommendation"
  const [toast, setToast] = useState(null);
  const [reviewed, setReviewed] = useState(false);

  function showToast(message) {
    setToast(message);
    setTimeout(() => setToast(null), 2600);
  }

  const meta = statusMeta(seal.status);

  const coverageMeta = resolvedAssetCode
    ? { tier: "normal", label: "LTSA Covered", message: "Linked to an LTSA-covered pump." }
    : { tier: "neutral", label: "Outside LTSA Contract", message: "Outside active LTSA scope." };

  const requiredAction =
    !resolvedAssetCode && aiStatusVariant === "unavailable"
      ? "Associate this seal with an LTSA-covered asset."
      : null;

  const ltsaEmptyReason = "No LTSA association";
  const dataEmptyReason = "No engineering data";

  const compatibilityGroups = [
    {
      id: "pumps",
      title: "Compatible Pumps",
      items: seal.compatiblePumps.map((tag) => ({ key: tag, name: tag, flagLabel: "Kompatibel" })),
      emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason,
    },
    { id: "plans", title: "Compatible API Plans", items: [], emptyReason: dataEmptyReason },
    { id: "services", title: "Compatible Services", items: [], emptyReason: dataEmptyReason },
    {
      id: "materials",
      title: "Compatible Materials",
      items: seal.material ? [{ key: "material", name: seal.material, flagLabel: "Terdaftar" }] : [],
      emptyReason: dataEmptyReason,
    },
    {
      id: "replacements",
      title: "Compatible Replacements",
      items: seal.compatibleSeals.map((code) => ({ key: code, name: code, flagLabel: "Kompatibel" })),
      emptyReason: dataEmptyReason,
    },
  ];

  const relatedGroups = [
    {
      id: "pm",
      title: "Related PM",
      items: pmRecords.map((pm) => ({ key: pm.id, name: pm.id, meta: pm.nextDue ? `Jatuh tempo ${pm.nextDue}` : pm.procedure, flagLabel: pm.status })),
      emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason,
    },
    { id: "cm", title: "Related Condition Monitoring", items: [], emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason },
    { id: "fa", title: "Related Failure Analysis", items: [], emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason },
    {
      id: "cm-reports",
      title: "Related CM Reports",
      items: cmRecords.map((cm) => ({ key: cm.id, name: cm.id, meta: cm.failureDescription, flagLabel: cm.status })),
      emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason,
    },
    {
      id: "wo",
      title: "Related Work Orders",
      items: workOrderRecords.map((wo) => ({ key: wo.id, name: wo.id, meta: wo.title, flagLabel: wo.status })),
      emptyReason: !resolvedAssetCode ? ltsaEmptyReason : dataEmptyReason,
    },
  ];

  const preferredReplacement = seal.compatibleSeals[0]
    ? { name: seal.compatibleSeals[0], meta: "Interchange tercatat pada Seal Registry" }
    : null;

  return (
    <div className="ltsa-open-design" data-testid="seal-open-design">
      <div className="chrome-bar" data-od-id="chrome-bar">
        <div className="chrome-inner">
          <div className="crumb">
            {resolvedAssetCode ? (
              <button type="button" className="crumb-link" onClick={() => onOpenPump?.(resolvedAssetCode)} data-od-id="crumb-pump-link">
                {resolvedAssetCode}
              </button>
            ) : (
              <span>Outside LTSA</span>
            )}
            <span className="sep">›</span><span>Mechanical Seal</span>
            <span className="sep">›</span><b>{seal.code}</b>
          </div>
        </div>
      </div>

      <div className="workspace-grid">
        <main className="object-column">
          <section className="identity" data-od-id="identity-section">
            <h1>{seal.name}</h1>
            <div className="identity-status">
              <StatusSignal tier={meta.tier} label={meta.label} />
              {resolvedAssetCode && (
                <span className="running-line">
                  <span className="dot-sm" />
                  {installedSince ? `Terpasang di ${resolvedAssetCode} sejak ${installedSince}` : `Terpasang di ${resolvedAssetCode}`}
                </span>
              )}
              {stock && (
                <span className="running-line">
                  <span className="dot-sm" />
                  Stock: {stock.quantityOnHand ?? "—"}
                </span>
              )}
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Identity</div>
              <InfoRow label="Code" value={seal.code} valueClassName="mono" />
              <InfoRow label="Manufacturer" value={seal.manufacturer ?? "—"} />
              <InfoRow label="Model" value={seal.model ?? "—"} />
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Technical</div>
              <InfoRow label="Seal Type" value={seal.type ?? "—"} />
              <InfoRow label="Material" value={seal.material ?? "—"} />
              <InfoRow label="Shaft" value={seal.shaftSize != null ? `${seal.shaftSize} mm` : "—"} />
              <InfoRow label="Operating Temperature" value={seal.temperatureLimit != null ? `${seal.temperatureLimit}°C` : "—"} />
            </div>
          </section>

          <Section id="engineering-overview-section" title="Seal Engineering Overview">
            <div className="assessment-columns" style={{ marginTop: "var(--space-3)" }}>
              <div>
                <div className="eyebrow">Operating Limits</div>
                <InfoRow label="Suhu Operasi" value={seal.temperatureLimit != null ? `${seal.temperatureLimit}°C` : "—"} />
                <InfoRow label="Tekanan Maks." value={seal.pressureLimit != null ? `${seal.pressureLimit} bar` : "—"} />
              </div>
              <div>
                <div className="eyebrow">Materials &amp; Construction</div>
                <InfoRow label="Material" value={seal.material ?? "—"} />
                <InfoRow label="Shaft Size" value={seal.shaftSize ?? "—"} />
              </div>
            </div>
          </Section>

          <Section id="current-status-section" title="Current Status">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              <InfoRow label="Stock" value={stock ? (stock.quantityOnHand ?? "Unknown") : "Unknown"} />
              <InfoRow label="Coverage" value={coverageMeta.label} />
            </div>
          </Section>

          <Section id="coverage-section" title="LTSA Coverage">
            <div className="identity-status" style={{ marginTop: "var(--space-3)" }}>
              <StatusSignal tier={coverageMeta.tier} label={coverageMeta.label} />
            </div>
            <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>{coverageMeta.message}</p>
            {!resolvedAssetCode && (
              <>
                <div className="confidence-label" style={{ fontWeight: 600, marginTop: "var(--space-2)", marginBottom: "var(--space-1)" }}>Unavailable</div>
                <ul style={{ margin: 0, paddingLeft: "var(--space-4)" }}>
                  <li className="confidence-label">PM History</li>
                  <li className="confidence-label">Engineering AI</li>
                  <li className="confidence-label">Asset Analytics</li>
                </ul>
              </>
            )}
          </Section>

          <Section id="engineering-context-section" title="Engineering Context">
            <div style={{ marginTop: "var(--space-2)" }}>
              <InfoRow label="Engineering Reference" value={seal.engineeringReference ?? "Unknown"} />
              <InfoRow label="Equipment Type" value={seal.equipmentType ?? "Unknown"} />
              <InfoRow label="LTSA Coverage" value={coverageMeta.label} />
            </div>
          </Section>

          <Section id="stock-section" title="Stock Status">
            <div style={{ marginTop: "var(--space-2)" }}>
              {stock ? (
                <>
                  <InfoRow label="Quantity On Hand" value={stock.quantityOnHand ?? "Unknown"} />
                  <InfoRow label="Reorder Point" value={stock.reorderPoint ?? "—"} />
                  <InfoRow label="Location" value={stock.location ?? "—"} />
                </>
              ) : (
                <>
                  <InfoRow label="Inventory Status" value="Unknown" valueClassName="ref-group-empty" />
                  <InfoRow label="Warehouse" value="Unknown" valueClassName="ref-group-empty" />
                  <InfoRow label="ETA" value="Unknown" valueClassName="ref-group-empty" />
                </>
              )}
            </div>
          </Section>

          <Section id="recommended-replacement-section" title="Engineering Recommendation">
            {seal.recommendation ? (
              <>
                <h2 className="assessment-headline">{seal.recommendation}</h2>
                {preferredReplacement && (
                  <RefGroup title="Preferred Seal" items={[{ ...preferredReplacement, flag: "ok", flagLabel: "Direkomendasikan" }]} />
                )}
                <div className="assessment-footer">
                  <StatusSignal tier={meta.tier} label={meta.label} />
                  <button type="button" className="btn-link" onClick={() => setDrawer("recommendation")} data-od-id="cta-generate-recommendation">
                    Lihat detail rekomendasi →
                  </button>
                </div>
              </>
            ) : (
              <p className="confidence-label" style={{ marginTop: "var(--space-2)" }}>No recommendation available.</p>
            )}
          </Section>

          <Section id="engineering-ai-section" title="Engineering AI">
            <div className="info-panel" style={{ marginTop: "var(--space-3)" }}>
              {aiReady ? (
                <>
                  <EngineeringAIStatus response={aiResponse} />
                  <EngineeringAISummary response={aiResponse} />
                  <EngineeringAIProviderInfo response={aiResponse} />
                  <EngineeringAIConfidence response={aiResponse} />
                  <EngineeringAIRisk response={aiResponse} />
                  <EngineeringAIRemainingLife response={aiResponse} />
                </>
              ) : (
                <>
                  <StatusSignal tier={aiStatusVariant} label={aiStatusLabel} dot={false} />
                  <div style={{ marginTop: "var(--space-2)" }}>
                    <InfoRow label="Reason" value={!resolvedAssetCode ? coverageMeta.label : aiStatusText} />
                    {requiredAction && <InfoRow label="Required Action" value={requiredAction} />}
                  </div>
                </>
              )}
            </div>
          </Section>
          {aiReady && <EngineeringAIFindings response={aiResponse} />}
          {aiReady && <EngineeringAIEvidence response={aiResponse} />}
          {aiReady && <EngineeringAIRecommendation response={aiResponse} />}
          {aiReady && <EngineeringAISourceReferences response={aiResponse} />}

          <Section id="compatibility-section" title="Compatibility">
            <div style={{ marginTop: "var(--space-3)" }}>
              {compatibilityGroups.map((g) => (
                <RefGroup key={g.id} title={g.title} items={g.items} emptyReason={g.emptyReason} />
              ))}
            </div>
          </Section>

          <Section id="related-engineering-section" title="Related Engineering">
            <div style={{ marginTop: "var(--space-3)" }}>
              {relatedGroups.map((g) => (
                <RefGroup key={g.id} title={g.title} items={g.items} emptyReason={g.emptyReason} />
              ))}
            </div>
          </Section>

          {/* Documents deliberately keeps raw markup -- its eyebrow sits
              inside .section-head alongside a button, deviating from the
              generic Section shape (see the archaeology report). */}
          <section className="assessment-section" data-od-id="documents-section">
            <div className="section-head">
              <span className="eyebrow">Documents</span>
              <button
                type="button"
                className="btn-link"
                onClick={() => { onOpenDrawing?.(); setDrawer("drawing"); }}
                data-od-id="open-drawing-link"
              >
                Buka Drawing →
              </button>
            </div>
            <div style={{ marginTop: "var(--space-2)" }}>
              <div className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>Document Types</div>
              <InfoRow label="Drawing" value="—" valueClassName="ref-group-empty" />
              <InfoRow label="Datasheet" value="—" valueClassName="ref-group-empty" />
              <InfoRow label="Installation Procedure" value="—" valueClassName="ref-group-empty" />
              <InfoRow label="Certificates" value="—" valueClassName="ref-group-empty" />
              <InfoRow label="Revision History" value="—" valueClassName="ref-group-empty" />
            </div>
          </section>
        </main>

        <aside className="inspector-rail" data-od-id="inspector-rail">
          <RailSection id="seal-health-section" title="Seal Health">
            <StatusSignal tier={meta.tier} label={meta.label} />
          </RailSection>

          <RailSection id="lifecycle-section" title="Lifecycle">
            <div className="stepper" data-od-id="lifecycle-stepper">
              {LIFECYCLE_STEPS.map((step, i) => {
                const currentIndex = lifecycleCurrentIndex(seal.status);
                const state = i < currentIndex ? "done" : i === currentIndex ? "current" : "upcoming";
                return (
                  <div className="step-item" key={step.id} data-state={state}>
                    <span className="step-dot" />
                    <div className="step-label">{step.label}</div>
                  </div>
                );
              })}
            </div>
          </RailSection>

          <RailSection id="criticality-section" title="Criticality">
            <div className="confidence-label ref-group-empty">Belum ada data kritikalitas.</div>
          </RailSection>

          <RailSection id="recommendation-section" title="Recommendation">
            <div className="confidence-label">{seal.recommendation || "Belum ada rekomendasi."}</div>
          </RailSection>

          <RailSection id="recent-activities-section" title="Recent Activities">
            <div className="confidence-label ref-group-empty">Belum ada aktivitas terbaru.</div>
          </RailSection>
        </aside>
      </div>

      <ActionBar
        label={`${seal.code} · ${meta.label}`}
        metaPrimary={coverageMeta.label}
        metaLabel="Stock"
        metaValue={stock ? (stock.quantityOnHand ?? "Unknown") : "Unknown"}
      >
        {resolvedAssetCode && (
          <button type="button" className="btn-link" onClick={() => onOpenPump?.(resolvedAssetCode)} data-od-id="action-bar-open-pump">
            Buka Pump →
          </button>
        )}
        <button type="button" className="btn-primary" onClick={() => setDrawer("recommendation")} data-od-id="action-bar-generate-recommendation">
          Buat Rekomendasi
        </button>
      </ActionBar>

      <PumpWorkspaceDrawer open={drawer === "drawing"} onClose={() => setDrawer(null)} title="Seal Drawing">
        <div className="drawing-thumb" />
        <p>Belum ada data drawing — Drawing Workspace belum memiliki backend.</p>
      </PumpWorkspaceDrawer>

      <PumpWorkspaceDrawer open={drawer === "recommendation"} onClose={() => setDrawer(null)} title="Generate Recommendation">
        <p>{seal.recommendation || "Belum ada rekomendasi engineering."}</p>
        {preferredReplacement && (
          <RefGroup title="Preferred Seal" items={[{ ...preferredReplacement, flag: "ok", flagLabel: "Direkomendasikan" }]} />
        )}
        {reviewed ? (
          <p style={{ color: "var(--status-normal)" }}>Rekomendasi ditandai sudah ditinjau.</p>
        ) : (
          <button
            type="button"
            className="btn-primary"
            style={{ marginTop: "var(--space-2)" }}
            onClick={() => { setReviewed(true); showToast("Rekomendasi ditandai sudah ditinjau"); }}
            data-od-id="mark-reviewed-btn"
          >
            Tandai Sudah Ditinjau
          </button>
        )}
      </PumpWorkspaceDrawer>

      <div className="toast" data-open={!!toast} data-od-id="toast">
        {toast}
      </div>
    </div>
  );
}
