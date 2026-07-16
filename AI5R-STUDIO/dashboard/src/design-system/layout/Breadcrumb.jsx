export default function Breadcrumb({
    items = ["AI5R Studio", "LTSA", "Dashboard"],
}) {
    return (
        <div
            style={{
                height: 36,
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "0 24px",
                background: "#0F172A",
                borderBottom: "1px solid #1E293B",
                color: "#94A3B8",
                fontSize: 13,
            }}
        >
            {items.map((item, index) => (
                <div
                    key={item}
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                    }}
                >
                    <span>{item}</span>

                    {index !== items.length - 1 && (
                        <span style={{ color: "#475569" }}>/</span>
                    )}
                </div>
            ))}
        </div>
    );
}