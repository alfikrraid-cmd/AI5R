import { useState } from "react";
import { Card, SearchBox } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import {
  applyLibraryScope,
  DOCUMENT_TYPES,
  groupDocumentsByCategory,
  matchesDocumentSearch,
  matchesDocumentType,
} from "../utils/documentMapping";

const SCOPES = [
  { id: "all", label: "All" },
  { id: "recent", label: "Recent" },
  { id: "favorites", label: "Favorites" },
];

/**
 * Document Library: reuses DrawingLibraryPanel's exact tree/treeitem/group
 * role structure and search pattern (the canonical Drawing Workspace
 * reference this RC reuses), extended with the two library features the
 * Drawing Foundation explicitly deferred (scope tabs, type filter) --
 * both already named in the original Drawing Open Design's own
 * LibraryScopeTabs spec, reused here rather than invented fresh.
 * Two top-level folder-tree groups (Reference Documents, Equipment
 * Documents), the latter further grouped by equipment tag exactly like
 * Drawing's single equipment-tag grouping.
 */
export default function DocumentLibraryPanel({
  documents,
  selectedDocumentId,
  onSelectDocument,
  documentTypeFilter,
  onDocumentTypeFilterChange,
}) {
  const [search, setSearch] = useState("");
  const [scope, setScope] = useState("all");

  const scoped = applyLibraryScope(documents, scope);
  const filtered = scoped.filter(
    (document) => matchesDocumentSearch(document, search) && matchesDocumentType(document, documentTypeFilter)
  );
  const { reference, equipment } = groupDocumentsByCategory(filtered);

  function renderRow(document) {
    const isSelected = document.id === selectedDocumentId;
    return (
      <button
        key={document.id}
        type="button"
        role="treeitem"
        aria-selected={isSelected}
        onClick={() => onSelectDocument(document.id)}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: spacing.sm,
          textAlign: "left",
          width: "100%",
          padding: spacing.xs,
          borderRadius: spacing.xs,
          border: `1px solid ${isSelected ? colors.info : colors.border}`,
          background: isSelected ? colors.background : "transparent",
          color: colors.text,
          cursor: "pointer",
        }}
      >
        <span>
          <div>{document.title}</div>
          <div style={{ fontSize: 12, color: colors.textMuted }}>{document.documentNumber}</div>
        </span>
        <span style={{ fontSize: 11, color: colors.textMuted }}>
          {document.favorite ? "★ " : ""}Rev {document.currentRevision}
        </span>
      </button>
    );
  }

  return (
    <Card title="Document Library">
      <div style={{ marginBottom: spacing.sm }}>
        <SearchBox
          value={search}
          onChange={setSearch}
          placeholder="Search equipment, document number, title…"
        />
      </div>

      <div role="tablist" aria-label="Library scope" style={{ display: "flex", gap: spacing.xs, marginBottom: spacing.sm }}>
        {SCOPES.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={scope === item.id}
            onClick={() => setScope(item.id)}
            style={{
              padding: `${spacing.xs}px ${spacing.sm}px`,
              borderRadius: 16,
              border: `1px solid ${scope === item.id ? colors.info : colors.border}`,
              background: scope === item.id ? colors.background : "transparent",
              color: colors.text,
              cursor: "pointer",
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div style={{ marginBottom: spacing.sm }}>
        <label>
          <span style={{ fontSize: 12, color: colors.textMuted, marginRight: spacing.xs }}>Type</span>
          <select
            aria-label="Filter by document type"
            value={documentTypeFilter}
            onChange={(event) => onDocumentTypeFilterChange(event.target.value)}
          >
            <option value="">All types</option>
            {DOCUMENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
      </div>

      {reference.length === 0 && equipment.length === 0 ? (
        <p style={{ color: colors.textMuted }}>No documents match the current search/filter.</p>
      ) : (
        <div role="tree" aria-label="Document tree">
          {reference.length > 0 ? (
            <div role="group" style={{ marginBottom: spacing.md }}>
              <div role="treeitem" aria-expanded="true" style={{ fontWeight: "bold", color: colors.text, marginBottom: spacing.xs }}>
                Reference Documents
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs, paddingLeft: spacing.md }}>
                {reference.map(renderRow)}
              </div>
            </div>
          ) : null}

          {equipment.map((group) => (
            <div key={group.equipmentTag} role="group" style={{ marginBottom: spacing.md }}>
              <div role="treeitem" aria-expanded="true" style={{ fontWeight: "bold", color: colors.text, marginBottom: spacing.xs }}>
                {group.equipmentTag}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs, paddingLeft: spacing.md }}>
                {group.documents.map(renderRow)}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
