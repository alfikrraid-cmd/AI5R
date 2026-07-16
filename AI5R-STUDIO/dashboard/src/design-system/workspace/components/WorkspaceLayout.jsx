import { useWorkspace } from "../hooks/useWorkspace";

export default function WorkspaceLayout() {
    const { activeWorkspace } = useWorkspace();

    if (!activeWorkspace) {
        return (
            <div className="workspace-layout-empty">
                No workspace opened.
            </div>
        );
    }

    const Component = activeWorkspace.component;

    return (
        <div className="workspace-layout">
            <Component />
        </div>
    );
}