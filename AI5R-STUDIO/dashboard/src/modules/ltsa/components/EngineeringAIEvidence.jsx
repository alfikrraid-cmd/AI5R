import { renderAIItem } from "../utils/engineeringAIRender";

/**
 * Presentational only. Self-contained section (heading + content) for
 * EngineeringAIResponse.evidence, matching the exact "Evidence Strip"
 * section markup the Golden Reference already used. No fetch, no Router,
 * no state, no recommendation logic.
 */
export default function EngineeringAIEvidence({ response }) {
  const evidence = response?.evidence ?? [];
  return (
    <section className="assessment-section" data-testid="ai-evidence">
      <div className="section-head">
        <h2>Evidence Strip</h2>
      </div>
      {evidence.length ? (
        evidence.map((item, index) => {
          const { key, text } = renderAIItem(item, index);
          return (
            <div className="info-row" key={key}>
              <span className="v">{text}</span>
            </div>
          );
        })
      ) : (
        <p className="v">No evidence strip available.</p>
      )}
    </section>
  );
}
