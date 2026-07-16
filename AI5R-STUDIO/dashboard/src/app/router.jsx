import { BrowserRouter, Routes, Route } from "react-router-dom";

import Dashboard from "../modules/ltsa/pages/Dashboard";
import MainLayout from "../layouts/MainLayout";

export default function Router() {
    return (
        <BrowserRouter>
            <Routes>

                <Route element={<MainLayout />}>

                    <Route
                        path="/"
                        element={<Dashboard />}
                    />

                    <Route
                        path="/ltsa"
                        element={<Dashboard />}
                    />

                </Route>

            </Routes>
        </BrowserRouter>
    );
}