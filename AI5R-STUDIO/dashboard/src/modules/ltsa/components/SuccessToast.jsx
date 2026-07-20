import { useEffect } from "react";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const AUTO_DISMISS_MS = 4000;

export default function SuccessToast({ message, onDismiss }) {
  useEffect(() => {
    if (!message) {
      return undefined;
    }

    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [message, onDismiss]);

  if (!message) {
    return null;
  }

  return (
    <div
      role="status"
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: spacing.md,
        background: colors.success,
        color: colors.text,
        borderRadius: spacing.xs,
        padding: `${spacing.sm}px ${spacing.md}px`,
        marginBottom: spacing.md,
      }}
    >
      <span>{message}</span>

      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss"
        style={{
          background: "transparent",
          border: "none",
          color: colors.text,
          cursor: "pointer",
          fontWeight: "bold",
        }}
      >
        ×
      </button>
    </div>
  );
}
