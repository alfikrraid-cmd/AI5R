import { Outlet } from "react-router-dom";

import Sidebar from "../design-system/layout/Sidebar";
import Topbar from "../design-system/layout/Topbar";
import Breadcrumb from "../design-system/layout/Breadcrumb";
import StatusBar from "../design-system/layout/StatusBar";


export default function MainLayout() {
    return (
        <div
            style={{
                display: "flex",
                height: "100vh",
                background: "#070B18",
                overflow: "hidden",
            }}
        >

            <Sidebar />

            <div
                style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    minWidth: 0,
                }}
            >

                <Topbar />

                <Breadcrumb />

                <main
                    style={{
                        flex: 1,
                        overflow: "auto",
                    }}
                >
                    <Outlet />
                </main>


                <StatusBar />

            </div>

        </div>
    );
}