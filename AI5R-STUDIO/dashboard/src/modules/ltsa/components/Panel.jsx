export default function Panel({
    title,
    children,
}) {
    return (
        <div
            style={{
                background: "#111827",
                border: "1px solid #1F2937",
                borderRadius: 16,
                padding: 24,
                boxShadow:
                    "0 8px 20px rgba(0,0,0,.25)",
            }}
        >
            <div
                style={{
                    fontSize: 18,
                    fontWeight: 700,
                    marginBottom: 20,
                    color: "#F9FAFB",
                }}
            >
                {title}
            </div>

            {children}
        </div>
    );
}