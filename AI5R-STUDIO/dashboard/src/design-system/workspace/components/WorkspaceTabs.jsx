import { useWorkspace } from "../hooks/useWorkspace";

export default function WorkspaceTabs() {

    const {
        workspaces,
        activeWorkspace,
        activateWorkspace,
    } = useWorkspace();


    return (
        <div className="workspace-tabs">

            {workspaces.map(workspace => (

                <button
                    key={workspace.id}
                    onClick={() => activateWorkspace(workspace.id)}
                    className={
                        workspace.id === activeWorkspace?.id
                            ? "active"
                            : ""
                    }
                >
                    {workspace.title}
                </button>

            ))}

        </div>
    );
}