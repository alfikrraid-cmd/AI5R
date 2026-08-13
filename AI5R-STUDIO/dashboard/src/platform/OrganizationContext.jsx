export default class OrganizationContext {
  constructor({ organizationId, slug, displayName, metadata = {} }) {
    if (!organizationId) {
      throw new Error("organizationId is required");
    }
    if (!slug) {
      throw new Error("slug is required");
    }
    if (!displayName) {
      throw new Error("displayName is required");
    }

    this.organizationId = organizationId;
    this.slug = slug;
    this.displayName = displayName;
    this.metadata = Object.freeze({ ...metadata });

    Object.freeze(this);
  }
}
