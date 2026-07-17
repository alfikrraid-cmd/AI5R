import { Badge, Card, EmptyState, StatusBadge } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text }}>{value}</div>
    </div>
  );
}

function BadgeList({ label, items, emptyLabel }) {
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.xs }}>
        {label}
      </div>

      {items.length === 0 ? (
        <div style={{ color: colors.textMuted }}>{emptyLabel}</div>
      ) : (
        <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}>
          {items.map((item) => (
            <Badge key={item} variant="info">
              {item}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SealDetailPanel({ seal }) {
  if (!seal) {
    return (
      <EmptyState
        title="No seal selected"
        description="Select a seal from the registry table to view its details."
      />
    );
  }

  return (
    <Card title={seal.name}>
      <Field label="Seal Code" value={seal.code} />
      <Field label="Type" value={seal.type} />
      <Field label="Manufacturer" value={seal.manufacturer} />

      <BadgeList
        label="Compatible Pumps"
        items={seal.compatiblePumps}
        emptyLabel="No compatible pumps recorded."
      />

      <BadgeList
        label="Compatible Seals"
        items={seal.compatibleSeals}
        emptyLabel="No compatible seals recorded."
      />

      <div style={{ marginBottom: spacing.sm }}>
        <div style={{ color: colors.textMuted, fontSize: 12 }}>Status</div>
        <StatusBadge label="Status" status={seal.status} />
      </div>

      <Field label="Recommendation" value={seal.recommendation} />

      <BadgeList
        label="Knowledge Links"
        items={seal.knowledgeLinks}
        emptyLabel="No knowledge links."
      />
    </Card>
  );
}
