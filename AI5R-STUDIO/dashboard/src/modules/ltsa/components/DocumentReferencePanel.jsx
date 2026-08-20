import { Card } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";
import { DOCUMENT_TYPES } from "../utils/documentMapping";

/**
 * Reference Documents (RC-004 §6). "Navigation only" -- rather than
 * implementing a second, parallel filtering mechanism, each chip drives
 * the exact same `documentTypeFilter` state DocumentLibraryPanel's own
 * "Type" select already owns (both lifted to DocumentWorkspace.jsx, the
 * single source of truth) -- clicking a chip here filters the Document
 * Library to that type, reusing its existing filter rather than
 * duplicating it.
 *
 * MWO-LTSA-052A -- `bare` (optional, default false): when true, renders
 * only the chip row, without the design-system `Card`/title wrapper --
 * for reuse inside DocumentOpenDesignView.jsx's own `Section` chrome
 * (LTSAOpenDesign.css's `.assessment-section`/`.eyebrow`, a different
 * visual system from design-system's `Card`), so the chips aren't nested
 * inside two competing title bars. Default (false) is byte-for-byte
 * unchanged from before this MWO -- every existing consumer/test keeps
 * working exactly as it did.
 */
export default function DocumentReferencePanel({ documentTypeFilter, onDocumentTypeFilterChange, bare = false }) {
  const chips = (
    <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}>
      {DOCUMENT_TYPES.map((type) => {
        const isActive = documentTypeFilter === type;
        return (
          <button
            key={type}
            type="button"
            aria-pressed={isActive}
            onClick={() => onDocumentTypeFilterChange(isActive ? "" : type)}
            style={{
              padding: `${spacing.xs}px ${spacing.sm}px`,
              borderRadius: 16,
              border: `1px solid ${isActive ? colors.info : colors.border}`,
              background: isActive ? colors.background : "transparent",
              color: colors.text,
              cursor: "pointer",
            }}
          >
            {type}
          </button>
        );
      })}
    </div>
  );

  if (bare) {
    return chips;
  }

  return <Card title="Reference Documents">{chips}</Card>;
}
