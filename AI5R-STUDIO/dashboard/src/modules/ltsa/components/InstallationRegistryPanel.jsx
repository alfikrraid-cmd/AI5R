import { useState } from "react";
import { Card, SearchBox, Table } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { matchesInstallationSearch } from "../utils/installationMapping";

const NA = "N/A";

/**
 * MWO-LTSA-INSTALLATION-UI-PHASE-1 -- Installation Registry, the list
 * surface InstallationWorkspace.jsx's own header comment previously
 * documented as deliberately absent ("Installation has exactly one real
 * record today and no registry to browse"). That reasoning no longer
 * holds -- production now has 42 real installation_report rows across 39
 * pumps (verified read-only audit) -- so this is the registry that
 * reasoning always said would be needed once more than one record
 * existed, built the same DocumentLibraryPanel.jsx shape (search box +
 * Card + design-system Table, MWO-LTSA-052A's own template) rather than
 * inventing a new list pattern.
 *
 * Phase 1 scope only (this MWO's own instruction): a single search box
 * across Pump Tag + Seal Type (matchesInstallationSearch()), no scope
 * tabs, no type/date filter, no grouping -- DocumentLibraryPanel's scope
 * tabs/type filter are deliberately NOT reused here, since building them
 * now would be scope this MWO explicitly deferred ("Do NOT build advanced
 * filtering yet").
 *
 * Every displayed cell falls back to the literal string "N/A" (this
 * MWO's own explicit display standard), never a fabricated value and
 * never the "—" placeholder InstallationOpenDesignView.jsx's older,
 * already-shipped rows use elsewhere on this page -- a real, disclosed
 * convention difference confined to this new surface only, not a
 * retroactive rewrite of already-shipped rows this MWO didn't touch.
 */
export default function InstallationRegistryPanel({ installations, selectedInstallationId, onSelectInstallation }) {
  const [search, setSearch] = useState("");

  const filtered = installations.filter((installation) => matchesInstallationSearch(installation, search));

  const columns = [
    { key: "pumpTag", header: "Pump Tag" },
    { key: "area", header: "Area" },
    { key: "date", header: "Installation Date" },
    { key: "sealType", header: "Seal Type" },
    { key: "assemblyGpn", header: "Assembly GPN" },
    { key: "drawingNo", header: "Drawing No." },
    { key: "sourceDocument", header: "Source Document" },
  ];

  const rows = filtered.map((installation) => ({
    __id: installation.id,
    pumpTag: installation.pumpTagNumber ?? installation.plantEquipNo ?? NA,
    area: installation.area ?? NA,
    date: installation.date ?? NA,
    sealType: installation.sealType ?? NA,
    assemblyGpn: installation.assemblyGpn ?? NA,
    drawingNo: installation.drawingNo ?? NA,
    sourceDocument: installation.sourceDocumentName ?? NA,
  }));

  return (
    <Card title="Installation Registry">
      <div style={{ marginBottom: spacing.sm }}>
        <SearchBox value={search} onChange={setSearch} placeholder="Search pump tag, seal type…" />
      </div>

      {rows.length === 0 ? (
        <p style={{ color: colors.textMuted }}>No installation reports match the current search.</p>
      ) : (
        <Table
          rowKey="__id"
          data={rows}
          columns={columns}
          selectedKey={selectedInstallationId}
          onRowClick={(row) => onSelectInstallation(row.__id)}
        />
      )}
    </Card>
  );
}
