export default function StatusBadge({
    status = "ONLINE",
}) {
    const online = status === "ONLINE";

    return (
        <div
            style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 12px",
                borderRadius: 999,
                background: online
                    ? "rgba(34,197,94,.15)"
                    : "rgba(239,68,68,.15)",
                color: online
                    ? "#22C55E"
                    : "#EF4444",
                fontWeight: 600,
                fontSize: 13,
            }}
        >
            <div
                style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: online
                        ? "#22C55E"
                        : "#EF4444",
                }}
            />

            {status}
        </div>
    );
}