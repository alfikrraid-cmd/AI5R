import { Badge, Card } from "../../../design-system";
import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

const DIRECTION_LABEL = {
  UP: "▲ Rising",
  DOWN: "▼ Falling",
  FLAT: "▬ Stable",
};

const DIRECTION_VARIANT = {
  UP: "danger",
  DOWN: "success",
  FLAT: "info",
};

const HEADERS = ["Week", "PM", "CM", "Work Orders", "Total"];

const thStyle = {
  textAlign: "left",
  color: colors.textMuted,
  borderBottom: `1px solid ${colors.border}`,
  padding: spacing.xs,
};

const tdStyle = { padding: spacing.xs, color: colors.text };

export default function ActivityTrendTable({ trend }) {
  return (
    <Card title="Maintenance Activity Trend">
      <div style={{ marginBottom: spacing.sm }}>
        <div style={{ color: colors.textMuted, fontSize: 12 }}>Corrective Maintenance Trend</div>
        <Badge variant={DIRECTION_VARIANT[trend.correctiveMaintenanceDirection]}>
          {DIRECTION_LABEL[trend.correctiveMaintenanceDirection]}
        </Badge>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {HEADERS.map((header) => (
                <th key={header} style={thStyle}>
                  {header}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {trend.buckets.map((bucket) => (
              <tr key={bucket.label}>
                <td style={tdStyle}>{bucket.label}</td>
                <td style={tdStyle}>{bucket.pmCount}</td>
                <td style={tdStyle}>{bucket.cmCount}</td>
                <td style={tdStyle}>{bucket.woCount}</td>
                <td style={tdStyle}>
                  <strong>{bucket.total}</strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
