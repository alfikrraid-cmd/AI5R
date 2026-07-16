import { Loader2 } from "lucide-react";

export default function LoadingState({
    message = "Loading...",
    size = 24,
}) {
    return (
        <div
            style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 12,
                padding: 32,
            }}
        >
            <style>
                {`@keyframes ai5r-feedback-spin { to { transform: rotate(360deg); } }`}
            </style>

            <Loader2
                size={size}
                color="#94A3B8"
                style={{
                    animation: "ai5r-feedback-spin 1s linear infinite",
                }}
            />

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
        </div>
    );
}
