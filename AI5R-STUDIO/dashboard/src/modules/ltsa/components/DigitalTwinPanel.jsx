import { Card, EmptyState } from "../../../design-system";

/**
 * RC-002 (Executive Dashboard React Implementation). Placeholder only --
 * no 3D/visualization library, no live telemetry, per mission scope.
 */
export default function DigitalTwinPanel() {
  return (
    <Card title="Digital Twin">
      <EmptyState
        title="Digital Twin is not yet available"
        description="Reserved for a future, separately-scoped visualization capability."
      />
    </Card>
  );
}
