import { useCallback, useEffect, useRef, useState } from "react";
import { Badge, Button, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { getDrawingContentBlob } from "../../../api/ai5rClient";
import { drawingStatusBadgeVariant } from "../utils/drawingMapping";

const ZOOM_MIN = 25;
const ZOOM_MAX = 400;
const ZOOM_STEP = 10;

export default function DrawingViewerPanel({ drawing }) {
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [panMode, setPanMode] = useState(false);
  const [blobUrl, setBlobUrl] = useState(null);
  const [blobContentType, setBlobContentType] = useState(null);
  const [blobFilename, setBlobFilename] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copiedLink, setCopiedLink] = useState(false);

  const currentUrlRef = useRef(null);

  const documentCode = drawing?.documentCode || drawing?.id;
  const storageAvailable = Boolean(drawing?.storageAvailable);

  const fetchContent = useCallback(async () => {
    if (!documentCode || !storageAvailable) {
      if (currentUrlRef.current) {
        URL.revokeObjectURL(currentUrlRef.current);
        currentUrlRef.current = null;
      }
      setBlobUrl(null);
      setBlobContentType(null);
      setBlobFilename(null);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const { url, contentType, filename } = await getDrawingContentBlob(documentCode);
      if (currentUrlRef.current) {
        URL.revokeObjectURL(currentUrlRef.current);
      }
      currentUrlRef.current = url;
      setBlobUrl(url);
      setBlobContentType(contentType);
      setBlobFilename(filename);
      setLoading(false);
    } catch (err) {
      setError(err?.detail || err?.message || "Failed to load drawing file");
      setLoading(false);
    }
  }, [documentCode, storageAvailable]);

  useEffect(() => {
    fetchContent();

    return () => {
      if (currentUrlRef.current) {
        URL.revokeObjectURL(currentUrlRef.current);
        currentUrlRef.current = null;
      }
    };
  }, [fetchContent]);

  // Reset zoom & rotation when drawing changes
  useEffect(() => {
    setZoom(100);
    setRotation(0);
    setPanMode(false);
  }, [documentCode]);

  const handleDownload = () => {
    if (!blobUrl) return;
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = blobFilename || `${drawing.drawingNumber || "drawing"}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handlePrint = () => {
    if (!blobUrl) return;
    const printWindow = window.open(blobUrl, "_blank");
    if (printWindow) {
      printWindow.focus();
    }
  };

  const handleCopyDeepLink = () => {
    const url = `${window.location.origin}/ltsa/drawing?tag=${encodeURIComponent(
      drawing.equipmentTag || ""
    )}&drawing=${encodeURIComponent(drawing.drawingNumber || documentCode || "")}`;
    navigator.clipboard?.writeText(url).then(() => {
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    });
  };

  if (!drawing) {
    return (
      <Card title="Drawing Viewer">
        <EmptyState
          title="No drawing selected"
          description="Choose an equipment tag or drawing from the library."
        />
      </Card>
    );
  }

  const isPdf =
    blobContentType === "application/pdf" ||
    (drawing.fileName && drawing.fileName.toLowerCase().endsWith(".pdf"));
  const isImage =
    blobContentType?.startsWith("image/") ||
    (drawing.fileName && /\.(png|jpe?g)$/i.test(drawing.fileName));
  const isCad =
    drawing.fileName && /\.(dwg|dxf|step|stp)$/i.test(drawing.fileName);

  return (
    <Card title="Drawing Viewer">
      {/* Viewer Toolbar */}
      <div
        role="toolbar"
        aria-label="Drawing viewer toolbar"
        style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs, marginBottom: spacing.sm, alignItems: "center" }}
      >
        <Button
          onClick={() => setZoom((current) => Math.max(ZOOM_MIN, current - ZOOM_STEP))}
          disabled={!storageAvailable || zoom <= ZOOM_MIN || loading}
        >
          Zoom Out
        </Button>
        <span aria-live="polite" style={{ alignSelf: "center", color: colors.textMuted, fontSize: 12, minWidth: 40, textAlign: "center" }}>
          {zoom}%
        </span>
        <Button
          onClick={() => setZoom((current) => Math.min(ZOOM_MAX, current + ZOOM_STEP))}
          disabled={!storageAvailable || zoom >= ZOOM_MAX || loading}
        >
          Zoom In
        </Button>

        <Button
          onClick={() => {
            setZoom(100);
            setRotation(0);
          }}
          disabled={!storageAvailable || loading}
        >
          Reset
        </Button>

        <Button
          onClick={() => setRotation((current) => (current + 90) % 360)}
          disabled={!storageAvailable || loading}
        >
          Rotate
        </Button>

        <Button
          onClick={() => setPanMode((current) => !current)}
          disabled={!storageAvailable || loading}
        >
          {panMode ? "Pan: On" : "Pan: Off"}
        </Button>

        <Button
          onClick={handleDownload}
          disabled={!storageAvailable || !blobUrl || loading}
        >
          Download
        </Button>

        <Button
          onClick={handlePrint}
          disabled={!storageAvailable || !blobUrl || loading}
        >
          Print
        </Button>

        <Button onClick={handleCopyDeepLink}>
          {copiedLink ? "Link Copied!" : "Copy Deep Link"}
        </Button>

        {drawing.equipmentSide ? (
          <Badge variant={drawing.equipmentSide === "DE" ? "info" : "purple"}>
            Side: {drawing.equipmentSide}
          </Badge>
        ) : null}

        {drawing.confidenceStatus ? (
          <Badge variant={drawing.confidenceStatus === "CONFIRMED" ? "success" : "warning"}>
            {drawing.confidenceStatus}
          </Badge>
        ) : null}
      </div>

      {/* Main Content Stage */}
      <div
        data-testid="drawing-viewer-stage"
        style={{
          border: `1px solid ${colors.border}`,
          borderRadius: 8,
          minHeight: 500,
          background: colors.backgroundDark ?? "#0f172a",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          overflow: "auto",
          position: "relative",
          cursor: panMode ? "grab" : "default",
        }}
      >
        {/* Loading State */}
        {loading && (
          <div data-testid="drawing-viewer-loading" style={{ padding: spacing.xl, textAlign: "center", color: colors.text }}>
            <p>Loading authenticated engineering drawing...</p>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div data-testid="drawing-viewer-error" style={{ padding: spacing.xl, textAlign: "center", color: colors.danger }}>
            <p style={{ marginBottom: spacing.md }}>Unable to load drawing: {error}</p>
            <Button onClick={fetchContent}>Retry</Button>
          </div>
        )}

        {/* Reference Only / No File in Storage State */}
        {!loading && !error && !storageAvailable && (
          <div
            data-testid="drawing-viewer-canvas"
            style={{
              padding: spacing.xl,
              textAlign: "center",
              color: colors.text,
              maxWidth: 500,
            }}
          >
            <div style={{ marginBottom: spacing.md }}>
              <Badge variant={drawingStatusBadgeVariant(drawing.status)}>{drawing.status || "REFERENCE_ONLY"}</Badge>
            </div>
            <div style={{ fontWeight: "bold", fontSize: 18, marginBottom: spacing.xs }}>
              {drawing.title || drawing.drawingNumber}
            </div>
            <div style={{ color: colors.textMuted, fontSize: 13, marginBottom: spacing.md }}>
              Drawing Number: {drawing.drawingNumber} {drawing.currentRevision ? `· Rev ${drawing.currentRevision}` : ""}
            </div>
            <div
              style={{
                background: "rgba(148, 163, 184, 0.1)",
                border: `1px dashed ${colors.border}`,
                borderRadius: 8,
                padding: spacing.md,
                marginTop: spacing.md,
                fontSize: 13,
                color: colors.textMuted,
                lineHeight: 1.6,
              }}
            >
              <div style={{ fontWeight: 600, color: colors.text, marginBottom: spacing.xs }}>
                Drawing file not available
              </div>
              <div>
                {drawing.confidenceStatus === "CONFIRMED"
                  ? "Authoritative drawing reference is confirmed for this equipment, but the physical drawing file is not currently archived in storage."
                  : "Engineering drawing reference is recorded for information purposes. No physical binary file is available in the archive."}
              </div>
            </div>
          </div>
        )}

        {/* Real PDF Viewer */}
        {!loading && !error && storageAvailable && isPdf && blobUrl && (
          <div
            data-testid="drawing-viewer-canvas"
            style={{
              width: "100%",
              height: "650px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <iframe
              data-testid="drawing-pdf-viewer"
              src={blobUrl}
              title={drawing.title || drawing.drawingNumber}
              style={{
                width: "100%",
                height: "100%",
                border: "none",
                borderRadius: 4,
              }}
            />
          </div>
        )}

        {/* Real Image Viewer */}
        {!loading && !error && storageAvailable && isImage && blobUrl && (
          <div
            data-testid="drawing-viewer-canvas"
            style={{
              padding: spacing.md,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <img
              data-testid="drawing-image-viewer"
              src={blobUrl}
              alt={drawing.title || drawing.drawingNumber}
              style={{
                maxWidth: "100%",
                maxHeight: "650px",
                transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
                transition: "transform 0.15s ease",
              }}
            />
          </div>
        )}

        {/* CAD Format Card */}
        {!loading && !error && storageAvailable && isCad && blobUrl && (
          <div
            data-testid="drawing-viewer-canvas"
            style={{
              padding: spacing.xl,
              textAlign: "center",
              color: colors.text,
              maxWidth: 450,
            }}
          >
            <Badge variant="info">CAD Model</Badge>
            <div style={{ fontWeight: "bold", fontSize: 18, marginTop: spacing.sm, marginBottom: spacing.xs }}>
              {drawing.fileName || `${drawing.drawingNumber}.dwg`}
            </div>
            <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.md }}>
              Engineering drawing in binary CAD format.
            </div>
            <p style={{ color: colors.textMuted, fontSize: 13, marginBottom: spacing.lg }}>
              This format cannot be rendered inline in standard web browsers. Download the file to view it in CAD software.
            </p>
            <Button onClick={handleDownload}>
              Download CAD File
            </Button>
          </div>
        )}

        {/* Fallback Display if format unrecognized but file exists */}
        {!loading && !error && storageAvailable && !isPdf && !isImage && !isCad && blobUrl && (
          <div
            data-testid="drawing-viewer-canvas"
            style={{
              padding: spacing.xl,
              textAlign: "center",
              color: colors.text,
            }}
          >
            <div style={{ fontWeight: "bold", fontSize: 16 }}>{drawing.title}</div>
            <div style={{ color: colors.textMuted, fontSize: 12, marginTop: spacing.xs, marginBottom: spacing.md }}>
              {drawing.fileName || drawing.drawingNumber}
            </div>
            <Button onClick={handleDownload}>Download File</Button>
          </div>
        )}
      </div>
    </Card>
  );
}
