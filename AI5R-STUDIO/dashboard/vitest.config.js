import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    // Root cause of "React.act is not a function": this shell's NODE_ENV
    // is set to "production" (inherited from the outer environment), so
    // React/ReactDOM resolve their production builds when required inside
    // the Vitest process -- and React 19's production build strips the
    // `act` export that react-dom/test-utils' deprecated act() shim
    // depends on. Forcing NODE_ENV=test here, for the test run only,
    // makes React/ReactDOM resolve their development builds (which do
    // export `act`) without touching any application code or npm scripts.
    env: { NODE_ENV: "test" },
  },
});
