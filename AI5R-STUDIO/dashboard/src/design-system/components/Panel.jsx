import colors from "../theme/colors";
import spacing from "../theme/spacing";

export default function Panel({ children, className = "" }) {
  const classes = ["card", className].filter(Boolean).join(" ");

  return (
    <div
      className={classes}
      data-testid="panel"
      style={{ background: colors.panel, color: colors.text, borderRadius: spacing.sm }}
    >
      {children}
    </div>
  );
}
