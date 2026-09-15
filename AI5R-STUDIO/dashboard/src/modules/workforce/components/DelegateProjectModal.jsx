import React, { useState } from "react";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import typography from "../../../design-system/theme/typography";

export default function DelegateProjectModal({ isOpen, onClose, onDelegate, isSubmitting }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isProduction, setIsProduction] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Mission title is required");
      return;
    }
    setError(null);
    try {
      await onDelegate({
        title: title.trim(),
        description: description.trim(),
        isProduction,
      });
      setTitle("");
      setDescription("");
      setIsProduction(false);
    } catch (err) {
      setError(err.message || "Failed to delegate mission");
    }
  };

  return (
    <div
      data-testid="delegate-project-modal"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: spacing.md,
      }}
    >
      <div
        style={{
          background: colors.surface,
          border: `1px solid ${colors.border}`,
          borderRadius: spacing.sm,
          width: "100%",
          maxWidth: "560px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: `${spacing.md}px ${spacing.lg}px`,
            borderBottom: `1px solid ${colors.border}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h3
              style={{
                margin: 0,
                color: colors.text,
                fontSize: typography.size.lg,
                fontWeight: typography.weight.bold,
              }}
            >
              ⚡ Delegate Mission to NEXA
            </h3>
            <p
              style={{
                margin: `${spacing.xs}px 0 0`,
                color: colors.textMuted,
                fontSize: typography.size.xs,
              }}
            >
              NEXA will decompose this into specialist tasks across the engineering team.
            </p>
          </div>
          <button
            type="button"
            data-testid="close-delegate-modal"
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: colors.textMuted,
              fontSize: typography.size.lg,
              cursor: "pointer",
            }}
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: `${spacing.md}px ${spacing.lg}px` }}>
          {error ? (
            <div
              data-testid="delegate-error"
              style={{
                padding: spacing.sm,
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid #ef4444",
                borderRadius: spacing.xs,
                color: "#ef4444",
                fontSize: typography.size.xs,
                marginBottom: spacing.md,
              }}
            >
              {error}
            </div>
          ) : null}

          <div style={{ marginBottom: spacing.md }}>
            <label
              htmlFor="mission-title"
              style={{
                display: "block",
                marginBottom: spacing.xs,
                color: colors.text,
                fontSize: typography.size.xs,
                fontWeight: typography.weight.bold,
              }}
            >
              Mission Title *
            </label>
            <input
              id="mission-title"
              type="text"
              data-testid="mission-title-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Build Customer Authentication Portal"
              style={{
                width: "100%",
                padding: `${spacing.sm}px`,
                background: colors.background,
                border: `1px solid ${colors.border}`,
                borderRadius: spacing.xs,
                color: colors.text,
                fontSize: typography.size.sm,
                boxSizing: "border-box",
              }}
              required
            />
          </div>

          <div style={{ marginBottom: spacing.md }}>
            <label
              htmlFor="mission-desc"
              style={{
                display: "block",
                marginBottom: spacing.xs,
                color: colors.text,
                fontSize: typography.size.xs,
                fontWeight: typography.weight.bold,
              }}
            >
              Engineering Scope & Requirements
            </label>
            <textarea
              id="mission-desc"
              data-testid="mission-description-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detail the architecture goals, API endpoints, testing criteria, and deployment objectives..."
              rows={4}
              style={{
                width: "100%",
                padding: `${spacing.sm}px`,
                background: colors.background,
                border: `1px solid ${colors.border}`,
                borderRadius: spacing.xs,
                color: colors.text,
                fontSize: typography.size.sm,
                resize: "vertical",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div
            style={{
              marginBottom: spacing.md,
              padding: spacing.sm,
              background: isProduction ? "rgba(245, 158, 11, 0.1)" : "rgba(255, 255, 255, 0.03)",
              border: `1px solid ${isProduction ? "#f59e0b" : colors.border}`,
              borderRadius: spacing.xs,
            }}
          >
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: spacing.xs,
                color: colors.text,
                fontSize: typography.size.sm,
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                data-testid="mission-production-checkbox"
                checked={isProduction}
                onChange={(e) => setIsProduction(e.target.checked)}
              />
              <span style={{ fontWeight: typography.weight.bold }}>
                Production Release Mission
              </span>
            </label>
            {isProduction ? (
              <div
                data-testid="production-warning"
                style={{
                  marginTop: spacing.xs,
                  color: "#f59e0b",
                  fontSize: typography.size.xs,
                  lineHeight: 1.4,
                }}
              >
                ⚠️ Production release step will be protected by the Human Chief Approval Gate.
                AI employees cannot approve production releases.
              </div>
            ) : null}
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: spacing.sm,
              marginTop: spacing.lg,
            }}
          >
            <button
              type="button"
              data-testid="cancel-delegate-button"
              onClick={onClose}
              disabled={isSubmitting}
              style={{
                background: "transparent",
                color: colors.textMuted,
                border: `1px solid ${colors.border}`,
                borderRadius: spacing.xs,
                padding: `${spacing.sm}px ${spacing.md}px`,
                fontSize: typography.size.sm,
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              data-testid="submit-mission-button"
              disabled={isSubmitting || !title.trim()}
              style={{
                background: "#4f46e5",
                color: "#ffffff",
                border: "none",
                borderRadius: spacing.xs,
                padding: `${spacing.sm}px ${spacing.lg}px`,
                fontSize: typography.size.sm,
                fontWeight: typography.weight.bold,
                cursor: isSubmitting || !title.trim() ? "not-allowed" : "pointer",
                opacity: isSubmitting || !title.trim() ? 0.6 : 1,
              }}
            >
              {isSubmitting ? "Orchestrating..." : "⚡ Decompose & Delegate"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
