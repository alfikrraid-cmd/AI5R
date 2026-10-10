import React, { useEffect, useState } from "react";
import { getPumpCurrentInstallation } from "../../../api/ai5rClient";
import "./CurrentInstallationCard.css";

// LTSA_CURRENT_INSTALLATION_ASSET360_UI_R4 -- Authoritative Current Mechanical
// Seal Installation Component. Consumes GET /api/ltsa/pumps/{tag}/current-installation.
// Strictly separates:
// - Configured / Design Seal (from pump master data)
// - Current Installed Seal (authoritative installation records only)
// Never labels configured seal as installed seal; never uses compatibility or
// drawing registry as fallback for Current Installation.
// Side-by-side DE and NDE physical positions for BB equipment; single block for OH/SINGLE.
// Neutral indicator when installed variant differs from configured design.

const NOT_RECORDED = "Not Recorded";

function Row({ label, value, fallback = NOT_RECORDED, testId }) {
  return (
    <div className="info-row" data-testid={testId}>
      <span className="k">{label}</span>
      <span className="v">{value ?? fallback}</span>
    </div>
  );
}

function normalize(str) {
  return str ? String(str).trim().toLowerCase() : "";
}

function findMatchingDrawing(drawingNo, drawings = []) {
  if (!drawingNo) return null;
  const target = normalize(drawingNo);
  return (
    drawings.find((d) => {
      const docNum = normalize(d.documentNumber);
      const id = normalize(d.id);
      const docCode = normalize(d.document_code);
      const drawingNum = normalize(d.drawing_number);
      return docNum === target || id === target || docCode === target || drawingNum === target;
    }) ?? null
  );
}

function DrawingRefField({ drawingNo, drawings = [], onNavigate, tag }) {
  if (!drawingNo) {
    return <Row label="Drawing Ref" value="—" testId="installed-drawing-ref" />;
  }
  const match = findMatchingDrawing(drawingNo, drawings);
  if (match) {
    return (
      <div className="info-row" data-testid="installed-drawing-ref">
        <span className="k">Drawing Ref</span>
        <span className="v drawing-action-group">
          <span className="drawing-code">{drawingNo}</span>
          <button
            type="button"
            className="btn-link drawing-viewer-btn"
            onClick={() =>
              onNavigate?.("drawing", {
                assetTag: tag,
                drawingId: match.id || match.documentNumber || match.document_code || drawingNo,
              })
            }
          >
            View Drawing
          </button>
        </span>
      </div>
    );
  }
  return (
    <div className="info-row" data-testid="installed-drawing-ref">
      <span className="k">Drawing Ref</span>
      <span className="v">{`${drawingNo} (reference only)`}</span>
    </div>
  );
}

