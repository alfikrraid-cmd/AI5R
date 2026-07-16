import { useMemo, useState } from "react";

import WorkspaceContext from "./WorkspaceContext";
import WorkspaceRegistry from "./WorkspaceRegistry";
import WorkspaceManager from "./WorkspaceManager";

export default function WorkspaceProvider({ children }) {
    const registry = useMemo(() => new WorkspaceRegistry(), []);

    const manager = useMemo(
        () => new WorkspaceManager(registry),
        [registry]
    );

    const [, forceUpdate] = useState(0);

    const refresh = () => {
        forceUpdate(value => value + 1);
    };

    const value = {
        registry,
        manager,

        registerWorkspace(descriptor) {
            registry.register(descriptor);
            refresh();
        },

        unregisterWorkspace(id) {
            registry.unregister(id);
            refresh();
        },

        openWorkspace(id) {
            manager.openWorkspace(id);
            refresh();
        },

        closeWorkspace(id) {
            manager.closeWorkspace(id);
            refresh();
        },

        activateWorkspace(id) {
            manager.activateWorkspace(id);
            refresh();
        },

        getWorkspace(id) {
            return registry.get(id);
        },

        getWorkspaces() {
            return registry.getAll();
        },

        getOpenedWorkspaces() {
            return manager.getOpenedWorkspaces();
        },

        getActiveWorkspace() {
            return manager.getActiveWorkspace();
        },
    };

    return (
        <WorkspaceContext.Provider value={value}>
            {children}
        </WorkspaceContext.Provider>
    );
}