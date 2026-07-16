/**
 * ============================================================================
 * AI5R Studio Framework
 * Workspace Engine
 * ----------------------------------------------------------------------------
 * File : WorkspaceRegistry.js
 *
 * Responsibility
 * Store all registered Workspace descriptors.
 *
 * This class DOES NOT:
 * - Manage UI
 * - Manage React
 * - Manage lifecycle
 * ============================================================================
 */

export default class WorkspaceRegistry {
    constructor() {
        this.workspaces = new Map();
    }

    register(descriptor) {
        if (!descriptor?.id) {
            throw new Error("Workspace id is required.");
        }

        if (this.workspaces.has(descriptor.id)) {
            throw new Error(
                `Workspace '${descriptor.id}' is already registered.`
            );
        }

        this.workspaces.set(descriptor.id, descriptor);

        return descriptor;
    }

    unregister(id) {
        this.workspaces.delete(id);
    }

    has(id) {
        return this.workspaces.has(id);
    }

    get(id) {
        return this.workspaces.get(id) ?? null;
    }

    getAll() {
        return Array.from(this.workspaces.values());
    }

    clear() {
        this.workspaces.clear();
    }

    size() {
        return this.workspaces.size;
    }
}