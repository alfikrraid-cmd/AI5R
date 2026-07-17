import { Badge, Card, EmptyState, StatusBadge } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const STATUS_MODIFIER = {
  ACTIVE: "active",
  STANDBY: "idle",
  MAINTENANCE: "warning",
  ALERT: "warning",
  FAULT: "error",
};

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

export default function PumpDetailPanel({ pump }) {
  if (!pump) {
    return (
      <EmptyState
        title="No pump selected"
        description="Select a pump from the registry table to view its details."
      />
    );
  }

  return (
    <Card title={pump.name}>
      <Field label="Pump Code" value={pump.code} />
      <Field label="Manufacturer" value={pump.manufacturer} />
      <Field label="Pump Type" value={pump.type} />
      <Field label="Seal" value={pump.seal} />
      <Field label="Location" value={pump.location} />

      <div style={{ marginBottom: spacing.sm }}>
        <div style={{ color: colors.textMuted, fontSize: 12 }}>Status</div>
        <StatusBadge label="Status" status={STATUS_MODIFIER[pump.status] ? pump.status : pump.status} />
      </div>

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
  );
}
