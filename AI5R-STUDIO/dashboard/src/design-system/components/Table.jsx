import colors from "../theme/colors";
import spacing from "../theme/spacing";

export default function Table({ rows, columns, data, rowKey, onRowClick, selectedKey }) {
  if (columns) {
    return (
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                style={{
                  textAlign: "left",
                  color: colors.textMuted,
                  borderBottom: `1px solid ${colors.border}`,
                  padding: spacing.xs,
                }}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {(data ?? []).map((item) => {
            const key = item[rowKey];
            const isSelected = key === selectedKey;

            return (
              <tr
                key={key}
                aria-selected={onRowClick ? isSelected : undefined}
                onClick={onRowClick ? () => onRowClick(item) : undefined}
                style={{
                  cursor: onRowClick ? "pointer" : "default",
                  background: isSelected ? colors.background : "transparent",
                }}
              >
                {columns.map((column) => (
                  <td key={column.key} style={{ padding: spacing.xs, color: colors.text }}>
                    {item[column.key]}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }

  return (
    <table>
      <tbody>
        {(rows ?? []).map((row, index) => (
          <tr key={row.label ?? index}>
            <td>{row.label}</td>
            <td>{row.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
