import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

// MWO-LTSA-ASSET360-CONSOLIDATION-001 -- optional sticky section navigator.
// These are page anchors (scrollIntoView against KnowledgeSection's own
// `id={kn-section-${id}}`), NOT separate routes/pages -- clicking never
// calls onNavigate/changes the URL, only scrolls within this one page, per
// the mission's explicit "Click = scroll to section... NOT separate
// routes/pages" rule.
const SECTIONS = [
  { id: "summary", label: "Overview" },
  { id: "condition", label: "Condition" },
  { id: "maintenance", label: "Maintenance" },
  { id: "seal", label: "Seal" },
  { id: "work-orders", label: "Work Orders" },
  // MWO-LTSA-ASSET360-COMPLETENESS-FIX-021B (item B) -- this button used
  // to be labeled "Documents" while pointing at id "drawings" (the Drawings
  // section), mislabeling the nav since no separate Documents section
  // existed yet. Now two distinct entries for two distinct sections.
  { id: "drawings", label: "Drawings" },
  { id: "documents", label: "Documents" },
  { id: "ai-copilot", label: "AI" },
];

function scrollToSection(sectionId) {
  const target = document.getElementById(`kn-section-${sectionId}`);
  target?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function AssetSectionNav() {
  return (
    <nav
      aria-label="Asset 360 sections"
      className="no-print"
      style={{
        position: "sticky",
        top: 0,
        zIndex: 5,
        display: "flex",
        flexWrap: "wrap",
        gap: spacing.xs,
        padding: `${spacing.xs}px 0`,
        background: colors.background,
        borderBottom: `1px solid ${colors.border}`,
        marginBottom: spacing.sm,
      }}
    >
      {SECTIONS.map((section) => (
        <button
          key={section.id}
          type="button"
          onClick={() => scrollToSection(section.id)}
          style={{
            padding: `2px ${spacing.sm}px`,
            borderRadius: spacing.xs,
            border: `1px solid ${colors.border}`,
            background: "transparent",
            color: colors.text,
            cursor: "pointer",
            fontSize: 12,
          }}
        >
          {section.label}
        </button>
      ))}
    </nav>
  );
}
