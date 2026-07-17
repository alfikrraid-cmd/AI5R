import colors from "../theme/colors";
import spacing from "../theme/spacing";

export default function Button({ children, onClick, type = "button", disabled = false, className = "" }) {
  const classes = ["ds-button", className].filter(Boolean).join(" ");

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={classes}
      style={{
        background: disabled ? colors.textMuted : colors.info,
        color: colors.text,
        border: "none",
        borderRadius: spacing.xs,
        padding: `${spacing.xs}px ${spacing.md}px`,
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      {children}
    </button>
  );
}
