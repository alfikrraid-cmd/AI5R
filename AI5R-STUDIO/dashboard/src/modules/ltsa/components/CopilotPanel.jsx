import { useState } from "react";
import { Badge, Card, Button } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import useCopilot from "./useCopilot";

// MWO-LTSA-GATE-C -- Executive Dashboard AI Engineering Copilot surface.
// `assetContext` is optional -- omitted when mounted on the GLOBAL
// Executive Dashboard (no single pump selected), so the backend answers
// over the caller's authorized LTSA scope as a whole. A future
// asset-scoped workspace reuses this same component/hook unchanged by
// passing its selected pump tag (WorkspaceContext/EngineeringObjectResolver's
// own { tag } shape) -- 940-P-2A/2B/2C stay distinct assets throughout;
// this component never infers or substitutes one tag for another.
const KIND_VARIANT = {
  FACT: "success",
  INTERPRETATION: "info",
  RECOMMENDATION: "warning",
  DATA_GAP: "purple",
};

// Suggested prompts are real questions submitted through the same
// askCopilot() path as manual input -- never pre-baked with a canned
// answer. Whatever the backend legitimately returns (including DATA_GAP
// when asked without an asset context, per identity-safety: a tag is
// never guessed out of question text) is what renders.
const SUGGESTED_PROMPTS = [
  "Analisa 940-P-2A",
  "Apa current seal 940-P-2A?",
  "Tampilkan maintenance history 940-P-2A",
  "Ada rekomendasi untuk 940-P-2A?",
];

// Presentation-only label mapping over the backend's own real tool
// identifiers (copilot_orchestrator.TOOL_CATALOG) -- never invents a
// source, falls back to the raw name for anything unmapped.
const TOOL_LABELS = {
  pump_status: "Pump Status",
  pump_history: "Maintenance History",
  work_orders: "Work Orders",
  pm: "Preventive Maintenance",
  cm: "Corrective Maintenance",
  current_seal: "Current Seal",
  seal_compat: "Seal Compatibility",
  inventory: "Inventory",
  drawing_document: "Drawings/Documents",
  installation: "Installation History",
  recommendation: "Recommendation",
};

export default function CopilotPanel({ assetContext }) {
  const [question, setQuestion] = useState("");
  const { status, result, errorMessage, ask } = useCopilot(assetContext);
  const busy = status === "loading";

  function handleSubmit(event) {
    event.preventDefault();
    ask(question);
  }

  function handleSuggestedPrompt(prompt) {
    if (busy) return;
    setQuestion(prompt);
    ask(prompt);
  }

  return (
    <Card title="AI Engineering Copilot">
      <p style={{ color: colors.textMuted, marginTop: 0, marginBottom: spacing.sm }}>
        Ask about pumps, seals, maintenance, reliability, drawings, inventory, and installation history.
      </p>

      <form onSubmit={handleSubmit} style={{ display: "flex", gap: spacing.sm, flexWrap: "wrap" }}>
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={assetContext ? `Ask about ${assetContext}...` : "Ask about pump status, work orders, PM/CM, seals, inventory..."}
          aria-label="Ask the Engineering Copilot"
          style={{
            flex: "1 1 220px",
            padding: `${spacing.xs}px ${spacing.sm}px`,
            borderRadius: spacing.xs,
            border: `1px solid ${colors.border}`,
            background: colors.background,
            color: colors.text,
          }}
        />
        <Button type="submit" disabled={busy || !question.trim()}>
          {busy ? "Asking..." : "Ask"}
        </Button>
      </form>

      {assetContext ? (
        <p style={{ color: colors.textMuted, marginTop: spacing.xs }}>Asset context: {assetContext}</p>
      ) : null}

      <div style={{ marginTop: spacing.md }}>
        <p style={{ color: colors.textMuted, fontSize: "0.85rem", marginBottom: spacing.xs }}>Suggested questions</p>
        <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs }}>
          {SUGGESTED_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={busy}
              onClick={() => handleSuggestedPrompt(prompt)}
              style={{
                textAlign: "left",
                padding: `${spacing.xs}px ${spacing.sm}px`,
                borderRadius: spacing.xs,
                border: `1px solid ${colors.border}`,
                background: "transparent",
                color: colors.text,
                cursor: busy ? "not-allowed" : "pointer",
              }}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {busy ? <p style={{ color: colors.textMuted, marginTop: spacing.sm }}>Thinking...</p> : null}

      {status === "unauthorized" ? (
        <p role="alert" style={{ color: colors.danger, marginTop: spacing.sm }}>
          You are not authorized to use the Engineering Copilot.
        </p>
      ) : null}

      {status === "error" ? (
        <p role="alert" style={{ color: colors.danger, marginTop: spacing.sm }}>
          {errorMessage}
        </p>
      ) : null}

      {(status === "answer" || status === "data_gap") && result ? (
        <div style={{ marginTop: spacing.sm }}>
          <Badge variant={KIND_VARIANT[result.kind] ?? "purple"}>{result.kind}</Badge>
          <p style={{ whiteSpace: "pre-line", color: colors.text, marginTop: spacing.xs }}>{result.answer}</p>

          {Array.isArray(result.evidence) && result.evidence.length > 0 ? (
            <ul style={{ color: colors.textMuted, fontSize: "0.8rem", margin: `${spacing.xs}px 0 0`, paddingLeft: spacing.md }}>
              {result.evidence.map((item, index) => (
                <li key={index}>
                  {item.source} · {item.reference} · {item.field}: {item.value}
                </li>
              ))}
            </ul>
          ) : null}

          {Array.isArray(result.tools_used) && result.tools_used.length > 0 ? (
            <p style={{ color: colors.textMuted, fontSize: "0.8rem", marginTop: spacing.xs }}>
              Sources: {result.tools_used.map((tool) => TOOL_LABELS[tool] ?? tool).join(" · ")}
            </p>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}
