import { renderAIItem } from "../utils/engineeringAIRender";

/**
 * Presentational only. Self-contained section (heading + content) for
 * EngineeringAIResponse.findings, matching the exact section/heading
 * markup the Golden Reference (FailureAnalysisWorkspace) already used, so
 * any LTSA workspace can drop this in without reconstructing the wrapper.
 * No fetch, no Router, no state, no recommendation logic.
 */
export default function EngineeringAIFindings({ response }) {
  const findings = response?.findings ?? [];
  return (
    <section className="assessment-section" data-testid="ai-findings">
      <div className="section-head">
        <h2>Engineering Findings</h2>
      </div>
      {findings.length ? (
        findings.map((item, index) => {
          const { key, text } = renderAIItem(item, index);
          return (
            <div className="info-row" key={key}>
              <span className="v">{text}</span>
            </div>
          );
        })
      ) : (
        <p className="v">No findings identified.</p>
      )}
    </section>
  );
}
