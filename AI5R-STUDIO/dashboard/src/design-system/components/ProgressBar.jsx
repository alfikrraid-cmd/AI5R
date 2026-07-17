import colors from "../theme/colors";
import spacing from "../theme/spacing";

function clampPercent(value, max) {
  if (!max) {
    return 0;
  }

  const percent = (value / max) * 100;

  return Math.min(100, Math.max(0, percent));
}

export default function ProgressBar({ value = 0, max = 100, label }) {
  const percent = clampPercent(value, max);

  return (
    <div className="ds-progress-bar">
      {label ? (
        <div className="ds-progress-bar-label" style={{ color: colors.textMuted }}>
          {label}
        </div>
      ) : null}

      <div
        className="ds-progress-bar-track"
        style={{ background: colors.border, borderRadius: spacing.xs, height: spacing.xs }}
      >
        <div
          className="ds-progress-bar-fill"
          data-testid="progress-bar-fill"
          style={{
            width: `${percent}%`,
            background: colors.info,
            borderRadius: spacing.xs,
            height: "100%",
          }}
        />
      </div>
    </div>
  );
}
