import colors from "../theme/colors";
import spacing from "../theme/spacing";

export default function Tabs({ items = [], activeKey, onChange }) {
  return (
    <div role="tablist" style={{ display: "flex", gap: spacing.md, borderBottom: `1px solid ${colors.border}` }}>
      {items.map((item) => {
        const isActive = item.key === activeKey;

        return (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(item.key)}
            style={{
              background: "transparent",
              border: "none",
              color: isActive ? colors.text : colors.textMuted,
              fontWeight: isActive ? "bold" : "normal",
              borderBottom: isActive ? `2px solid ${colors.info}` : "2px solid transparent",
              padding: `${spacing.xs}px ${spacing.sm}px`,
              cursor: "pointer",
            }}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
