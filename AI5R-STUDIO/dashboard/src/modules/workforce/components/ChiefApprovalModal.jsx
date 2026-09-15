import { useEffect, useState } from "react";
import Badge from "../../../design-system/components/Badge";
import Modal from "../../../design-system/components/Modal";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";
import { releaseWorkforceTask } from "../../../api/workforceClient";

export default function ChiefApprovalModal({
  isOpen,
  onClose,
  workItem,
  onReleased,
}) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setSubmitting(false);
      setError(null);
    }
  }, [isOpen, workItem]);

  if (!isOpen || !workItem) return null;

  async function handleApproveAndRelease() {
    if (submitting) return;

    setError(null);
    setSubmitting(true);

    try {
      // Explicit Human Chief Approval identity payload
      const result = await releaseWorkforceTask(workItem.work_item_id, {
        approverId: "CHIEF-USER-01",
        approverRole: "CHIEF",
        isHuman: true,
        metadata: {
          authorized_via: "AI5R_STUDIO_WORKFORCE_UI",
          timestamp: new Date().toISOString(),
        },
      });

      onReleased?.(result);
      onClose();
    } catch (err) {
      setError(err.message || "Failed to authorize and release work item");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Production Release Authorization"
    >
      <div
        data-testid="chief-approval-modal"
        style={{ display: "flex", flexDirection: "column", gap: spacing.md }}
      >
        {/* Warning Banner */}
        <div
          data-testid="chief-approval-warning"
          style={{
            background: "rgba(245, 158, 11, 0.15)",
            border: `1px solid ${colors.warning}`,
            borderRadius: spacing.xs,
            padding: spacing.md,
            display: "flex",
            flexDirection: "column",
            gap: spacing.xs,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: spacing.xs }}>
            <span style={{ fontSize: typography.size.md }}>⚠️</span>
            <span style={{ fontWeight: typography.weight.bold, color: colors.warning, fontSize: typography.size.sm }}>
              HUMAN CHIEF AUTHORIZATION REQUIRED
            </span>
          </div>
          <div style={{ fontSize: typography.size.xs, color: colors.text }}>
            This work item targets production systems and cannot be released automatically.
            AI employees and automated agents are strictly forbidden from approving production changes.
          </div>
        </div>

        {/* Work Item Metadata */}
        <div
          style={{
            background: colors.background,
            padding: spacing.sm,
            borderRadius: spacing.xs,
            display: "flex",
            flexDirection: "column",
            gap: spacing.xs,
            fontSize: typography.size.xs,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: colors.textMuted }}>Work Item ID:</span>
            <code>{workItem.work_item_id}</code>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: colors.textMuted }}>Title:</span>
            <span style={{ fontWeight: typography.weight.bold, color: colors.text }}>{workItem.title}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: colors.textMuted }}>Assigned Position:</span>
            <Badge variant="info">{workItem.assigned_position_id}</Badge>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: colors.textMuted }}>Current Status:</span>
            <Badge variant="warning">{workItem.status} (COMPLETED)</Badge>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: colors.textMuted }}>Production Target:</span>
            <Badge variant="danger">PRODUCTION</Badge>
          </div>
        </div>

        {/* Error Banner */}
        {error ? (
          <div
            data-testid="approval-error-banner"
            style={{
              background: "rgba(239, 68, 68, 0.15)",
              border: `1px solid ${colors.danger}`,
              borderRadius: spacing.xs,
              padding: spacing.sm,
              color: colors.danger,
              fontSize: typography.size.sm,
            }}
          >
            {error}
          </div>
        ) : null}

        {/* Action Buttons */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: spacing.sm, marginTop: spacing.xs }}>
          <button
            type="button"
            data-testid="cancel-approval-button"
            onClick={onClose}
            disabled={submitting}
            style={{
              background: "transparent",
              color: colors.textMuted,
              border: `1px solid ${colors.border}`,
              borderRadius: spacing.xs,
              padding: `${spacing.xs}px ${spacing.md}px`,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            data-testid="confirm-release-button"
            onClick={handleApproveAndRelease}
            disabled={submitting}
            style={{
              background: submitting ? colors.textMuted : colors.danger,
              color: colors.text,
              border: "none",
              borderRadius: spacing.xs,
              padding: `${spacing.xs}px ${spacing.md}px`,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? "Authorizing Release..." : "Approve & Release to Production"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
