import { useWorkspace } from "../hooks/useWorkspace";


export default function WorkspaceTabs() {

    const {
        workspaces,
        activeWorkspace,
        activateWorkspace,
        closeWorkspace,
    } = useWorkspace();



    return (

        <div className="workspace-tabs">


            {workspaces.map(workspace => (

                <div
                    key={workspace.id}
                    className={
                        workspace.id === activeWorkspace?.id
                            ? "workspace-tab active"
                            : "workspace-tab"
                    }
                >


                    <button
                        onClick={() =>
                            activateWorkspace(workspace.id)
                        }
                    >
                        {workspace.title}
                    </button>



                    <button
                        className="workspace-close"
                        onClick={(event) => {

                            event.stopPropagation();

                            closeWorkspace(workspace.id);

                        }}
                    >
                        ×
                    </button>


                </div>

            ))}


        </div>

    );
}