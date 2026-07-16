import { useWorkspace } from "@/design-system/workspace";

import PumpPage from "./pages/PumpPage";
// nanti ditambah:
// import OverviewPage from "./pages/OverviewPage";
// import SealPage from "./pages/SealPage";

export function registerLTSAWorkspaces() {
    const {
        registerWorkspace,
        openWorkspace,
    } = useWorkspace();

    registerWorkspace({
        id: "pump",
        title: "Pump Registry",
        component: PumpPage,
        order: 1,
        closable: false,
        defaultOpen: true,
    });

    openWorkspace("pump");
}