import { renderAIItem } from "../utils/engineeringAIRender";

/**
 * Presentational only. Self-contained rail section (heading + content)
 * for EngineeringAIResponse.source_references, matching the exact
 * markup the Golden Reference already used. No fetch, no Router, no
 * state.
 */
export default function EngineeringAISourceReferences({ response }) {
  const sourceReferences = response?.source_references ?? [];
  return (
    <section className="rail-section" data-testid="ai-source-references">
      <h3>Source References</h3>
      {sourceReferences.length ? (
        sourceReferences.map((item, index) => {
          const { key, text } = renderAIItem(item, index);
          return (
            <div className="info-row" key={key}>
              <span className="v">{text}</span>
            </div>
          );
        })
      ) : (
        <p className="v">No source references available.</p>
      )}
    </section>
  );
}
