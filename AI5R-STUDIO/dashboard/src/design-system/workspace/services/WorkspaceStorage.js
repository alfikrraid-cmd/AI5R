/**
 * ============================================================================
 * AI5R Studio Framework
 * Workspace Storage
 * ----------------------------------------------------------------------------
 * Responsibility:
 * Persist workspace state.
 *
 * This class DOES NOT:
 * - Manage workspace lifecycle
 * - Know React
 * - Render UI
 * ============================================================================
 */


const STORAGE_KEY = "ai5r.workspace.state";


export default class WorkspaceStorage {


    save(openedWorkspaces, activeWorkspace = null) {

        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({
                openedWorkspaces,
                activeWorkspace
            })
        );

    }



    load() {

        const data =
            localStorage.getItem(STORAGE_KEY);


        if (!data) {

            return { openedWorkspaces: [], activeWorkspace: null };

        }


        try {

            const parsed =
                JSON.parse(data);


            return {
                openedWorkspaces: parsed.openedWorkspaces || [],
                activeWorkspace: parsed.activeWorkspace ?? null
            };


        } catch (error) {

            return { openedWorkspaces: [], activeWorkspace: null };

        }

    }



    hasSavedState() {

        return this.load().openedWorkspaces.length > 0;

    }



    clear() {

        localStorage.removeItem(
            STORAGE_KEY
        );

    }

}
