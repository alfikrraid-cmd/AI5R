import { useEffect } from "react";

import {
    WorkspaceProvider,
    WorkspaceTabs,
    WorkspaceLayout,
    useWorkspace,
} from "@/design-system/workspace";

import bootstrapLTSA from "../bootstrap";


function LTSAContent() {

    const {
        registerWorkspace,
        openWorkspace,
        restoreWorkspace,
        hasSavedState,
    } = useWorkspace();



    useEffect(() => {

        bootstrapLTSA({
            registerWorkspace,
            openWorkspace,
            hasSavedState,
        });


        restoreWorkspace();


    }, []);



    return (
        <>
            <WorkspaceTabs />

            <WorkspaceLayout />
        </>
    );
}



export default function LTSA() {

    return (
        <WorkspaceProvider>

            <LTSAContent />

        </WorkspaceProvider>
    );

}