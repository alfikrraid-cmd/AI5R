import { renderAIItem } from "../utils/engineeringAIRender";

/**
 * Presentational only. Self-contained section (heading + content) for
 * EngineeringAIResponse.recommendations, matching the exact
 * "Recommendation" section markup the Golden Reference already used.
 * Renders whatever the response already contains -- it does not compute,
 * rank, or generate recommendations itself (that is
 * EngineeringAIOrchestrator's job, upstream of this component). No
 * fetch, no Router, no state.
 */
export default function EngineeringAIRecommendation({ response }) {
  const recommendations = response?.recommendations ?? [];
  return (
    <section className="assessment-section" data-testid="ai-recommendation">
      <div className="section-head">
        <h2>Recommendation</h2>
      </div>
      {recommendations.length ? (
        recommendations.map((item, index) => {
          const { key, text } = renderAIItem(item, index);
          return (
            <div className="info-row" key={key}>
              <span className="v">{text}</span>
            </div>
          );
        })
      ) : (
        <p className="v">No recommendation available.</p>
      )}
    </section>
  );
}
