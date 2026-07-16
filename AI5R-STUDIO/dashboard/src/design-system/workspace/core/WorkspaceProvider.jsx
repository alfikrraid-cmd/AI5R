import { useState, useRef } from "react";

import WorkspaceContext from "./WorkspaceContext";
import WorkspaceManager from "./WorkspaceManager";
import WorkspaceRegistry from "./WorkspaceRegistry";


export default function WorkspaceProvider({ children }) {

    const [, forceUpdate] = useState(0);


    const registryRef = useRef(null);
    const managerRef = useRef(null);


    if (!registryRef.current) {
        registryRef.current = new WorkspaceRegistry();
    }


    if (!managerRef.current) {
        managerRef.current =
            new WorkspaceManager(
                registryRef.current
            );
    }


    const registry = registryRef.current;
    const manager = managerRef.current;



    function registerWorkspace(workspace) {

        if (!registry.has(workspace.id)) {

            registry.register(workspace);

        }

        forceUpdate(value => value + 1);
    }



    function openWorkspace(id) {

        manager.openWorkspace(id);

        forceUpdate(value => value + 1);
    }



    function closeWorkspace(id) {

        manager.closeWorkspace(id);

        forceUpdate(value => value + 1);
    }



    function activateWorkspace(id) {

        manager.activateWorkspace(id);

        forceUpdate(value => value + 1);
    }



    const value = {

        // HANYA workspace yang sedang terbuka
        // tampil sebagai tab
        workspaces:
            manager.getOpenedWorkspaces(),


        // workspace aktif
        activeWorkspace:
            manager.getActiveWorkspace(),



        registerWorkspace,

        openWorkspace,

        closeWorkspace,

        activateWorkspace,

    };



    return (

        <WorkspaceContext.Provider value={value}>

            {children}

        </WorkspaceContext.Provider>

    );
}