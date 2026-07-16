export default function Topbar() {
    return (
        <header
            style={{
                height: 64,
                background: "#0F172A",
                borderBottom: "1px solid #1E293B",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0 24px",
                boxSizing: "border-box",
            }}
        >
            <div
                style={{
                    display: "flex",
                    flexDirection: "column",
                }}
            >
                <div
                    style={{
                        color: "#FFFFFF",
                        fontWeight: 700,
                        fontSize: 18,
                    }}
                >
                    LTSA Engineering
                </div>

                <div
                    style={{
                        color: "#64748B",
                        fontSize: 12,
                        marginTop: 2,
                    }}
                >
                    AI5R Studio / LTSA / Dashboard
                </div>
            </div>

            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 16,
                }}
            >
                <input
                    type="text"
                    placeholder="Search..."
                    style={{
                        width: 280,
                        padding: "9px 14px",
                        background: "#111827",
                        border: "1px solid #263244",
                        borderRadius: 8,
                        color: "#fff",
                        outline: "none",
                    }}
                />

                <div
                    style={{
                        color: "#94A3B8",
                        cursor: "pointer",
                        fontSize: 18,
                    }}
                >
                    🔔
                </div>

                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "6px 12px",
                        background: "#052E16",
                        color: "#22C55E",
                        borderRadius: 999,
                        fontWeight: 600,
                        fontSize: 12,
                    }}
                >
                    ● Runtime Online
                </div>

                <div
                    style={{
                        width: 38,
                        height: 38,
                        borderRadius: "50%",
                        background: "#2563EB",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#fff",
                        fontWeight: 700,
                    }}
                >
                    S
                </div>
            </div>
        </header>
    );
}