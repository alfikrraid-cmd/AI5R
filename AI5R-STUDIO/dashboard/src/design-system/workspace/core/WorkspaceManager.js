/**
 * ============================================================================
 * AI5R Studio Framework
 * Workspace Engine
 * ----------------------------------------------------------------------------
 * File : WorkspaceManager.js
 *
 * Responsibility:
 * Manage Workspace lifecycle.
 *
 * This class DOES NOT:
 * - Render UI
 * - Use React
 * - Know Factory Packs
 * ============================================================================
 */


export default class WorkspaceManager {


    constructor(registry, storage) {

        this.registry = registry;

        this.storage = storage;


        this.activeWorkspace = null;

        this.openedWorkspaces = [];

    }



    openWorkspace(id) {


        if (!this.registry.has(id)) {

            throw new Error(
                `Workspace '${id}' is not registered.`
            );

        }



        if (!this.openedWorkspaces.includes(id)) {

            this.openedWorkspaces.push(id);

        }



        this.activeWorkspace = id;



        this.storage.save(
            this.openedWorkspaces,
            this.activeWorkspace
        );



        return this.registry.get(id);

    }





    closeWorkspace(id) {


        this.openedWorkspaces =
            this.openedWorkspaces.filter(
                workspaceId =>
                    workspaceId !== id
            );



        if (this.activeWorkspace === id) {


            this.activeWorkspace =
                this.openedWorkspaces.length > 0
                    ? this.openedWorkspaces[0]
                    : null;


        }



        this.storage.save(
            this.openedWorkspaces,
            this.activeWorkspace
        );


    }





    activateWorkspace(id) {


        if (
            !this.openedWorkspaces.includes(id)
        ) {


            throw new Error(
                `Workspace '${id}' is not opened.`
            );


        }



        this.activeWorkspace = id;



        this.storage.save(
            this.openedWorkspaces,
            this.activeWorkspace
        );


    }





    restore() {


        const saved =
            this.storage.load();



        saved.openedWorkspaces.forEach(id => {


            if (
                this.registry.has(id)
            ) {


                if (
                    !this.openedWorkspaces.includes(id)
                ) {


                    this.openedWorkspaces.push(id);


                }


            }


        });



        if (
            saved.activeWorkspace &&
            this.openedWorkspaces.includes(saved.activeWorkspace)
        ) {


            this.activeWorkspace =
                saved.activeWorkspace;


        } else if (
            this.openedWorkspaces.length > 0
        ) {


            this.activeWorkspace =
                this.openedWorkspaces[0];


        }


    }




    hasSavedState() {

        return this.storage.hasSavedState();

    }





    isOpen(id) {

        return this.openedWorkspaces.includes(id);

    }





    getActiveWorkspace() {


        if (!this.activeWorkspace) {

            return null;

        }


        return this.registry.get(
            this.activeWorkspace
        );

    }





    getOpenedWorkspaces() {


        return this.openedWorkspaces.map(
            id =>
                this.registry.get(id)
        );


    }





    clear() {


        this.activeWorkspace = null;

        this.openedWorkspaces = [];


        this.storage.clear();


    }


}