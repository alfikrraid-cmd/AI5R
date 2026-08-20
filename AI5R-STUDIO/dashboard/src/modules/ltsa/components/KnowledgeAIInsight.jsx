import { formatConfidence } from "../utils/engineeringAIRender";

// MWO-LTSA-035 -- KnowledgeAIInsight: AI Insights body (KnowledgeCard
// variant="prose"), now backed by deterministic EngineeringInsight
// (CORE-SERVICES/API/engineering_insight.py) -- Root Cause, Risk,
// Recommended Action, Confidence, derived from RecommendationEngine +
// EngineeringContextEngine, no LLM, no network, no prompt. Reuses
// formatConfidence() (utils/engineeringAIRender.js) unchanged, same
// discipline as KnowledgeRecommendation.jsx.
//
// When `insight` is absent (no recommendations exist for this pump yet --
// a real, disclosed gap, not an error), falls back to the original locked
// "Segera Hadir" placeholder from MWO-LTSA-032A/032A-R1, unchanged.
const RISK_LABELS = { normal: "normal", attention: "attention", high: "high", critical: "critical" };

function LockedPlaceholder() {
  const fields = [
    { key: "rootCause", label: "Root Cause" },
    { key: "risk", label: "Risk" },
    { key: "remainingLife", label: "Remaining Life" },
    { key: "recommendedAction", label: "Recommended Action" },
    { key: "confidence", label: "Confidence" },
  ];

  return (
    <div data-testid="knowledge-ai-insight">
      <span className="confidence-tier locked">Segera Hadir</span>
      <ul className="future-panel-list">
        {fields.map((field) => (
          <li className="future-panel-item" key={field.key}>
            {field.label}: <span>&mdash;</span>
          </li>
        ))}
      </ul>
      <button type="button" className="btn-secondary" disabled aria-disabled="true">
        Belum Tersedia
      </button>
    </div>
  );
}

export default function KnowledgeAIInsight({ insight }) {
  if (!insight) {
    return <LockedPlaceholder />;
  }

  return (
    <div data-testid="knowledge-ai-insight-real">
      <div className="info-row">
        <span className="k">Root Cause</span>
        <span className="v">{insight.rootCause}</span>
      </div>
      <div className="info-row">
        <span className="k">Risk</span>
        {insight.risk ? (
          <span className={`status-signal ${insight.risk}`}>
            <span className="dot-lg" />
            {RISK_LABELS[insight.risk] ?? insight.risk}
          </span>
        ) : (
          <span className="v">Unavailable</span>
        )}
      </div>
      <div className="info-row">
        <span className="k">Recommended Action</span>
        <span className="v">{insight.recommendedAction}</span>
      </div>
      <div className="conf-meter">
        <div className="conf-meter-track">
          <div className="conf-meter-fill" style={{ width: formatConfidence(insight.confidence) }} />
        </div>
        <span className="conf-meter-value">{formatConfidence(insight.confidence)}</span>
      </div>
    </div>
  );
}
