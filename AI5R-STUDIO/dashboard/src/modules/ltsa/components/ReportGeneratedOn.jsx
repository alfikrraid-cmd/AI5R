import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

export default function ReportGeneratedOn({ date = new Date() }) {
  const formatted = date.toISOString().slice(0, 10);

  return (
    <div style={{ color: colors.textMuted, fontSize: 12, marginBottom: spacing.md }}>
      Generated: {formatted}
    </div>
  );
}
