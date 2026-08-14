import { Badge, EmptyState, Panel } from "../../../design-system";
import {
  findingSeverityVariant,
  findingStatusVariant,
} from "../utils/findingSelectors";
import WorkOrderPanel from "./WorkOrderPanel";


function MetadataList({ title, items, idKey, labelKey, typeKey }) {
  if (!Array.isArray(items) || items.length === 0) {
    return null;
  }

  return (
    <section className="finding-metadata">
      <h5>{title}</h5>
      <ul>
        {items.map((item) => (
          <li key={item[idKey]}>
            <span>{item[labelKey]}</span>
            {item[typeKey] ? <small>{item[typeKey]}</small> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function FindingInspector({
  finding,
  workOrders,
  workOrdersLoading,
  workOrdersError,
  selectedWorkOrder,
  onSelectWorkOrder,
}) {
  return (
    <section className="finding-detail" aria-label="Finding inspector">
      <div className="finding-detail-heading">
        <h4>Finding {finding.finding_id}</h4>
        <Badge variant={findingStatusVariant(finding.status)}>
          {finding.status}
        </Badge>
      </div>

      <dl>
        <div>
          <dt>Severity</dt>
          <dd>
            <Badge variant={findingSeverityVariant(finding.severity)}>
              {finding.severity}
            </Badge>
          </dd>
        </div>
        <div>
          <dt>Category</dt>
          <dd>{finding.category}</dd>
        </div>
        <div>
          <dt>Recommendation</dt>
          <dd>{finding.recommendation}</dd>
        </div>
      </dl>

      <MetadataList
        title="Photos"
        items={finding.photos}
        idKey="photo_id"
        labelKey="filename"
        typeKey="media_type"
      />
      <MetadataList
        title="Linked documents"
        items={finding.documents}
        idKey="document_id"
        labelKey="title"
        typeKey="document_type"
      />
      <WorkOrderPanel
        workOrders={workOrders}
        loading={workOrdersLoading}
        error={workOrdersError}
        selectedWorkOrder={selectedWorkOrder}
        onSelect={onSelectWorkOrder}
      />
    </section>
  );
}

export default function FindingPanel({
  findings,
  loading,
  error,
  selectedFinding,
  onSelect,
  workOrders = [],
  workOrdersLoading = false,
  workOrdersError = null,
  selectedWorkOrder = null,
  onSelectWorkOrder = () => {},
}) {
  if (loading) {
    return (
      <Panel>
        <p>Loading findings...</p>
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

  if (findings.length === 0) {
    return (
      <EmptyState
        title="No findings recorded"
        description="This inspection does not have recorded findings."
      />
    );
  }

  return (
    <section className="finding-panel" aria-label="Inspection findings">
      <h4>Findings</h4>
      <div className="finding-list">
        {findings.map((finding) => (
          <button
            key={finding.finding_id}
            type="button"
            aria-label={`${finding.finding_id} ${finding.category}`}
            aria-pressed={finding.finding_id === selectedFinding?.finding_id}
            onClick={() => onSelect(finding)}
          >
            <span>
              <strong>{finding.category}</strong>
              <small>{finding.recommendation}</small>
            </span>
            <Badge variant={findingSeverityVariant(finding.severity)}>
              {finding.severity}
            </Badge>
          </button>
        ))}
      </div>

      {selectedFinding ? (
        <FindingInspector
          finding={selectedFinding}
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
