import { CheckCircle, AlertTriangle, XCircle, Info, X } from "lucide-react";

const VARIANTS = {
    success: { icon: CheckCircle, color: "#22C55E" },
    warning: { icon: AlertTriangle, color: "#F59E0B" },
    error: { icon: XCircle, color: "#EF4444" },
    info: { icon: Info, color: "#38BDF8" },
};

export default function Toast({
    variant = "info",
    message,
    icon,
    onClose,
}) {
    const config = VARIANTS[variant] ?? VARIANTS.info;
    const Icon = icon ? null : config.icon;

    return (
        <div
            style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 14px",
                background: "#0F172A",
                border: "1px solid #1E293B",
                borderLeft: `3px solid ${config.color}`,
                borderRadius: 10,
                boxShadow: "0 8px 20px rgba(0,0,0,.25)",
                minWidth: 240,
            }}
        >
            {icon ?? (Icon && <Icon size={18} color={config.color} />)}

            <div
                style={{
                    flex: 1,
                    fontSize: 13,
                    color: "#F1F5F9",
                }}
            >
                {message}
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
                    }}
                >
                    <X size={14} />
                </button>
            )}
        </div>
    );
}
