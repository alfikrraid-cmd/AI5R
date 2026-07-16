/**
 * ============================================================================
 * AI5R Studio Framework
 * Workspace Engine
 * ----------------------------------------------------------------------------
 * File : WorkspaceManager.js
 *
 * Responsibility
 * Manage Workspace lifecycle.
 *
 * This class DOES NOT:
 * - Render UI
 * - Use React
 * - Know Factory Packs
 * ============================================================================
 */

export default class WorkspaceManager {
    constructor(registry) {
        this.registry = registry;

        this.activeWorkspace = null;
        this.openedWorkspaces = [];
    }

    openWorkspace(id) {
        if (!this.registry.has(id)) {
            throw new Error(`Workspace '${id}' is not registered.`);
        }

        if (!this.openedWorkspaces.includes(id)) {
            this.openedWorkspaces.push(id);
        }

        this.activeWorkspace = id;

        return this.registry.get(id);
    }

    closeWorkspace(id) {
        this.openedWorkspaces = this.openedWorkspaces.filter(
            workspaceId => workspaceId !== id
        );

        if (this.activeWorkspace === id) {
            this.activeWorkspace =
                this.openedWorkspaces.length > 0
                    ? this.openedWorkspaces[0]
                    : null;
        }
    }

    activateWorkspace(id) {
        if (!this.openedWorkspaces.includes(id)) {
            throw new Error(`Workspace '${id}' is not opened.`);
        }

        this.activeWorkspace = id;
    }

    isOpen(id) {
        return this.openedWorkspaces.includes(id);
    }

    getActiveWorkspace() {
        if (!this.activeWorkspace) {
            return null;
        }

        return this.registry.get(this.activeWorkspace);
    }

    getOpenedWorkspaces() {
        return this.openedWorkspaces.map(id => this.registry.get(id));
    }

    clear() {
        this.activeWorkspace = null;
        this.openedWorkspaces = [];
    }
}