function PositionBlock({
  positionKey,
  positionData,
  configuredSeal,
  drawings,
  onNavigate,
  tag,
}) {
  const isConfirmed =
    positionData?.resolution_status === "CONFIRMED" && positionData?.installed_seal != null;
  const seal = positionData?.installed_seal || {};
  const sealType = seal.seal_type || positionData?.seal_type;
  const sealSize = seal.seal_size || positionData?.seal_size;
  const sourceRef = positionData?.source_reference;
  const sourceDate =
    positionData?.source_date ||
    (positionData?.installed_at ? String(positionData.installed_at).slice(0, 10) : null);
  const drawingNo = seal.drawing_no || positionData?.drawing_no;
  const assemblyGpn = seal.assembly_gpn || positionData?.assembly_gpn;
  const materialCode = seal.material_code || positionData?.material_code;

  const configuredType = configuredSeal?.sealType;
  const isDifferent =
    Boolean(configuredType) &&
    Boolean(sealType) &&
    normalize(configuredType) !== normalize(sealType);

  const testIdKey = positionKey.toLowerCase();

  if (!isConfirmed) {
    return (
      <div className="position-block is-empty" data-testid={`position-${testIdKey}`}>
        <div className="position-header">
          <h5 className="position-title">Position {positionKey}</h5>
          <span className="status-signal not-recorded" data-testid={`position-status-${testIdKey}`}>
            <span className="dot-lg" />
            Not recorded
          </span>
        </div>
        <p className="position-subtext">No authoritative current installation record is available.</p>
      </div>
    );
  }

  return (
    <div className="position-block is-confirmed" data-testid={`position-${testIdKey}`}>
      <div className="position-header">
        <div className="position-title-group">
          <h5 className="position-title">Position {positionKey}</h5>
          {isDifferent && (
            <span className="seal-diff-badge" data-testid="configured-diff-indicator">
              Different from configured design
            </span>
          )}
        </div>
        <span className="status-signal confirmed" data-testid={`position-status-${testIdKey}`}>
          <span className="dot-lg" />
          Confirmed
        </span>
      </div>

      <div className="position-rows">
        <Row label="Position" value={positionKey} />
        <Row label="Installation Status" value="Confirmed" />
        <Row label="Installed Seal Type" value={sealType} testId="installed-seal-type" />
        <Row label="Installed Seal Size" value={sealSize} testId="installed-seal-size" />
        <Row label="Installed Date" value={sourceDate} testId="installed-date" />
        <DrawingRefField drawingNo={drawingNo} drawings={drawings} onNavigate={onNavigate} tag={tag} />
        {assemblyGpn ? <Row label="Assembly GPN" value={assemblyGpn} testId="installed-assembly-gpn" /> : null}
        {materialCode ? <Row label="Material Code" value={materialCode} testId="installed-material-code" /> : null}
        <Row label="Evidence" value="Installation Report" />
        <Row label="Source Reference" value={sourceRef} testId="installed-source-ref" />
      </div>
    </div>
  );
}

