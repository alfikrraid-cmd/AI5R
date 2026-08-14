import { Badge } from "../../../design-system";
import { inspectionStatusVariant } from "../utils/inspectionSelectors";


export default function InspectionTimeline({
  inspections,
  selectedId,
  onSelect,
}) {
  return (
    <ol className="inspection-timeline" aria-label="Inspection timeline">
      {inspections.map((inspection) => (
        <li key={inspection.inspection_id}>
          <button
            type="button"
            aria-pressed={inspection.inspection_id === selectedId}
            aria-label={`${inspection.inspection_id} ${inspection.inspection_date}`}
            onClick={() => onSelect(inspection)}
          >
            <span className="inspection-timeline-marker" />
            <span className="inspection-timeline-content">
              <span className="inspection-timeline-heading">
                <strong>{inspection.inspection_date}</strong>
                <Badge variant={inspectionStatusVariant(inspection.status)}>
                  {inspection.status}
                </Badge>
              </span>
              <span>{inspection.engineer}</span>
              <span>{inspection.result}</span>
              <small>{inspection.finding_count} findings</small>
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}
