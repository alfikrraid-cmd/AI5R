export default function DataGridCell({ column, row }) {
    const value = column.render ? column.render(row) : row[column.key];

    return (
        <td
            style={{
                padding: "10px 16px",
                textAlign: column.align ?? "left",
                fontSize: 13,
                color: "#F1F5F9",
                borderBottom: "1px solid #1E293B",
            }}
        >
            {value}
        </td>
    );
}
