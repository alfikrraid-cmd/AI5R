import { useEffect, useMemo, useRef, useState } from "react";

import {
  getEquipment,
  getFindingWorkOrders,
  getInspectionFindings,
  getEquipmentInspections,
  getEquipmentList,
} from "../../../api/ai5rClient";
import { PageHeader, Panel } from "../../../design-system";
import EquipmentDetailPanel from "../components/EquipmentDetailPanel";
import EquipmentFilterBar from "../components/EquipmentFilterBar";
import EquipmentTable from "../components/EquipmentTable";
import {
  equipmentFilterOptions,
  filterEquipment,
} from "../utils/equipmentFilters";
import "./Equipment.css";

const INITIAL_FILTERS = {
  area: "ALL",
  equipmentType: "ALL",
  status: "ALL",
};

export default function Equipment() {
  const [equipment, setEquipment] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState(null);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedEquipment, setSelectedEquipment] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [inspections, setInspections] = useState([]);
  const [inspectionsLoading, setInspectionsLoading] = useState(false);
  const [inspectionsError, setInspectionsError] = useState(null);
  const [selectedInspection, setSelectedInspection] = useState(null);
  const [findings, setFindings] = useState([]);
  const [findingsLoading, setFindingsLoading] = useState(false);
  const [findingsError, setFindingsError] = useState(null);
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [workOrders, setWorkOrders] = useState([]);
  const [workOrdersLoading, setWorkOrdersLoading] = useState(false);
  const [workOrdersError, setWorkOrdersError] = useState(null);
  const [selectedWorkOrder, setSelectedWorkOrder] = useState(null);

  const equipmentSelectionToken = useRef(0);
  const inspectionSelectionToken = useRef(0);
  const findingSelectionToken = useRef(0);

  useEffect(() => {
    let active = true;

    getEquipmentList()
      .then((items) => {
        if (active) {
          setEquipment(items);
          setListError(null);
        }
      })
      .catch(() => {
        if (active) {
          setListError("Equipment data could not be loaded.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const options = useMemo(
    () => ({
      areas: equipmentFilterOptions(equipment, "area"),
      equipmentTypes: equipmentFilterOptions(equipment, "equipment_type"),
      statuses: equipmentFilterOptions(equipment, "status"),
    }),
    [equipment]
  );

  const filteredEquipment = useMemo(
    () => filterEquipment(equipment, { ...filters, search }),
    [equipment, filters, search]
  );

  function updateFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function selectEquipment(item) {
    const token = ++equipmentSelectionToken.current;

    setSelectedId(item.equipment_id);
    setSelectedEquipment(null);
    setDetailError(null);
    setDetailLoading(true);
    setInspections([]);
    setInspectionsError(null);
    setInspectionsLoading(true);
    setSelectedInspection(null);
    setFindings([]);
    setFindingsError(null);
    setFindingsLoading(false);
    setSelectedFinding(null);
    setWorkOrders([]);
    setWorkOrdersError(null);
    setWorkOrdersLoading(false);
    setSelectedWorkOrder(null);

    getEquipment(item.equipment_id)
      .then((data) => {
        if (equipmentSelectionToken.current === token) {
          setSelectedEquipment(data);
        }
      })
      .catch(() => {
        if (equipmentSelectionToken.current === token) {
          setDetailError("Equipment details could not be loaded.");
        }
      })
      .finally(() => {
        if (equipmentSelectionToken.current === token) {
          setDetailLoading(false);
        }
      });

    getEquipmentInspections(item.equipment_id)
      .then((data) => {
        if (equipmentSelectionToken.current === token) {
          setInspections(data);
        }
      })
      .catch(() => {
        if (equipmentSelectionToken.current === token) {
          setInspectionsError("Inspection history could not be loaded.");
        }
      })
      .finally(() => {
        if (equipmentSelectionToken.current === token) {
          setInspectionsLoading(false);
        }
      });
  }

  function selectInspection(inspection) {
    const token = ++inspectionSelectionToken.current;

    setSelectedInspection(inspection);
    setFindings([]);
    setFindingsError(null);
    setFindingsLoading(true);
    setSelectedFinding(null);
    setWorkOrders([]);
    setWorkOrdersError(null);
    setWorkOrdersLoading(false);
    setSelectedWorkOrder(null);

    getInspectionFindings(inspection.inspection_id)
      .then((data) => {
        if (inspectionSelectionToken.current === token) {
          setFindings(data);
        }
      })
      .catch(() => {
        if (inspectionSelectionToken.current === token) {
          setFindingsError("Findings could not be loaded.");
        }
      })
      .finally(() => {
        if (inspectionSelectionToken.current === token) {
          setFindingsLoading(false);
        }
      });
  }

  function selectFinding(finding) {
    const token = ++findingSelectionToken.current;

    setSelectedFinding(finding);
    setWorkOrders([]);
    setWorkOrdersError(null);
    setWorkOrdersLoading(true);
    setSelectedWorkOrder(null);

    getFindingWorkOrders(finding.finding_id)
      .then((data) => {
        if (findingSelectionToken.current === token) {
          setWorkOrders(data);
        }
      })
      .catch(() => {
        if (findingSelectionToken.current === token) {
          setWorkOrdersError("Work orders could not be loaded.");
        }
      })
      .finally(() => {
        if (findingSelectionToken.current === token) {
          setWorkOrdersLoading(false);
        }
      });
  }
  return (
    <div>
      <PageHeader
        title="Equipment"
        subtitle="Browse imported equipment from the Enterprise API"
      />

      <EquipmentFilterBar
        search={search}
        onSearchChange={setSearch}
        filters={filters}
        onFilterChange={updateFilter}
        options={options}
      />

      {loading ? (
        <Panel>
          <p>Loading equipment...</p>
        </Panel>
      ) : listError ? (
        <Panel>
          <p role="alert">{listError}</p>
        </Panel>
      ) : (
        <div className="equipment-workspace-layout">
          <section aria-label="Equipment list">
            <EquipmentTable
              equipment={filteredEquipment}
              selectedId={selectedId}
              onSelect={selectEquipment}
            />
          </section>
          <EquipmentDetailPanel
            equipment={selectedEquipment}
            loading={detailLoading}
            error={detailError}
            inspections={inspections}
            inspectionsLoading={inspectionsLoading}
            inspectionsError={inspectionsError}
            selectedInspection={selectedInspection}
            onSelectInspection={selectInspection}
            findings={findings}
            findingsLoading={findingsLoading}
            findingsError={findingsError}
            selectedFinding={selectedFinding}
            onSelectFinding={selectFinding}
            workOrders={workOrders}
            workOrdersLoading={workOrdersLoading}
            workOrdersError={workOrdersError}
            selectedWorkOrder={selectedWorkOrder}
            onSelectWorkOrder={setSelectedWorkOrder}
          />
        </div>
      )}
    </div>
  );
}
