import { ChevronDown, ChevronUp } from "lucide-react";

export default function PanelHeader({
    title,
    collapsible = false,
    collapsed = false,
    onToggle,
}) {
    return (
        <div
            onClick={collapsible ? onToggle : undefined}
            style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "16px 20px",
                borderBottom: collapsed
                    ? "none"
                    : "1px solid #1E293B",
                cursor: collapsible ? "pointer" : "default",
                userSelect: "none",
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

            {collapsible && (
                <button
                    type="button"
                    onClick={(event) => {
                        event.stopPropagation();
                        onToggle?.();
                    }}
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        background: "transparent",
                        border: "none",
                        color: "#64748B",
                        cursor: "pointer",
                        padding: 4,
                    }}
                >
                    {collapsed ? (
                        <ChevronDown size={16} />
                    ) : (
                        <ChevronUp size={16} />
                    )}
                </button>
            )}
        </div>
    );
}
