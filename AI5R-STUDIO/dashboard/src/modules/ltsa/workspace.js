import Dashboard from "./pages/Dashboard";
import Pump from "./pages/Pump";
import Seal from "./pages/Seal";
import Runtime from "./pages/Runtime";
import Knowledge from "./pages/Knowledge";


const workspaces = [

    {
        id: "dashboard",
        title: "Dashboard",
        component: Dashboard,
        defaultOpen: true,
    },

    {
        id: "pump",
        title: "Pump",
        component: Pump,
        defaultOpen: true,
    },

    {
        id: "seal",
        title: "Seal",
        component: Seal,
        defaultOpen: true,
    },

    {
        id: "runtime",
        title: "Runtime",
        component: Runtime,
        defaultOpen: true,
    },

    {
        id: "knowledge",
        title: "Knowledge",
        component: Knowledge,
        defaultOpen: true,
    },

];


export default workspaces;