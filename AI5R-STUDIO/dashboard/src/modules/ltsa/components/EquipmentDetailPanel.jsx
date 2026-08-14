import { Badge, EmptyState, Panel } from "../../../design-system";
import { equipmentStatusVariant } from "../utils/equipmentFilters";
import InspectionHistoryPanel from "./InspectionHistoryPanel";

const FIELDS = [
  ["equipment_id", "Equipment ID"],
  ["tag_number", "Tag Number"],
  ["equipment_type", "Equipment Type"],
  ["area", "Area"],
  ["location", "Location"],
  ["manufacturer", "Manufacturer"],
  ["model", "Model"],
  ["serial_number", "Serial Number"],
];

export default function EquipmentDetailPanel({
  equipment,
  loading,
  error,
  inspections = [],
  inspectionsLoading = false,
  inspectionsError = null,
  selectedInspection = null,
  onSelectInspection = () => {},
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
  return (
    <aside aria-label="Equipment inspector">
      {loading ? (
        <Panel>
          <p>Loading equipment details...</p>
        </Panel>
      ) : error ? (
        <Panel>
          <p role="alert">{error}</p>
        </Panel>
      ) : !equipment ? (
        <EmptyState
          title="No equipment selected"
          description="Select a row to inspect the complete equipment record."
        />
      ) : (
        <Panel className="equipment-inspector">
          <div className="equipment-inspector-heading">
            <div>
              <p className="equipment-inspector-eyebrow">Equipment inspector</p>
              <h2>{equipment.equipment_name}</h2>
            </div>
            <Badge variant={equipmentStatusVariant(equipment.status)}>
              {equipment.status}
            </Badge>
          </div>

          <dl className="equipment-detail-list">
            {FIELDS.map(([key, label]) => (
              <div key={key}>
                <dt>{label}</dt>
                <dd>{equipment[key] || "â€”"}</dd>
              </div>
            ))}
          </dl>

          <InspectionHistoryPanel
            inspections={inspections}
            loading={inspectionsLoading}
            error={inspectionsError}
            selectedInspection={selectedInspection}
            onSelect={onSelectInspection}
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
        </Panel>
      )}
    </aside>
  );
}
