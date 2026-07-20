import { Badge, Button, Card, EmptyState } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { criticalityBadgeVariant, healthScoreColor, statusBadgeVariant } from "../utils/pumpHealth";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

export default function PumpDetailPanel({ pump, onCreatePM, onCreateCM, onViewHistory }) {
  if (!pump) {
    return (
      <EmptyState
        title="No pump selected"
        description="Select a pump from the registry table to view its details."
      />
    );
  }

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>{pump.name}</h2>

      <Card title="Equipment Summary">
        <Field label="Pump Code" value={pump.code} />
        <Field label="Tag" value={pump.tag} />
        <Field label="Manufacturer" value={pump.manufacturer} />
        <Field label="Pump Type" value={pump.type} />
        <Field label="Seal" value={pump.seal} />
        <Field label="Location" value={pump.location} />
        <Field label="Area" value={pump.area} />

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Criticality</div>
          <Badge variant={criticalityBadgeVariant(pump.criticality)}>{pump.criticality}</Badge>
        </div>

        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Status</div>
          <Badge variant={statusBadgeVariant(pump.status)}>{pump.status}</Badge>
        </div>
      </Card>

      <Card title="Maintenance Summary">
        <div style={{ marginBottom: spacing.sm }}>
          <div style={{ color: colors.textMuted, fontSize: 12 }}>Health Score</div>
          <strong style={{ color: healthScoreColor(pump.healthScore) }}>{pump.healthScore}</strong>
        </div>

        <Field label="Availability" value={`${pump.availability}%`} />
        <Field label="Runtime Hours" value={`${pump.runtimeHours.toLocaleString("en-US")} hrs`} />
        <Field label="Last PM" value={pump.lastPM} />
        <Field label="Next PM" value={pump.nextPM} />
        <Field label="Open Work Orders" value={pump.openWO} />
      </Card>

      <Card title="AI Recommendation">
        <Field label="Recommendation" value={pump.recommendation} />

        <div>
          <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>
            Knowledge Links
          </div>

          {pump.knowledgeLinks.length === 0 ? (
            <div style={{ color: colors.textMuted }}>No knowledge links.</div>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}>
              {pump.knowledgeLinks.map((link) => (
                <Badge key={link} variant="info">
                  {link}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </Card>

      <Card title="Quick Actions">
        <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.sm }}>
          <Button onClick={onViewHistory}>View History</Button>
          <Button onClick={onCreatePM}>Create PM</Button>
          <Button onClick={onCreateCM}>Create CM</Button>
          <Button disabled>Documents</Button>
        </div>
      </Card>
    </div>
  );
}
