import colors from "../theme/colors";
import spacing from "../theme/spacing";
import typography from "../theme/typography";

export default function PageHeader({ title, subtitle, actions }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: spacing.lg,
      }}
    >
      <div>
        <h1 style={{ margin: 0, color: colors.text, fontFamily: typography.fontFamily }}>
          {title}
        </h1>

        {subtitle ? (
          <p style={{ margin: 0, color: colors.textMuted }}>{subtitle}</p>
        ) : null}
      </div>

      {actions ? <div>{actions}</div> : null}
    </div>
  );
}
