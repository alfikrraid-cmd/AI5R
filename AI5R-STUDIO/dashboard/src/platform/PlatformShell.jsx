import ApplicationRouter from "./ApplicationRouter";
import PlatformProvider from "./PlatformProvider";

// MWO-LTSA-STANDALONE-PRODUCT-SHELL-001 -- Studio's own DashboardLayout
// chrome is no longer applied unconditionally here; ApplicationRouter
// (which already resolves the current application from the route) decides
// per-application whether Studio chrome wraps it, so a standalone product
// like LTSA is never nested inside Studio's shell.
export default function PlatformShell() {
  return (
    <PlatformProvider>
      <ApplicationRouter />
    </PlatformProvider>
  );
}
