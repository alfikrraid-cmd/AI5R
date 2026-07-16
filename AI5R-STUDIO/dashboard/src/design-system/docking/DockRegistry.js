/**
 * ============================================================================
 * AI5R Studio Framework
 * Docking System
 * ----------------------------------------------------------------------------
 * File : DockRegistry.js
 *
 * Responsibility:
 * Store all registered Dock Panel descriptors.
 *
 * This class DOES NOT:
 * - Render UI
 * - Use React
 * - Manage lifecycle
 * ============================================================================
 */

export const DOCK_AREAS = ["left", "center", "right", "bottom"];

export default class DockRegistry {
    constructor() {
        this.panels = new Map();
    }

    register(descriptor) {
        if (!descriptor?.id) {
            throw new Error("Dock panel id is required.");
        }

        if (!DOCK_AREAS.includes(descriptor.area)) {
            throw new Error(
                `Dock panel '${descriptor.id}' has invalid area '${descriptor.area}'.`
            );
        }

        if (this.panels.has(descriptor.id)) {
            throw new Error(
                `Dock panel '${descriptor.id}' is already registered.`
            );
        }

        this.panels.set(descriptor.id, descriptor);

        return descriptor;
    }

    unregister(id) {
        this.panels.delete(id);
    }

    has(id) {
        return this.panels.has(id);
    }

    get(id) {
        return this.panels.get(id) ?? null;
    }

    getAll() {
        return Array.from(this.panels.values());
    }

    getByArea(area) {
        return this.getAll().filter(
            (panel) => panel.area === area
        );
    }

    clear() {
        this.panels.clear();
    }

    size() {
        return this.panels.size;
    }
}
