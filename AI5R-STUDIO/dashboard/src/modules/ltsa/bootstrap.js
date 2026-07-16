import workspaces from "./workspace";

export default function bootstrapLTSA(workspace) {

    const restoring = workspace.hasSavedState();

    workspaces.forEach(item => {

        workspace.registerWorkspace(item);

        if (!restoring && item.defaultOpen) {
            workspace.openWorkspace(item.id);
        }

    });

}