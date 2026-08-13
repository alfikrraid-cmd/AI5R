import DashboardLayout from "../layout/DashboardLayout";
import ApplicationRouter from "./ApplicationRouter";
import PlatformProvider from "./PlatformProvider";

export default function PlatformShell() {
  return (
    <PlatformProvider>
      <DashboardLayout>
        <ApplicationRouter />
      </DashboardLayout>
    </PlatformProvider>
  );
}
