import { useState } from "react";

import PanelHeader from "./PanelHeader";

export default function Panel({
    title,
    children,
    collapsible = false,
    defaultCollapsed = false,
}) {
    const [collapsed, setCollapsed] = useState(defaultCollapsed);

    return (
        <div
            style={{
                background: "#0F172A",
                border: "1px solid #1E293B",
                borderRadius: 16,
                boxShadow: "0 8px 20px rgba(0,0,0,.25)",
                overflow: "hidden",
            }}
        >
            {title && (
                <PanelHeader
                    title={title}
                    collapsible={collapsible}
                    collapsed={collapsed}
                    onToggle={() => setCollapsed((value) => !value)}
                />
            )}

            {!collapsed && (
                <div style={{ padding: 20 }}>
                    {children}
                </div>
            )}
        </div>
    );
}
