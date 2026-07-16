import { useContext } from "react";
import WorkspaceContext from "../core/WorkspaceContext";

export default function useWorkspace() {
    return useContext(WorkspaceContext);
}