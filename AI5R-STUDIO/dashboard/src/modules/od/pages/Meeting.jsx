import { PageHeader } from "../../../design-system";
import ExecutiveCard from "../components/ExecutiveCard";
import sampleExecutives from "../data/sampleExecutives";
import "./Meeting.css";

/**
 * The Meeting layout (per layouts.md) — a low-commitment way to see who is
 * present in the company before asking them to do anything (OD-002,
 * Suggested Next Actions: "Meet your executives").
 */
export default function Meeting() {
  return (
    <div className="od-meeting">
      <PageHeader title="Meeting" subtitle="Your executives, in the room." />

      <div className="od-meeting-grid">
        {sampleExecutives.map((executive) => (
          <ExecutiveCard key={executive.id} executive={executive} showGreeting />
        ))}
      </div>
    </div>
  );
}
