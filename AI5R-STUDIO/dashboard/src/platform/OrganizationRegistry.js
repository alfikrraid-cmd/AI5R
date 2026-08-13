export default class OrganizationRegistry {
  constructor() {
    this._organizations = new Map();
  }

  register(organization) {
    if (!organization?.organizationId) {
      throw new Error("organizationId is required");
    }

    this._organizations.set(organization.organizationId, organization);
    return organization;
  }

  get(organizationId) {
    return this._organizations.get(organizationId) ?? null;
  }

  list() {
    return Array.from(this._organizations.values());
  }

  exists(organizationId) {
    return this._organizations.has(organizationId);
  }
}
