import { useState } from "react";
import { Card, Button } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import useCopilot from "./useCopilot";

// MWO-AI5R-LTSA-COPILOT-001 -- LTSA Dashboard Copilot: minimum vertical
// slice UI. `assetContext` is optional -- omitted here (mounted on the
// GLOBAL Executive Dashboard, no single pump selected), so the backend
// answers over the caller's authorized LTSA scope as a whole. A future
// asset-scoped workspace can reuse this same component/hook by passing
// its selected pump tag (WorkspaceContext/EngineeringObjectResolver's own
// { tag } shape), unchanged.
const KIND_COLOR = {
  FACT: colors.success,
  RECOMMENDATION: colors.warning,
  INTERPRETATION: colors.info,
  DATA_GAP: colors.textMuted,
};

export default function CopilotPanel({ assetContext }) {
  const [question, setQuestion] = useState("");
  const { status, result, errorMessage, ask } = useCopilot(assetContext);

  function handleSubmit(event) {
    event.preventDefault();
    ask(question);
  }

  return (
    <Card title="Engineering Copilot">
      <form onSubmit={handleSubmit} style={{ display: "flex", gap: spacing.sm, flexWrap: "wrap" }}>
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={assetContext ? `Ask about ${assetContext}...` : "Ask about pump status, work orders, PM/CM, seals, inventory..."}
          aria-label="Ask the Engineering Copilot"
          style={{
            flex: "1 1 320px",
            padding: `${spacing.xs}px ${spacing.sm}px`,
            borderRadius: spacing.xs,
            border: `1px solid ${colors.border}`,
            background: colors.background,
            color: colors.text,
          }}
        />
        <Button type="submit" disabled={status === "loading" || !question.trim()}>
          {status === "loading" ? "Asking..." : "Ask"}
        </Button>
      </form>

      {assetContext ? (
        <p style={{ color: colors.textMuted, marginTop: spacing.xs }}>Asset context: {assetContext}</p>
      ) : null}

      {status === "loading" ? <p style={{ color: colors.textMuted }}>Thinking...</p> : null}

      {status === "unauthorized" ? (
        <p role="alert" style={{ color: colors.danger }}>
          You are not authorized to use the Engineering Copilot.
        </p>
      ) : null}

      {status === "error" ? (
        <p role="alert" style={{ color: colors.danger }}>
          {errorMessage}
        </p>
      ) : null}

      {(status === "answer" || status === "data_gap") && result ? (
        <div style={{ marginTop: spacing.sm }}>
          <span
            style={{
              display: "inline-block",
              padding: `2px ${spacing.xs}px`,
              borderRadius: spacing.xs,
              color: colors.text,
              background: KIND_COLOR[result.kind] ?? colors.textMuted,
              fontSize: "0.75rem",
              marginBottom: spacing.xs,
            }}
          >
            {result.kind}
          </span>
          <p style={{ whiteSpace: "pre-line", color: colors.text }}>{result.answer}</p>
          {Array.isArray(result.evidence) && result.evidence.length > 0 ? (
            <p style={{ color: colors.textMuted, fontSize: "0.85rem" }}>
              {result.evidence.length} evidence item(s) cited.
            </p>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
