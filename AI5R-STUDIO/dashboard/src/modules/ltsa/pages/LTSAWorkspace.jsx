import {
    WorkspaceTabs,
    WorkspaceLayout,
} from "@/design-system/workspace";

export default function LTSAWorkspace() {
    return (
        <div className="flex h-full flex-col">

            <WorkspaceTabs />

            <div className="flex-1 overflow-hidden">
                <WorkspaceLayout />
            </div>

        </div>
    );
}   