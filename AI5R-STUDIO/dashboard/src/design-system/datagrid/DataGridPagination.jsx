export default function DataGridPagination({
    page,
    pageCount,
    totalRows,
    onPageChange,
}) {
    return (
        <div
            style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 16px",
                borderTop: "1px solid #1E293B",
                fontSize: 12,
                color: "#94A3B8",
            }}
        >
            <div>{totalRows} rows</div>

            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                }}
            >
                <button
                    type="button"
                    disabled={page <= 0}
                    onClick={() => onPageChange?.(page - 1)}
                    style={{
                        background: "transparent",
                        border: "1px solid #1E293B",
                        borderRadius: 6,
                        color: page <= 0 ? "#475569" : "#F1F5F9",
                        cursor: page <= 0 ? "default" : "pointer",
                        padding: "4px 10px",
                        fontSize: 12,
                    }}
                >
                    Prev
                </button>

                <span>
                    Page {page + 1} of {pageCount}
                </span>

                <button
                    type="button"
                    disabled={page >= pageCount - 1}
                    onClick={() => onPageChange?.(page + 1)}
                    style={{
                        background: "transparent",
                        border: "1px solid #1E293B",
                        borderRadius: 6,
                        color:
                            page >= pageCount - 1
                                ? "#475569"
                                : "#F1F5F9",
                        cursor:
                            page >= pageCount - 1
                                ? "default"
                                : "pointer",
                        padding: "4px 10px",
                        fontSize: 12,
                    }}
                >
                    Next
                </button>
            </div>
        </div>
    );
}
