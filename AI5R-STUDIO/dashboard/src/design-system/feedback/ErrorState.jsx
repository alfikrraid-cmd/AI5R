import { AlertTriangle } from "lucide-react";

export default function ErrorState({
    title = "Something went wrong",
    description,
    action,
    icon,
}) {
    return (
        <div
            style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                padding: 32,
                textAlign: "center",
            }}
        >
            <div style={{ color: "#EF4444", marginBottom: 4 }}>
                {icon ?? <AlertTriangle size={28} />}
            </div>

            <div
                style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: "#F1F5F9",
                }}
            >
                {title}
            </div>

            {description && (
                <div
                    style={{
                        fontSize: 13,
                        color: "#94A3B8",
                        maxWidth: 320,
                    }}
                >
                    {description}
                </div>
            )}

            {action && (
                <div style={{ marginTop: 12 }}>{action}</div>
            )}
        </div>
    );
}
