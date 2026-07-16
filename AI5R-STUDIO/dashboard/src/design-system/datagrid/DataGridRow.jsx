import DataGridCell from "./DataGridCell";

export default function DataGridRow({
    row,
    columns,
    selectable = false,
    selected = false,
    onToggle,
}) {
    return (
        <tr
            style={{
                background: selected ? "#1E293B" : "transparent",
            }}
        >
            {selectable && (
                <td
                    style={{
                        width: 40,
                        padding: "10px 16px",
                        borderBottom: "1px solid #1E293B",
                    }}
                >
                    <input
                        type="checkbox"
                        checked={selected}
                        onChange={onToggle}
                    />
                </td>
            )}

            {columns.map((column) => (
                <DataGridCell
                    key={column.key}
                    column={column}
                    row={row}
                />
            ))}
        </tr>
    );
}
