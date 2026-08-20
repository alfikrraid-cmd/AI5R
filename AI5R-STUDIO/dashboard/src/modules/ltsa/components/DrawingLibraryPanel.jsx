import { useState } from "react";
import { Card, SearchBox } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { groupDrawingsByEquipment } from "../utils/drawingMapping";

function matchesSearch(drawing, term) {
  if (!term) {
    return true;
  }

  const haystack = `${drawing.equipmentTag} ${drawing.drawingNumber} ${drawing.title} ${drawing.drawingType}`.toLowerCase();
  return haystack.includes(term.toLowerCase());
}

/**
 * Drawing Library: folder tree (one node per equipment tag, per the
 * approved IA — drawing-workspace-spec.html §04) + drawing list nested
 * under each node. Foundation scope: always-expanded groups, no
 * collapse/expand interaction, no Recent/Favorites scope tabs (both out
 * of scope for RC-003A — "Nothing more").
 */
export default function DrawingLibraryPanel({ drawings, selectedDrawingId, onSelectDrawing }) {
  const [search, setSearch] = useState("");

  const filtered = drawings.filter((drawing) => matchesSearch(drawing, search));
  const groups = groupDrawingsByEquipment(filtered);

  return (
    <Card title="Drawing Library">
      <div style={{ marginBottom: spacing.sm }}>
        <SearchBox
          value={search}
          onChange={setSearch}
          placeholder="Search equipment, drawing number, title…"
        />
      </div>

      {groups.length === 0 ? (
        <p style={{ color: colors.textMuted }}>
          {search ? <>No drawings match &quot;{search}&quot;.</> : "No drawings available."}
        </p>
      ) : (
        <div role="tree" aria-label="Equipment drawing tree">
          {groups.map((group) => (
            <div key={group.equipmentTag} role="group" style={{ marginBottom: spacing.md }}>
              <div role="treeitem" aria-expanded="true" style={{ fontWeight: "bold", color: colors.text, marginBottom: spacing.xs }}>
                {group.equipmentTag}
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs, paddingLeft: spacing.md }}>
                {group.drawings.map((drawing) => {
                  const isSelected = drawing.id === selectedDrawingId;

                  return (
                    <button
                      key={drawing.id}
                      type="button"
                      role="treeitem"
                      aria-selected={isSelected}
                      onClick={() => onSelectDrawing(drawing.id)}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: spacing.sm,
                        textAlign: "left",
                        padding: spacing.xs,
                        borderRadius: spacing.xs,
                        border: `1px solid ${isSelected ? colors.info : colors.border}`,
                        background: isSelected ? colors.background : "transparent",
                        color: colors.text,
                        cursor: "pointer",
                      }}
                    >
                      <span>
                        <div>{drawing.drawingType}</div>
                        <div style={{ fontSize: 12, color: colors.textMuted }}>{drawing.drawingNumber}</div>
                      </span>
                      <span style={{ fontSize: 11, color: colors.textMuted }}>Rev {drawing.currentRevision}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
