export default function Toolbar({ children }) {
    return (
        <div
            style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 12px",
                background: "#0F172A",
                border: "1px solid #1E293B",
                borderRadius: 12,
            }}
        >
            {children}
        </div>
    );
}
