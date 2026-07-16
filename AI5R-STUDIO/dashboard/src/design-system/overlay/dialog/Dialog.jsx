export default function Dialog({ title, message, actions }) {
    return (
        <div
            style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
            }}
        >
            <div
                style={{
                    pointerEvents: "auto",
                    width: 360,
                    maxWidth: "90vw",
                    background: "#0F172A",
                    border: "1px solid #1E293B",
                    borderRadius: 16,
                    boxShadow: "0 20px 60px rgba(0,0,0,.5)",
                    padding: 24,
                    textAlign: "center",
                }}
            >
                {title && (
                    <div
                        style={{
                            fontSize: 16,
                            fontWeight: 700,
                            color: "#F1F5F9",
                            marginBottom: 8,
                        }}
                    >
                        {title}
                    </div>
                )}

                {message && (
                    <div
                        style={{
                            fontSize: 13,
                            color: "#94A3B8",
                            marginBottom: 20,
                        }}
                    >
                        {message}
                    </div>
                )}

                {actions && (
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 8,
                        }}
                    >
                        {actions}
                    </div>
                )}
            </div>
        </div>
    );
}
