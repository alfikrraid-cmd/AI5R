import { useMemo, useState } from "react";

import DataGridHeader from "./DataGridHeader";
import DataGridRow from "./DataGridRow";
import DataGridPagination from "./DataGridPagination";

function compareValues(a, b) {
    if (a == null && b == null) return 0;
    if (a == null) return -1;
    if (b == null) return 1;

    if (typeof a === "number" && typeof b === "number") {
        return a - b;
    }

    return String(a).localeCompare(String(b));
}

function sortRows(rows, columns, sort) {
    if (!sort?.key || !sort.direction) {
        return rows;
    }

    const column = columns.find((item) => item.key === sort.key);
    const direction = sort.direction === "asc" ? 1 : -1;

    return [...rows].sort((a, b) => {
        const result = column?.sortFn
            ? column.sortFn(a, b)
            : compareValues(a[sort.key], b[sort.key]);

        return result * direction;
    });
}

function nextSortState(current, key) {
    if (current.key !== key) {
        return { key, direction: "asc" };
    }

    if (current.direction === "asc") {
        return { key, direction: "desc" };
    }

    return { key: null, direction: null };
}

export default function DataGrid({
    columns,
    rows,
    rowKey = "id",
    selectable = false,
    pageSize,
    onSortChange,
    onSelectionChange,
}) {
    const [sort, setSort] = useState({ key: null, direction: null });
    const [selectedIds, setSelectedIds] = useState(() => new Set());
    const [page, setPage] = useState(0);

    const sortedRows = useMemo(
        () => sortRows(rows, columns, sort),
        [rows, columns, sort]
    );

    const pageCount = pageSize
        ? Math.max(1, Math.ceil(sortedRows.length / pageSize))
        : 1;

    const currentPage = Math.min(page, pageCount - 1);

    const pagedRows = pageSize
        ? sortedRows.slice(
              currentPage * pageSize,
              currentPage * pageSize + pageSize
          )
        : sortedRows;

    function handleSort(key) {
        const next = nextSortState(sort, key);
        setSort(next);
        onSortChange?.(next);
    }

    function handleToggleRow(id) {
        const next = new Set(selectedIds);

        if (next.has(id)) {
            next.delete(id);
        } else {
            next.add(id);
        }

        setSelectedIds(next);
        onSelectionChange?.(Array.from(next));
    }

    function handleToggleAll() {
        const pageIds = pagedRows.map((row) => row[rowKey]);
        const allSelected = pageIds.every((id) => selectedIds.has(id));

        const next = new Set(selectedIds);

        if (allSelected) {
            pageIds.forEach((id) => next.delete(id));
        } else {
            pageIds.forEach((id) => next.add(id));
        }

        setSelectedIds(next);
        onSelectionChange?.(Array.from(next));
    }

    function handlePageChange(nextPage) {
        setPage(Math.min(Math.max(nextPage, 0), pageCount - 1));
    }

    const allSelected =
        pagedRows.length > 0 &&
        pagedRows.every((row) => selectedIds.has(row[rowKey]));

    return (
        <div
            style={{
                background: "#0F172A",
                border: "1px solid #1E293B",
                borderRadius: 16,
                overflow: "hidden",
            }}
        >
            <table
                style={{
                    width: "100%",
                    borderCollapse: "collapse",
                }}
            >
                <DataGridHeader
                    columns={columns}
                    selectable={selectable}
                    allSelected={allSelected}
                    sort={sort}
                    onSort={handleSort}
                    onToggleAll={handleToggleAll}
                />

                <tbody>
                    {pagedRows.map((row) => (
                        <DataGridRow
                            key={row[rowKey]}
                            row={row}
                            columns={columns}
                            selectable={selectable}
                            selected={selectedIds.has(row[rowKey])}
                            onToggle={() =>
                                handleToggleRow(row[rowKey])
                            }
                        />
                    ))}
                </tbody>
            </table>

            {pageSize && (
                <DataGridPagination
                    page={currentPage}
                    pageCount={pageCount}
                    totalRows={sortedRows.length}
                    onPageChange={handlePageChange}
                />
            )}
        </div>
    );
}
