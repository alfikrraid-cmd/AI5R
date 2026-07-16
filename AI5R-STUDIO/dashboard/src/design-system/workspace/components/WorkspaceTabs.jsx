import useWorkspace from "../hooks/useWorkspace";

export default function WorkspaceTabs() {
    const {
        getOpenedWorkspaces,
        getActiveWorkspace,
        activateWorkspace,
    } = useWorkspace();

    const workspaces = getOpenedWorkspaces();
    const active = getActiveWorkspace();

    return (
        <div
            style={{
                display: "flex",
                gap: "8px",
                padding: "8px",
                borderBottom: "1px solid #ddd",
            }}
        >
            {workspaces.map((workspace) => (
                <button
                    key={workspace.id}
                    onClick={() => activateWorkspace(workspace.id)}
                    style={{
                        padding: "8px 12px",
                        cursor: "pointer",
                        border:
                            active?.id === workspace.id
                                ? "2px solid #2563eb"
                                : "1px solid #ccc",
                        background:
                            active?.id === workspace.id
                                ? "#eff6ff"
                                : "#ffffff",
                    }}
                >
                    {workspace.title}
                </button>
            ))}
        </div>
    );
}