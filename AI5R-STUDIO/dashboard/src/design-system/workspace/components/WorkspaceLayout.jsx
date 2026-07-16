import useWorkspace from "../hooks/useWorkspace";
import WorkspaceTabs from "./WorkspaceTabs";

export default function WorkspaceLayout() {
    const { getActiveWorkspace } = useWorkspace();

    const activeWorkspace = getActiveWorkspace();

    const ActiveComponent = activeWorkspace?.component;

    return (
        <div
            style={{
                display: "flex",
                flexDirection: "column",
                height: "100%",
            }}
        >
            {/* Toolbar Placeholder */}
            <div
                style={{
                    height: 48,
                    borderBottom: "1px solid #ddd",
                    display: "flex",
                    alignItems: "center",
                    padding: "0 16px",
                }}
            >
                Toolbar
            </div>

            {/* Workspace Tabs */}
            <WorkspaceTabs />

            {/* Workspace Content */}
            <div
                style={{
                    flex: 1,
                    overflow: "auto",
                    padding: "16px",
                }}
            >
                {ActiveComponent ? (
                    <ActiveComponent />
                ) : (
                    <div>No Workspace Open</div>
                )}
            </div>

            {/* Status Bar Placeholder */}
            <div
                style={{
                    height: 28,
                    borderTop: "1px solid #ddd",
                    padding: "0 12px",
                    display: "flex",
                    alignItems: "center",
                }}
            >
                Status Bar
            </div>
        </div>
    );
}