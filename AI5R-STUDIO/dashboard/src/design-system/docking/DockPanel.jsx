export default function DockPanel({
    panels,
    activeId,
    onActivate,
    onClose,
}) {
    if (!panels || panels.length === 0) {
        return null;
    }

    const active =
        panels.find((panel) => panel.id === activeId) ?? panels[0];

    const Component = active.component;

    return (
        <div
            style={{
                display: "flex",
                flexDirection: "column",
                height: "100%",
                minHeight: 0,
                background: "#0F172A",
                border: "1px solid #1E293B",
                overflow: "hidden",
            }}
        >
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    padding: "0 8px",
                    height: 36,
                    flexShrink: 0,
                    background: "#0F172A",
                    borderBottom: "1px solid #1E293B",
                    overflowX: "auto",
                }}
            >
                {panels.map((panel) => {
                    const isActive = panel.id === active.id;

                    return (
                        <div
                            key={panel.id}
                            onClick={() => onActivate?.(panel.id)}
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 8,
                                padding: "6px 12px",
                                borderRadius: 6,
                                fontSize: 13,
                                fontWeight: 500,
                                cursor: "pointer",
                                userSelect: "none",
                                color: isActive ? "#FFFFFF" : "#94A3B8",
                                background: isActive
                                    ? "#2563EB"
                                    : "transparent",
                                whiteSpace: "nowrap",
                            }}
                        >
                            <span>{panel.title}</span>

                            {panel.closable !== false && (
                                <span
                                    onClick={(event) => {
                                        event.stopPropagation();
                                        onClose?.(panel.id);
                                    }}
                                    style={{
                                        color: isActive
                                            ? "#FFFFFF"
                                            : "#64748B",
                                        cursor: "pointer",
                                        lineHeight: 1,
                                    }}
                                >
                                    ×
                                </span>
                            )}
                        </div>
                    );
                })}
            </div>

            <div
                style={{
                    flex: 1,
                    minHeight: 0,
                    overflow: "auto",
                    padding: 16,
                }}
            >
                {Component && <Component />}
            </div>
        </div>
    );
}
