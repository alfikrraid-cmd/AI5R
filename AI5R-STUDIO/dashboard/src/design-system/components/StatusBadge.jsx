import colors from "../theme/colors";
import spacing from "../theme/spacing";

const KNOWN_STATUS_MODIFIERS = new Set(["active", "warning", "error", "idle"]);

const MODIFIER_COLOR = {
  active: colors.success,
  warning: colors.warning,
  error: colors.danger,
  idle: colors.textMuted,
  neutral: colors.textMuted,
};

function statusModifier(status) {
  const normalized = String(status ?? "").toLowerCase();

  return KNOWN_STATUS_MODIFIERS.has(normalized) ? normalized : "neutral";
}

export default function StatusBadge({ label, status }) {
  const modifier = statusModifier(status);

  return (
    <div
      className={`ds-status-badge ds-status-badge--${modifier}`}
      data-testid="status-badge"
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: spacing.sm,
        padding: `${spacing.xs}px ${spacing.sm}px`,
        borderRadius: spacing.xs,
        color: colors.text,
        borderLeft: `3px solid ${MODIFIER_COLOR[modifier]}`,
      }}
    >
      <span>{label}</span>
      <strong style={{ color: MODIFIER_COLOR[modifier] }}>{status}</strong>
    </div>
  );
}
