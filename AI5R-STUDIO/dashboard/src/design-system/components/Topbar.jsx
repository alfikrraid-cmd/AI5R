import colors from "../theme/colors";
import spacing from "../theme/spacing";

export default function Topbar({ title, actions }) {
  return (
    <header
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        background: colors.panel,
        color: colors.text,
        padding: `${spacing.sm}px ${spacing.md}px`,
      }}
    >
      <strong>{title}</strong>

      {actions ? <div>{actions}</div> : null}
    </header>
  );
}
