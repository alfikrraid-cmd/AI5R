export default function RuntimeMetricCard({
    title,
    value,
    color = "#22C55E",
}) {
    return (
        <div
            style={{
                background: "#111827",
                border: "1px solid #1F2937",
                borderRadius: 12,
                padding: 18,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
            }}
        >
            <div>
                <div
                    style={{
                        color: "#94A3B8",
                        fontSize: 13,
                    }}
                >
                    {title}
                </div>

                <div
                    style={{
                        fontSize: 28,
                        fontWeight: 700,
                        marginTop: 8,
                    }}
                >
                    {value}
                </div>
            </div>

            <div
                style={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    background: color,
                }}
            />
        </div>
    );
}