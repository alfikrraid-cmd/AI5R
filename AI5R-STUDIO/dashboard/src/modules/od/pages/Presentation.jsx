import { Badge, Card, EmptyState, PageHeader } from "../../../design-system";
import "./Presentation.css";

/**
 * The Presentation layout (per layouts.md) — the Business Blueprint reveal,
 * per OD-001: the payoff screen, shown as a real artifact rather than a
 * form-submission confirmation. Read-only; sealed blueprints do not change
 * here.
 */
export default function Presentation({ blueprint }) {
  if (!blueprint) {
    return (
      <div className="od-presentation">
        <PageHeader title="Presentation" />
        <EmptyState
          title="No Business Blueprint yet"
          description="Complete Open Design to seal your first Business Blueprint."
        />
      </div>
    );
  }

  return (
    <div className="od-presentation">
      <PageHeader title="Business Blueprint" subtitle="Sealed and ready." />

      <Card>
        <div className="od-presentation-header">
          <h2 style={{ margin: 0 }}>{blueprint.businessIdentity}</h2>
          <Badge variant="success">Sealed</Badge>
        </div>

        <p>
          <strong>Objective</strong>
          <br />
          {blueprint.objective}
        </p>

        <p>
          <strong>Context</strong>
          <br />
          {blueprint.context}
        </p>

        <p className="od-presentation-meta">
          {blueprint.blueprintId} &middot; sealed {blueprint.capturedAt}
        </p>
      </Card>
    </div>
  );
}
