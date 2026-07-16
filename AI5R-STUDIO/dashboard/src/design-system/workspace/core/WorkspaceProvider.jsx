import { useState, useRef } from "react";

import WorkspaceContext from "./WorkspaceContext";
import WorkspaceManager from "./WorkspaceManager";
import WorkspaceRegistry from "./WorkspaceRegistry";

import WorkspaceStorage from "../services/WorkspaceStorage";


export default function WorkspaceProvider({ children }) {


    const [, forceUpdate] = useState(0);


    const registryRef = useRef(null);

    const managerRef = useRef(null);



    if (!registryRef.current) {

        registryRef.current =
            new WorkspaceRegistry();

    }



    if (!managerRef.current) {

        const storage =
            new WorkspaceStorage();


        managerRef.current =
            new WorkspaceManager(
                registryRef.current,
                storage
            );

    }



    const registry =
        registryRef.current;


    const manager =
        managerRef.current;




    function registerWorkspace(workspace) {


        if (!registry.has(workspace.id)) {

            registry.register(workspace);

        }


        forceUpdate(
            value => value + 1
        );

    }




    function openWorkspace(id) {


        manager.openWorkspace(id);


        forceUpdate(
            value => value + 1
        );

    }




    function closeWorkspace(id) {


        manager.closeWorkspace(id);


        forceUpdate(
            value => value + 1
        );

    }




    function activateWorkspace(id) {


        manager.activateWorkspace(id);


        forceUpdate(
            value => value + 1
        );

    }





    function restoreWorkspace() {


        manager.restore();


        forceUpdate(
            value => value + 1
        );

    }




    function hasSavedState() {

        return manager.hasSavedState();

    }





    const value = {


        workspaces:
            manager.getOpenedWorkspaces(),



        activeWorkspace:
            manager.getActiveWorkspace(),



        registerWorkspace,

        openWorkspace,

        closeWorkspace,

        activateWorkspace,

        restoreWorkspace,

        hasSavedState,


    };




    return (

        <WorkspaceContext.Provider
            value={value}
        >

            {children}

        </WorkspaceContext.Provider>

    );

}