import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "../pages/Home";
import Dashboard from "../modules/ltsa/pages/Dashboard";
import MainLayout from "../layouts/MainLayout";

export default function Router() {
    return (
        <BrowserRouter>
            <Routes>

                <Route path="/" element={<Home />} />

                <Route element={<MainLayout />}>

                    <Route
                        path="/ltsa"
                        element={<Dashboard />}
                    />

                </Route>

            </Routes>
        </BrowserRouter>
    );
}