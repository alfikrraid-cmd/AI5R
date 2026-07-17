import colors from "../theme/colors";
import spacing from "../theme/spacing";
import typography from "../theme/typography";

const VARIANT_COLOR = {
  success: colors.success,
  info: colors.info,
  warning: colors.warning,
  danger: colors.danger,
  purple: colors.purple,
};

export default function Badge({ children, variant = "purple" }) {
  const backgroundColor = VARIANT_COLOR[variant] ?? colors.purple;

  return (
    <span
      data-testid="badge"
      style={{
        backgroundColor,
        color: colors.text,
        fontFamily: typography.fontFamily,
        fontSize: typography.size.sm,
        fontWeight: typography.weight.bold,
        padding: `${spacing.xs / 2}px ${spacing.sm}px`,
        borderRadius: spacing.md,
        display: "inline-block",
      }}
    >
      {children}
    </span>
  );
}
