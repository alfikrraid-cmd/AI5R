import { Badge, EmptyState, Panel } from "../../../design-system";
import {
  inspectionStatusVariant,
  inspectionSummary,
} from "../utils/inspectionSelectors";
import FindingPanel from "./FindingPanel";
import InspectionSummary from "./InspectionSummary";
import InspectionTimeline from "./InspectionTimeline";


function InspectionInspector({
  inspection,
  findings,
  findingsLoading,
  findingsError,
  selectedFinding,
  onSelectFinding,
  workOrders,
  workOrdersLoading,
  workOrdersError,
  selectedWorkOrder,
  onSelectWorkOrder,
}) {
  return (
    <section className="inspection-detail" aria-label="Inspection inspector">
      <div className="inspection-detail-heading">
        <h3>Inspection {inspection.inspection_id}</h3>
        <Badge variant={inspectionStatusVariant(inspection.status)}>
          {inspection.status}
        </Badge>
      </div>
      <dl>
        <div>
          <dt>Date</dt>
          <dd>{inspection.inspection_date}</dd>
        </div>
        <div>
          <dt>Engineer</dt>
          <dd>{inspection.engineer}</dd>
        </div>
        <div>
          <dt>Result</dt>
          <dd>{inspection.result}</dd>
        </div>
        <div>
          <dt>Finding count</dt>
          <dd>{inspection.finding_count}</dd>
        </div>
      </dl>

      <FindingPanel
        findings={findings}
        loading={findingsLoading}
        error={findingsError}
        selectedFinding={selectedFinding}
        onSelect={onSelectFinding}
        workOrders={workOrders}
        workOrdersLoading={workOrdersLoading}
        workOrdersError={workOrdersError}
        selectedWorkOrder={selectedWorkOrder}
        onSelectWorkOrder={onSelectWorkOrder}
      />
    </section>
  );
}

export default function InspectionHistoryPanel({
  inspections,
  loading,
  error,
  selectedInspection,
  onSelect,
  findings = [],
  findingsLoading = false,
  findingsError = null,
  selectedFinding = null,
  onSelectFinding = () => {},
  workOrders = [],
  workOrdersLoading = false,
  workOrdersError = null,
  selectedWorkOrder = null,
  onSelectWorkOrder = () => {},
}) {
  if (loading) {
    return (
      <Panel>
        <p>Loading inspection history...</p>
      </Panel>
    );
  }

  if (error) {
    return (
      <Panel>
        <p role="alert">{error}</p>
      </Panel>
    );
  }

  if (inspections.length === 0) {
    return (
      <EmptyState
        title="No inspections recorded"
        description="This equipment does not have inspection history yet."
      />
    );
  }

  return (
    <section className="inspection-history" aria-label="Inspection history">
      <h3>Inspection history</h3>
      <InspectionSummary summary={inspectionSummary(inspections)} />
      <InspectionTimeline
        inspections={inspections}
        selectedId={selectedInspection?.inspection_id}
        onSelect={onSelect}
      />
      {selectedInspection ? (
        <InspectionInspector
          inspection={selectedInspection}
          findings={findings}
          findingsLoading={findingsLoading}
          findingsError={findingsError}
          selectedFinding={selectedFinding}
          onSelectFinding={onSelectFinding}
          workOrders={workOrders}
          workOrdersLoading={workOrdersLoading}
          workOrdersError={workOrdersError}
          selectedWorkOrder={selectedWorkOrder}
          onSelectWorkOrder={onSelectWorkOrder}
        />
      ) : null}
    </section>
  );
}