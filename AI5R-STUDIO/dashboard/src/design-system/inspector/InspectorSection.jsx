import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

export default function InspectorSection({
    title,
    children,
    collapsible = false,
    defaultCollapsed = false,
}) {
    const [collapsed, setCollapsed] = useState(defaultCollapsed);

    return (
        <div style={{ marginBottom: 12 }}>
            {title && (
                <div
                    onClick={
                        collapsible
                            ? () => setCollapsed((value) => !value)
                            : undefined
                    }
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "8px 20px",
                        fontSize: 11,
                        fontWeight: 700,
                        letterSpacing: 1,
                        textTransform: "uppercase",
                        color: "#64748B",
                        cursor: collapsible ? "pointer" : "default",
                        userSelect: "none",
                    }}
                >
                    <span>{title}</span>

                    {collapsible &&
                        (collapsed ? (
                            <ChevronDown size={14} />
                        ) : (
                            <ChevronUp size={14} />
                        ))}
                </div>
            )}

            {!collapsed && <div>{children}</div>}
        </div>
    );
}
