import { X } from "lucide-react";

export default function Drawer({ title, children, side = "right", onClose }) {
    return (
        <div
            style={{
                position: "absolute",
                top: 0,
                bottom: 0,
                [side]: 0,
                width: 360,
                maxWidth: "90vw",
                pointerEvents: "auto",
                background: "#0F172A",
                borderLeft: side === "right" ? "1px solid #1E293B" : "none",
                borderRight: side === "left" ? "1px solid #1E293B" : "none",
                boxShadow: "0 20px 60px rgba(0,0,0,.5)",
                display: "flex",
                flexDirection: "column",
            }}
        >
            {(title || onClose) && (
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

                    {onClose && (
                        <button
                            type="button"
                            onClick={onClose}
                            style={{
                                background: "transparent",
                                border: "none",
                                color: "#64748B",
                                cursor: "pointer",
                            }}
                        >
                            <X size={16} />
                        </button>
                    )}
                </div>
            )}

            <div style={{ flex: 1, overflow: "auto", padding: 20, color: "#F1F5F9" }}>
                {children}
            </div>
        </div>
    );
}
