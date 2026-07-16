import StudioFactoryLoader from "./StudioFactoryLoader";

export default class StudioBootstrap {
    constructor(runtime) {
        this.runtime = runtime;
    }

    boot() {
        const loader = new StudioFactoryLoader();

        loader.load(this.runtime);
    }
}