export default function CurrentInstallationCard({
  tag,
  configuredSeal,
  drawings = [],
  onNavigate,
  data: propData,
  currentInstallationData,
  loading: propLoading,
  error: propError,
}) {
  const initialData = propData !== undefined ? propData : currentInstallationData;
  const [state, setState] = useState({
    data: initialData ?? null,
    loading: propLoading ?? (!initialData && Boolean(tag)),
    error: propError ?? null,
    tag: tag ?? null,
  });

  useEffect(() => {
    if (initialData !== undefined) {
      setState({
        data: initialData,
        loading: propLoading ?? false,
        error: propError ?? null,
        tag,
      });
      return;
    }

    if (!tag) {
      setState({ data: null, loading: false, error: null, tag: null });
      return;
    }

    // Stale state protection: clear old data immediately when tag changes
    setState({ data: null, loading: true, error: null, tag });

    let active = true;
    if (typeof getPumpCurrentInstallation !== "function") {
      setState({ data: null, loading: false, error: null, tag });
      return;
    }

    getPumpCurrentInstallation(tag)
      .then((res) => {
        if (!active) return;
        setState({ data: res?.data ?? res, loading: false, error: null, tag });
      })
      .catch((err) => {
        if (!active) return;
        setState({
          data: null,
          loading: false,
          error: err?.message || "Current installation unavailable",
          tag,
        });
      });

    return () => {
      active = false;
    };
  }, [tag, initialData, propLoading, propError]);

  const currentData = initialData !== undefined ? initialData : state.data;
  const isLoading = propLoading !== undefined ? propLoading : (initialData === undefined && state.loading);
  const currentError = propError !== undefined ? propError : (initialData === undefined && state.error);

  if (isLoading) {
    return (
      <div className="current-installation-card is-loading" data-testid="current-installation-loading">
        <div className="skel skel-text skel-line-sm" />
        <div className="skel skel-text skel-line-lg" />
        <div className="skel skel-text skel-line-md" />
      </div>
    );
  }

  if (currentError) {
    return (
      <div className="current-installation-card is-error" data-testid="current-installation-error">
        <div className="status-signal critical">
          <span className="dot-lg" />
          Current installation unavailable
        </div>
        <p className="notice-text">{currentError}</p>
      </div>
    );
  }

  const positionsMap = currentData?.positions || {};
  const confirmedPositions = Object.entries(positionsMap).filter(
    ([_, pos]) => pos?.resolution_status === "CONFIRMED" && pos?.installed_seal != null
  );

  const hasReviewEvidence =
    currentData?.status === "REVIEW_REQUIRED" ||
    (Array.isArray(currentData?.unpositioned_evidence) && currentData.unpositioned_evidence.length > 0) ||
    Object.values(positionsMap).some(
      (pos) => pos?.resolution_status === "REVIEW_REQUIRED" || pos?.resolution_status === "CONFLICT"
    );

  const pumpType = (currentData?.pump_type || "").toUpperCase();
  const isBB = pumpType.includes("BB") || "DE" in positionsMap || "NDE" in positionsMap;

  // Case 1: Review or Conflict (and no confirmed positions)
  if (confirmedPositions.length === 0 && hasReviewEvidence) {
    return (
      <div className="current-installation-card is-review" data-testid="current-installation-review">
        <div className="current-installation-header">
          <h4 className="knowledge-seal-subhead">Current Installed Seal</h4>
          <span className="status-signal attention" data-testid="current-installation-status">
            <span className="dot-lg" />
            Not confirmed
          </span>
        </div>
        <div className="current-installation-empty-notice">
          <p className="notice-text">Installation evidence requires review.</p>
        </div>
      </div>
    );
  }

  // Case 2: No Current Record (empty pump, no authoritative records)
  if (confirmedPositions.length === 0) {
    return (
      <div className="current-installation-card is-empty" data-testid="current-installation-empty">
        <div className="current-installation-header">
          <h4 className="knowledge-seal-subhead">Current Installed Seal</h4>
          <span className="status-signal not-recorded" data-testid="current-installation-status">
            <span className="dot-lg" />
            Not recorded
          </span>
        </div>
        <div className="current-installation-empty-notice">
          <p className="notice-text">No authoritative current installation record is available.</p>
        </div>
      </div>
    );
  }

  // Overall status badge for confirmed/partial
  let overallStatusLabel = "Confirmed";
  let overallStatusClass = "confirmed";
  if (isBB && confirmedPositions.length < 2) {
    overallStatusLabel = "Partial";
    overallStatusClass = "attention";
  }

  // Case 3: BB Equipment (DE & NDE)
  if (isBB) {
    const dePos = positionsMap["DE"] || { equipment_side: "DE", resolution_status: "NO_AUTHORITATIVE_EVIDENCE", installed_seal: null };
    const ndePos = positionsMap["NDE"] || { equipment_side: "NDE", resolution_status: "NO_AUTHORITATIVE_EVIDENCE", installed_seal: null };

    return (
      <div className="current-installation-card" data-testid="current-installation-card">
        <div className="current-installation-header">
          <h4 className="knowledge-seal-subhead">Current Installed Seal</h4>
          <span className={`status-signal ${overallStatusClass}`} data-testid="current-installation-status">
            <span className="dot-lg" />
            {overallStatusLabel}
          </span>
        </div>
        <div className="positions-grid">
          <PositionBlock
            positionKey="DE"
            positionData={dePos}
            configuredSeal={configuredSeal}
            drawings={drawings}
            onNavigate={onNavigate}
            tag={tag}
          />
          <PositionBlock
            positionKey="NDE"
            positionData={ndePos}
            configuredSeal={configuredSeal}
            drawings={drawings}
            onNavigate={onNavigate}
            tag={tag}
          />
        </div>
      </div>
    );
  }

  // Case 4: SINGLE Equipment
  const singlePos = positionsMap["SINGLE"] || Object.values(positionsMap)[0] || {};
  return (
    <div className="current-installation-card" data-testid="current-installation-card">
      <div className="current-installation-header">
        <h4 className="knowledge-seal-subhead">Current Installed Seal</h4>
        <span className="status-signal confirmed" data-testid="current-installation-status">
          <span className="dot-lg" />
          Confirmed
        </span>
      </div>
      <div className="positions-single">
        <PositionBlock
          positionKey="SINGLE"
          positionData={singlePos}
          configuredSeal={configuredSeal}
          drawings={drawings}
          onNavigate={onNavigate}
          tag={tag}
        />
      </div>
    </div>
  );
}

