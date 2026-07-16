/**
 * ============================================================================
 * AI5R Studio
 * Factory Registry
 * ----------------------------------------------------------------------------
 * Stores all registered Factory Packs.
 * ============================================================================
 */

export default class FactoryRegistry {
    constructor() {
        this.factories = new Map();
    }

    register(factory) {
        if (!factory?.id) {
            throw new Error("Factory id is required.");
        }

        if (this.factories.has(factory.id)) {
            throw new Error(
                `Factory '${factory.id}' already registered.`
            );
        }

        this.factories.set(factory.id, factory);

        return factory;
    }

    unregister(id) {
        this.factories.delete(id);
    }

    has(id) {
        return this.factories.has(id);
    }

    get(id) {
        return this.factories.get(id) ?? null;
    }

    getAll() {
        return Array.from(this.factories.values());
    }

    clear() {
        this.factories.clear();
    }
}