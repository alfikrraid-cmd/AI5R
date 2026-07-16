import { BrowserRouter, Routes, Route } from "react-router-dom";

import MainLayout from "../layouts/MainLayout";

import Dashboard from "../modules/ltsa/pages/Dashboard";
import Pump from "../modules/ltsa/pages/Pump";
import Seal from "../modules/ltsa/pages/Seal";
import Runtime from "../modules/ltsa/pages/Runtime";
import Knowledge from "../modules/ltsa/pages/Knowledge";

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

                    <Route
                        path="/ltsa/pump"
                        element={<Pump />}
                    />

                    <Route
                        path="/ltsa/seal"
                        element={<Seal />}
                    />

                    <Route
                        path="/ltsa/runtime"
                        element={<Runtime />}
                    />

                    <Route
                        path="/ltsa/knowledge"
                        element={<Knowledge />}
                    />

                </Route>

            </Routes>
        </BrowserRouter>
    );
}