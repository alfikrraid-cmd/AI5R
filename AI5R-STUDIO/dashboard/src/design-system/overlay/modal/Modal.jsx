import { X } from "lucide-react";

export default function Modal({ title, children, onClose }) {
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
                    width: 480,
                    maxWidth: "90vw",
                    maxHeight: "85vh",
                    overflow: "auto",
                    background: "#0F172A",
                    border: "1px solid #1E293B",
                    borderRadius: 16,
                    boxShadow: "0 20px 60px rgba(0,0,0,.5)",
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
                                    display: "flex",
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

                <div style={{ padding: 20, color: "#F1F5F9" }}>
                    {children}
                </div>
            </div>
        </div>
    );
}
