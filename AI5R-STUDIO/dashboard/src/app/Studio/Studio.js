import StudioRuntime from "./StudioRuntime";
import StudioBootstrap from "./StudioBootstrap";

export default class Studio {
    constructor() {
        this.runtime = new StudioRuntime();

        this.bootstrap = new StudioBootstrap(
            this.runtime
        );

        this.bootstrap.boot();
    }

    getRuntime() {
        return this.runtime;
    }
}