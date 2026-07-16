import { Outlet } from "react-router-dom";

import Sidebar from "../design-system/layout/Sidebar";
import Topbar from "../design-system/layout/Topbar";
import Breadcrumb from "../design-system/layout/Breadcrumb";
import WorkspaceTabs from "../design-system/layout/WorkspaceTabs";
import Workspace from "../design-system/layout/Workspace";
import StatusBar from "../design-system/layout/StatusBar";

export default function MainLayout() {
    return (
        <div
            style={{
                display: "flex",
                height: "100vh",
                background: "#070B18",
            }}
        >
            <Sidebar />

            <div
                style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                }}
            >
                <Topbar />

                <Breadcrumb />

                <WorkspaceTabs />

                <Workspace>
                    <Outlet />
                </Workspace>

                <StatusBar />
            </div>
        </div>
    );
}