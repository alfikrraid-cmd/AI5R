import colors from "../theme/colors";
import spacing from "../theme/spacing";

export default function Sidebar({ items = [], activeKey, onSelect }) {
  return (
    <nav
      style={{
        background: colors.panel,
        padding: spacing.md,
        display: "flex",
        flexDirection: "column",
        gap: spacing.xs,
        minWidth: 180,
      }}
    >
      {items.map((item) => {
        const isActive = item.key === activeKey;

        return (
          <span
            key={item.key}
            role="button"
            aria-current={isActive ? "true" : undefined}
            onClick={() => onSelect(item.key)}
            style={{
              color: isActive ? colors.text : colors.textMuted,
              fontWeight: isActive ? "bold" : "normal",
              cursor: "pointer",
              padding: `${spacing.xs}px ${spacing.sm}px`,
              borderRadius: spacing.xs,
              background: isActive ? colors.background : "transparent",
            }}
          >
            {item.label}
          </span>
        );
      })}
    </nav>
  );
}
