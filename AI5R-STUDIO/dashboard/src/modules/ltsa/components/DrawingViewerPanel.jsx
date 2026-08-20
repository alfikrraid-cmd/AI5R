import { useState } from "react";
import { Button, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const ZOOM_MIN = 25;
const ZOOM_MAX = 400;
const ZOOM_STEP = 10;

/**
 * Drawing Viewer, Foundation scope. No real PDF/image rendering library is
 * introduced (none exists anywhere in this repo, and adding one is a
 * separately-scoped decision beyond "bring the Drawing Workspace to
 * life" for this RC) -- the canvas is a disclosed static placeholder
 * showing the selected drawing's identity, matching the same
 * disclosed-placeholder discipline as PumpWorkspaceComingSoon elsewhere
 * in LTSA. Zoom, Rotate, and Pan are real, working toolbar state; Download,
 * Print, and Deep-link are explicitly named "placeholder" by RC-003A and
 * render disabled, per that instruction.
 */
export default function DrawingViewerPanel({ drawing }) {
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [panMode, setPanMode] = useState(false);

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

  return (
    <Card title="Drawing Viewer">
      <div
        role="toolbar"
        aria-label="Drawing viewer toolbar"
        style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs, marginBottom: spacing.sm }}
      >
        <Button
          onClick={() => setZoom((current) => Math.max(ZOOM_MIN, current - ZOOM_STEP))}
          disabled={zoom <= ZOOM_MIN}
        >
          Zoom Out
        </Button>
        <span aria-live="polite" style={{ alignSelf: "center", color: colors.textMuted, fontSize: 12 }}>
          {zoom}%
        </span>
        <Button
          onClick={() => setZoom((current) => Math.min(ZOOM_MAX, current + ZOOM_STEP))}
          disabled={zoom >= ZOOM_MAX}
        >
          Zoom In
        </Button>

        <Button onClick={() => setRotation((current) => (current + 90) % 360)}>Rotate</Button>

        <Button onClick={() => setPanMode((current) => !current)}>
          {panMode ? "Pan: On" : "Pan: Off"}
        </Button>

        <Button disabled>Download (Coming soon)</Button>
        <Button disabled>Print (Coming soon)</Button>
        <Button disabled>Copy Deep Link (Coming soon)</Button>
      </div>

      <div
        data-testid="drawing-viewer-stage"
        style={{
          border: `1px dashed ${colors.border}`,
          borderRadius: 8,
          padding: spacing.lg,
          textAlign: "center",
          cursor: panMode ? "grab" : "default",
        }}
      >
        <div
          data-testid="drawing-viewer-canvas"
          style={{
            display: "inline-block",
            transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
            color: colors.text,
          }}
        >
          <div style={{ fontWeight: "bold" }}>{drawing.title}</div>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>
            {drawing.drawingNumber} · Rev {drawing.currentRevision}
          </div>
          <p style={{ color: colors.textMuted, marginTop: spacing.sm }}>
            Static viewer placeholder — no drawing file/rendering backend exists yet.
          </p>
        </div>
      </div>
    </Card>
  );
}
