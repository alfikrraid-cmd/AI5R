import { Outlet } from "react-router-dom";

export default function MainLayout() {
    return (
        <div
            style={{
                minHeight: "100vh",
                background: "#0B1020",
                color: "white",
                padding: "40px",
            }}
        >
            <h2>AI5R Studio</h2>

            <hr />

            <Outlet />
        </div>
    );
}