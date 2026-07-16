export default function Sidebar() {
    const menu = [
        "Dashboard",
        "LTSA",
        "Auditor OS",
        "UMKM OS",
        "Runtime",
        "AI Workforce",
        "Analytics",
        "Settings",
    ];

    return (
        <aside
            style={{
                width: 260,
                background: "#0E1628",
                borderRight: "1px solid #1E293B",
                padding: 24,
            }}
        >
            <h2
                style={{
                    color: "#00D084",
                    marginBottom: 40,
                }}
            >
                🌳 AI5R Studio
            </h2>

            {menu.map((item) => (
                <div
                    key={item}
                    style={{
                        padding: "12px 16px",
                        marginBottom: 8,
                        borderRadius: 10,
                        cursor: "pointer",
                    }}
                >
                    {item}
                </div>
            ))}
        </aside>
    );
}