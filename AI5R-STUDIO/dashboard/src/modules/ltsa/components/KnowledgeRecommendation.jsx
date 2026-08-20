import { EmptySection } from "./KnowledgeCard";
import { formatConfidence } from "../utils/engineeringAIRender";

// MWO-LTSA-032B -- KnowledgeRecommendation: Recommendation panel body
// (KnowledgeCard variant="prose"), bound to the REAL, deterministic
// RecommendationEngine (CORE-SERVICES/API/recommendation_engine.py,
// MWO-LTSA-031F/R1) -- not the AI copilot pipeline (EngineeringAI*), and
// not the placeholder single-object `recommendation?: {...}` shape the
// original Knowledge Panel spec (031E-R1) sketched before
// RecommendationEngine existed. RecommendationEngine.recommend() returns
// 0-5 Recommendation objects (priority/category/title/description/
// evidence/confidence/action), so this renders a LIST, not a single card.
//
// Reuses formatConfidence() from utils/engineeringAIRender.js unchanged
// (per that file's own "No duplicated rendering" discipline) rather than
// re-deriving percentage formatting here.
//
// loading/error are real, tested states this component supports on its
// own -- in the current integration (one shared Knowledge API call) they
// are always false/null by the time this renders, since the whole
// workspace already resolved. They exist as a ready contract, not dead
// code: see the deliverable report's Architecture Impact section.
const PRIORITY_TO_SEVERITY = { 100: "critical", 90: "high", 70: "attention" };
const PRIORITY_TO_LABEL = { 100: "Critical", 90: "High", 70: "Medium" };

export default function KnowledgeRecommendation({ recommendations = [], loading = false, error = null }) {
  if (loading) {
    return (
      <div data-testid="knowledge-recommendation-loading">
        <div className="skel skel-text skel-line-lg" />
        <div className="skel skel-text skel-line-md" />
      </div>
    );
  }

  if (error) {
    return <EmptySection title="Gagal memuat rekomendasi" description={error} error />;
  }

  if (!recommendations.length) {
    return (
      <EmptySection
        title="Belum ada rekomendasi"
        description="Tidak ada aturan yang terpicu untuk peralatan ini."
      />
    );
  }

  return (
    <div data-testid="knowledge-recommendation">
      {recommendations.map((rec) => (
        <div className="eng-insight-section" key={rec.id} data-testid="knowledge-recommendation-item">
          <span className={`status-signal ${PRIORITY_TO_SEVERITY[rec.priority] ?? "unavailable"}`}>
            <span className="dot-lg" />
            {PRIORITY_TO_LABEL[rec.priority] ?? "Unknown"}
          </span>
          <p className="eng-insight-body">
            <strong>{rec.title}</strong>
            <br />
            {rec.description}
          </p>
          <div className="conf-meter">
            <div className="conf-meter-track">
              <div className="conf-meter-fill" style={{ width: formatConfidence(rec.confidence) }} />
            </div>
            <span className="conf-meter-value">{formatConfidence(rec.confidence)}</span>
          </div>
          <div className="info-row">
            <span className="k">Recommended Action</span>
            <span className="v">{rec.action}</span>
          </div>
          {rec.evidence?.length ? (
            <ul>
              {rec.evidence.map((item, index) => (
                <li className="info-row" key={index}>
                  <span className="k">
                    {item.source} — {item.field}
                  </span>
                  <span className="v">{item.value}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ))}
    </div>
  );
}
