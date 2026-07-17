import Button from "./Button";
import colors from "../theme/colors";
import shadows from "../theme/shadows";
import spacing from "../theme/spacing";

export default function Modal({ isOpen, onClose, title, children }) {
  if (!isOpen) {
    return null;
  }

  return (
    <div
      data-testid="modal-backdrop"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        data-testid="modal"
        onClick={(event) => event.stopPropagation()}
        style={{
          background: colors.panel,
          color: colors.text,
          borderRadius: spacing.sm,
          boxShadow: shadows.lg,
          padding: spacing.lg,
          minWidth: 320,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>{title}</h2>
          <Button onClick={onClose}>Close</Button>
        </div>

        <div style={{ marginTop: spacing.md }}>{children}</div>
      </div>
    </div>
  );
}
