import { ChevronDown, ChevronUp } from "lucide-react";

export default function DataGridHeader({
    columns,
    selectable = false,
    allSelected = false,
    sort,
    onSort,
    onToggleAll,
}) {
    return (
        <thead>
            <tr
                style={{
                    background: "#0F172A",
                    borderBottom: "1px solid #1E293B",
                }}
            >
                {selectable && (
                    <th
                        style={{
                            width: 40,
                            padding: "10px 16px",
                            textAlign: "left",
                        }}
                    >
                        <input
                            type="checkbox"
                            checked={allSelected}
                            onChange={onToggleAll}
                        />
                    </th>
                )}

                {columns.map((column) => {
                    const isSorted = sort?.key === column.key;

                    return (
                        <th
                            key={column.key}
                            onClick={
                                column.sortable
                                    ? () => onSort?.(column.key)
                                    : undefined
                            }
                            style={{
                                padding: "10px 16px",
                                textAlign: column.align ?? "left",
                                fontSize: 11,
                                fontWeight: 700,
                                letterSpacing: 1,
                                textTransform: "uppercase",
                                color: "#94A3B8",
                                cursor: column.sortable
                                    ? "pointer"
                                    : "default",
                                userSelect: "none",
                                whiteSpace: "nowrap",
                            }}
                        >
                            <span
                                style={{
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: 4,
                                }}
                            >
                                {column.title}

                                {column.sortable && isSorted && (
                                    sort.direction === "asc" ? (
                                        <ChevronUp size={12} />
                                    ) : sort.direction === "desc" ? (
                                        <ChevronDown size={12} />
                                    ) : null
                                )}
                            </span>
                        </th>
                    );
                })}
            </tr>
        </thead>
    );
}
