/**
 * ============================================================================
 * AI5R Studio Framework
 * Docking System
 * ----------------------------------------------------------------------------
 * File : DockManager.js
 *
 * Responsibility:
 * Manage which Dock Panels are open/active per dock area.
 *
 * A panel's area is fixed at registration (no drag-drop in v1) — this class
 * only tracks, per area, which registered panels are open and which one is
 * active, like an independent tab strip per area.
 *
 * This class DOES NOT:
 * - Render UI
 * - Use React
 * - Know Factory Packs
 * - Persist state
 * ============================================================================
 */

import { DOCK_AREAS } from "./DockRegistry";

export default class DockManager {
    constructor(registry) {
        this.registry = registry;

        this.openPanels = Object.fromEntries(
            DOCK_AREAS.map((area) => [area, []])
        );

        this.activePanel = Object.fromEntries(
            DOCK_AREAS.map((area) => [area, null])
        );
    }

    _areaOf(id) {
        const descriptor = this.registry.get(id);

        if (descriptor) {
            return descriptor.area;
        }

        return (
            DOCK_AREAS.find((area) =>
                this.openPanels[area].includes(id)
            ) ?? null
        );
    }

    openPanel(id) {
        if (!this.registry.has(id)) {
            throw new Error(
                `Dock panel '${id}' is not registered.`
            );
        }

        const area = this.registry.get(id).area;

        if (!this.openPanels[area].includes(id)) {
            this.openPanels[area].push(id);
        }

        this.activePanel[area] = id;
    }

    closePanel(id) {
        const area = this._areaOf(id);

        if (!area) {
            return;
        }

        this.openPanels[area] = this.openPanels[area].filter(
            (panelId) => panelId !== id
        );

        if (this.activePanel[area] === id) {
            this.activePanel[area] =
                this.openPanels[area][0] ?? null;
        }
    }

    activatePanel(id) {
        const area = this._areaOf(id);

        if (!area || !this.openPanels[area].includes(id)) {
            throw new Error(
                `Dock panel '${id}' is not opened.`
            );
        }

        this.activePanel[area] = id;
    }

    isOpen(id) {
        return DOCK_AREAS.some((area) =>
            this.openPanels[area].includes(id)
        );
    }

    getOpenPanels(area) {
        return this.openPanels[area]
            .map((id) => this.registry.get(id))
            .filter(Boolean);
    }

    getActivePanel(area) {
        const id = this.activePanel[area];

        return id ? this.registry.get(id) : null;
    }

    clear() {
        DOCK_AREAS.forEach((area) => {
            this.openPanels[area] = [];
            this.activePanel[area] = null;
        });
    }
}
