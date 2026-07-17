import Panel from "./Panel";
import colors from "../theme/colors";

export default function EmptyState({ title, description }) {
  return (
    <Panel className="ds-empty-state">
      <p style={{ color: colors.text, fontWeight: "bold" }}>{title}</p>

      {description ? (
        <p data-testid="empty-state-description" style={{ color: colors.textMuted }}>
          {description}
        </p>
      ) : null}
    </Panel>
  );
}
