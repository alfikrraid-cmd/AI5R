import { useContext } from "react";

import WorkspaceContext from "../core/WorkspaceContext";

export function useWorkspace() {
    return useContext(WorkspaceContext);
}