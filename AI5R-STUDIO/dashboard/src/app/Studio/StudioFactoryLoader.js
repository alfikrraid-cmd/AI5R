import ltsa from "@/modules/ltsa/workspace";

export default class StudioFactoryLoader {
    load(runtime) {
        ltsa.forEach(workspace => {
            runtime.workspaceRegistry.register(workspace);
        });
    }
}