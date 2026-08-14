import { Badge, Card } from "../../../design-system";
import colors from "../../../design-system/theme/colors";

/**
 * RC-002 (Executive Dashboard React Implementation): "Today's Engineering
 * Insight". Per mission instruction ("Do NOT aggregate AI. Do NOT read
 * other workspace state. Do NOT duplicate Engineering AI logic."), this
 * is a static reserved placeholder only -- it deliberately does NOT
 * import or render any of the canonical EngineeringAI* components (those
 * expect a real EngineeringAIResponse; passing one a fabricated response
 * would itself be the forbidden "duplicate/fabricate AI" behaviour). No
 * postEngineeringAI call, no aggregation across the six live workspaces.
 */
export default function EngineeringInsightPanel() {
  return (
    <Card title="Today's Engineering Insight">
      <div style={{ border: `1px dashed ${colors.border}`, borderRadius: 8, padding: 16 }}>
        <Badge variant="info">Reserved</Badge>
        <p style={{ color: colors.textMuted, marginTop: 8, marginBottom: 0 }}>
          Engineering AI Summary — Reserved for the Future Aggregation Platform. No cross-workspace
          Engineering AI aggregation exists yet; this panel does not read, poll, or summarize any
          workspace's AI state.
        </p>
      </div>
    </Card>
  );
}
