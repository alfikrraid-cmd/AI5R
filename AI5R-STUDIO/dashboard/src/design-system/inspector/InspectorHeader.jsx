export default function InspectorHeader({ title, actions }) {
    return (
        <div
            style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "16px 20px",
                borderBottom: "1px solid #1E293B",
            }}
        >
            <div
                style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: "#F1F5F9",
                }}
            >
                {title}
            </div>

            {actions && (
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                    }}
                >
                    {actions}
                </div>
            )}
        </div>
    );
}
