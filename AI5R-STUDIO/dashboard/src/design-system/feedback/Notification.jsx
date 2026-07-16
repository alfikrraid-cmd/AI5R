import { CheckCircle, AlertTriangle, XCircle, Info, X } from "lucide-react";

const VARIANTS = {
    success: { icon: CheckCircle, color: "#22C55E" },
    warning: { icon: AlertTriangle, color: "#F59E0B" },
    error: { icon: XCircle, color: "#EF4444" },
    info: { icon: Info, color: "#38BDF8" },
};

export default function Notification({
    variant = "info",
    title,
    message,
    icon,
    actions,
    onClose,
}) {
    const config = VARIANTS[variant] ?? VARIANTS.info;
    const Icon = icon ? null : config.icon;

    return (
        <div
            style={{
                display: "flex",
                gap: 12,
                padding: "14px 16px",
                background: "#0F172A",
                border: "1px solid #1E293B",
                borderLeft: `3px solid ${config.color}`,
                borderRadius: 12,
                width: "100%",
                boxSizing: "border-box",
            }}
        >
            <div style={{ flexShrink: 0, paddingTop: 2 }}>
                {icon ?? (Icon && <Icon size={18} color={config.color} />)}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
                {title && (
                    <div
                        style={{
                            fontSize: 14,
                            fontWeight: 700,
                            color: "#F1F5F9",
                            marginBottom: message ? 4 : 0,
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
                            gap: 8,
                            marginTop: 10,
                        }}
                    >
                        {actions}
                    </div>
                )}
            </div>

            {onClose && (
                <button
                    type="button"
                    onClick={onClose}
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        background: "transparent",
                        border: "none",
                        color: "#64748B",
                        cursor: "pointer",
                        padding: 2,
                        flexShrink: 0,
                        height: "fit-content",
                    }}
                >
                    <X size={14} />
                </button>
            )}
        </div>
    );
}
