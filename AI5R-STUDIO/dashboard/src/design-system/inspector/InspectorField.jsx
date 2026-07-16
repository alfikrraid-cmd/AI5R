export default function InspectorField({ label, value, children }) {
    return (
        <div
            style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                padding: "6px 20px",
            }}
        >
            <div
                style={{
                    fontSize: 13,
                    color: "#94A3B8",
                }}
            >
                {label}
            </div>

            <div
                style={{
                    fontSize: 13,
                    color: "#F1F5F9",
                    textAlign: "right",
                }}
            >
                {children ?? value}
            </div>
        </div>
    );
}
