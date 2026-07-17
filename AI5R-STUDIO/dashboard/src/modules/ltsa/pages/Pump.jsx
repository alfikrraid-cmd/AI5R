import { useMemo, useState } from "react";
import { PageHeader } from "../../../design-system";
import PumpFilterBar from "../components/PumpFilterBar";
import PumpRegistryTable from "../components/PumpRegistryTable";
import PumpDetailPanel from "../components/PumpDetailPanel";
import samplePumps from "../data/samplePumps";
import "./Pump.css";

function matchesSearch(pump, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    pump.tag.toLowerCase().includes(term) ||
    pump.name.toLowerCase().includes(term) ||
    pump.manufacturer.toLowerCase().includes(term)
  );
}

export default function Pump() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedCode, setSelectedCode] = useState(null);

  const statusOptions = useMemo(
    () => [...new Set(samplePumps.map((pump) => pump.status))],
    []
  );

  const filteredPumps = useMemo(
    () =>
      samplePumps.filter(
        (pump) =>
          matchesSearch(pump, search) &&
          (statusFilter === "ALL" || pump.status === statusFilter)
      ),
    [search, statusFilter]
  );

  const selectedPump = filteredPumps.find((pump) => pump.code === selectedCode) ?? null;

  return (
    <div>
      <PageHeader title="Pump Workspace" subtitle="LTSA Engineering — Pump Registry" />

      <PumpFilterBar
        searchValue={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statusOptions={statusOptions}
      />

      <div className="pump-workspace-layout">
        <div className="pump-workspace-registry">
          <PumpRegistryTable
            pumps={filteredPumps}
            selectedCode={selectedCode}
            onSelect={setSelectedCode}
          />
        </div>

        <div className="pump-workspace-detail">
          <PumpDetailPanel pump={selectedPump} />
        </div>
      </div>
    </div>
  );
}
