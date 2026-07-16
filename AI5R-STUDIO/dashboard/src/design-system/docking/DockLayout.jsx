import { useEffect, useRef, useState } from "react";

import DockRegistry from "./DockRegistry";
import DockManager from "./DockManager";
import DockPanel from "./DockPanel";

export default function DockLayout({ panels = [] }) {
    const [, forceUpdate] = useState(0);

    const registryRef = useRef(null);
    const managerRef = useRef(null);

    if (!registryRef.current) {
        registryRef.current = new DockRegistry();
    }

    if (!managerRef.current) {
        managerRef.current = new DockManager(registryRef.current);
    }

    const registry = registryRef.current;
    const manager = managerRef.current;

    useEffect(() => {
        panels.forEach((descriptor) => {
            if (!registry.has(descriptor.id)) {
                registry.register(descriptor);

                if (descriptor.defaultOpen) {
                    manager.openPanel(descriptor.id);
                }
            }
        });

        forceUpdate((value) => value + 1);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    function handleActivate(id) {
        manager.activatePanel(id);
        forceUpdate((value) => value + 1);
    }

    function handleClose(id) {
        manager.closePanel(id);
        forceUpdate((value) => value + 1);
    }

    const left = manager.getOpenPanels("left");
    const center = manager.getOpenPanels("center");
    const right = manager.getOpenPanels("right");
    const bottom = manager.getOpenPanels("bottom");

    return (
        <div
            style={{
                display: "flex",
                flexDirection: "column",
                height: "100%",
                minHeight: 0,
            }}
        >
            <div
                style={{
                    display: "flex",
                    flex: 1,
                    minHeight: 0,
                }}
            >
                {left.length > 0 && (
                    <div style={{ width: 260, flexShrink: 0 }}>
                        <DockPanel
                            panels={left}
                            activeId={manager.getActivePanel("left")?.id}
                            onActivate={handleActivate}
                            onClose={handleClose}
                        />
                    </div>
                )}

                <div style={{ flex: 1, minWidth: 0 }}>
                    <DockPanel
                        panels={center}
                        activeId={manager.getActivePanel("center")?.id}
                        onActivate={handleActivate}
                        onClose={handleClose}
                    />
                </div>

                {right.length > 0 && (
                    <div style={{ width: 260, flexShrink: 0 }}>
                        <DockPanel
                            panels={right}
                            activeId={manager.getActivePanel("right")?.id}
                            onActivate={handleActivate}
                            onClose={handleClose}
                        />
                    </div>
                )}
            </div>

            {bottom.length > 0 && (
                <div style={{ height: 220, flexShrink: 0 }}>
                    <DockPanel
                        panels={bottom}
                        activeId={manager.getActivePanel("bottom")?.id}
                        onActivate={handleActivate}
                        onClose={handleClose}
                    />
                </div>
            )}
        </div>
    );
}
