import { useState } from "react";
import { Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const COMPONENTS = [
  "Rotary Face",
  "Stationary Face",
  "Secondary Seal",
  "Spring",
  "Sleeve",
  "Drive Collar",
  "Gland Plate",
  "Throttle Bushing",
];

/**
 * Seal Component Navigator (RC-003B §2). Fixed set of 8 components,
 * always shown in this order (not data-driven per drawing, per the
 * approved Open Design's own SealComponentsNavigator spec). Selecting a
 * chip is a placeholder interaction only -- it records which component
 * area was requested (shown as feedback text) but does NOT highlight
 * anything inside the Drawing Viewer canvas ("Drawing Highlight" and
 * "Automatic Detection" are both explicitly forbidden for this RC).
 */
export default function SealComponentNavigator({ drawing }) {
  const [selectedComponent, setSelectedComponent] = useState(null);

  if (!drawing) {
    return (
      <Card title="Seal Component Navigator">
        <EmptyState
          title="No seal components to show"
          description="Seal components appear here once a drawing is opened."
        />
      </Card>
    );
  }

  return (
    <Card title="Seal Component Navigator">
      <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs, marginBottom: spacing.sm }}>
        {COMPONENTS.map((component) => (
          <button
            key={component}
            type="button"
            onClick={() => setSelectedComponent(component)}
            style={{
              padding: `${spacing.xs}px ${spacing.sm}px`,
              borderRadius: 16,
              border: `1px solid ${component === selectedComponent ? colors.info : colors.border}`,
              background: component === selectedComponent ? colors.background : "transparent",
              color: colors.text,
              cursor: "pointer",
            }}
          >
            {component}
          </button>
        ))}
      </div>

      {selectedComponent ? (
        <p style={{ color: colors.textMuted, fontSize: 13 }}>
          Navigating to <strong>{selectedComponent}</strong> — highlighting the corresponding drawing
          area is a future capability, not implemented in this release.
        </p>
      ) : (
        <p style={{ color: colors.textMuted, fontSize: 13 }}>
          Select a component to navigate to its area of the drawing.
        </p>
      )}
    </Card>
  );
}
