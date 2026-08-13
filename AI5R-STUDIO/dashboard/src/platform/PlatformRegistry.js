export default class PlatformRegistry {
  constructor() {
    this._applications = new Map();
  }

  register(application) {
    if (!application?.applicationId) {
      throw new Error("applicationId is required");
    }

    this._applications.set(application.applicationId, application);
    return application;
  }

  get(applicationId) {
    return this._applications.get(applicationId) ?? null;
  }

  list() {
    return Array.from(this._applications.values());
  }

  exists(applicationId) {
    return this._applications.has(applicationId);
  }
}
