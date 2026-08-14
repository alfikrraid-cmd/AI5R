import { Card, EmptyState, Modal, PageHeader, Timeline } from "../../../design-system";
import ExecutiveCard from "../components/ExecutiveCard";
import SuggestedActionsPanel from "../components/SuggestedActionsPanel";
import sampleExecutives from "../data/sampleExecutives";
import "./CompanyHeadquarters.css";

/**
 * The Workspace layout (per layouts.md), labeled "Company Headquarters"
 * per future-office.md's "I've just entered my company's headquarters."
 * Per OD-002: not a dashboard reporting on a company that exists elsewhere
 * — this *is* the company, freshly born from a sealed Business Blueprint.
 */
export default function CompanyHeadquarters({ blueprint, hasSeenBriefing, onDismissBriefing, onNavigate }) {
  const briefingExecutive = sampleExecutives[0];

  return (
    <div className="od-headquarters">
      <PageHeader
        title={blueprint.businessIdentity || "Your Company"}
        subtitle="Your Business Blueprint is sealed. Here is your headquarters."
      />

      <Modal isOpen={!hasSeenBriefing} onClose={onDismissBriefing} title="Executive Briefing">
        <p>{briefingExecutive.greeting}</p>
        <p>Your blueprint has been reviewed. Your executives are available whenever you need them.</p>
      </Modal>

      <Card title="Your Executives">
        <div className="od-headquarters-executive-row">
          {sampleExecutives.map((executive) => (
            <ExecutiveCard key={executive.id} executive={executive} />
          ))}
        </div>
      </Card>

      <Card title="Artifacts">
        <EmptyState
          title="Nothing produced yet"
          description="This is where the work your company does will appear."
        />
      </Card>

      <Timeline
        title="Company Timeline"
        activities={[`Business Blueprint sealed — ${blueprint.capturedAt}`]}
      />

      <SuggestedActionsPanel onNavigate={onNavigate} />
    </div>
  );
}
