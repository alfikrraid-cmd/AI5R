import WorkspaceRegistry from "@/design-system/workspace/core/WorkspaceRegistry";
import WorkspaceManager from "@/design-system/workspace/core/WorkspaceManager";

import FactoryRegistry from "./FactoryRegistry";

export default class StudioRuntime {
    constructor() {
        this.factoryRegistry = new FactoryRegistry();

        this.workspaceRegistry = new WorkspaceRegistry();

        this.workspaceManager = new WorkspaceManager(
            this.workspaceRegistry
        );
    }
}