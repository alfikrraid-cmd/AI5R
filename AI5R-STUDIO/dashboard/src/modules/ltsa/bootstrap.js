import workspaces from "./workspace";

export default function bootstrapLTSA(workspace) {

    workspaces.forEach(item => {

        workspace.registerWorkspace(item);

        if (item.defaultOpen) {
            workspace.openWorkspace(item.id);
        }

    });

}