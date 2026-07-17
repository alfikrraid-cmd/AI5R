import { useMemo, useState } from "react";
import { PageHeader } from "../../../design-system";
import SealFilterBar from "../components/SealFilterBar";
import SealRegistryTable from "../components/SealRegistryTable";
import SealDetailPanel from "../components/SealDetailPanel";
import sampleSeals from "../data/sampleSeals";
import "./Seal.css";

function matchesSearch(seal, search) {
  const term = search.trim().toLowerCase();

  if (!term) {
    return true;
  }

  return (
    seal.name.toLowerCase().includes(term) ||
    seal.type.toLowerCase().includes(term) ||
    seal.manufacturer.toLowerCase().includes(term)
  );
}

export default function Seal() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [selectedCode, setSelectedCode] = useState(null);

  const statusOptions = useMemo(
    () => [...new Set(sampleSeals.map((seal) => seal.status))],
    []
  );

  const filteredSeals = useMemo(
    () =>
      sampleSeals.filter(
        (seal) =>
          matchesSearch(seal, search) &&
          (statusFilter === "ALL" || seal.status === statusFilter)
      ),
    [search, statusFilter]
  );

  const selectedSeal = filteredSeals.find((seal) => seal.code === selectedCode) ?? null;

  return (
    <div>
      <PageHeader title="Seal Workspace" subtitle="LTSA Engineering — Mechanical Seal Registry" />

      <SealFilterBar
        searchValue={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        statusOptions={statusOptions}
      />

      <div className="seal-workspace-layout">
        <div className="seal-workspace-registry">
          <SealRegistryTable
            seals={filteredSeals}
            selectedCode={selectedCode}
            onSelect={setSelectedCode}
          />
        </div>

        <div className="seal-workspace-detail">
          <SealDetailPanel seal={selectedSeal} />
        </div>
      </div>
    </div>
  );
}
