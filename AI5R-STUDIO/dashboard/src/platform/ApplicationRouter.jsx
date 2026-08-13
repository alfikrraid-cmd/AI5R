import { useEffect, useMemo, useState } from "react";
import ApplicationAdapter from "./ApplicationAdapter";
import { usePlatformContext } from "./PlatformContext";

function resolveApplication(pathname, applications) {
  if (pathname === "/") {
    return applications.find((application) => application.applicationId === "platform-home");
  }

  const [, slug] = pathname.split("/");
  return applications.find((application) => application.slug === slug) ?? applications[0];
}

export default function ApplicationRouter() {
  const { applications, setCurrentApplication, setOrganizationContext } = usePlatformContext();
  const [pathname, setPathname] = useState(() => window.location.pathname);
  const application = useMemo(() => resolveApplication(pathname, applications), [applications, pathname]);

  useEffect(() => {
    const handlePopState = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    setCurrentApplication(application);
    setOrganizationContext(null);
  }, [application, setCurrentApplication, setOrganizationContext]);

  function handleNavigateApplication(applicationId) {
    const nextApplication = applications.find((item) => item.applicationId === applicationId);
    if (!nextApplication) {
      return;
    }

    window.history.pushState({}, "", nextApplication.defaultPath);
    setPathname(window.location.pathname);
  }

  return (
    <ApplicationAdapter
      application={application}
      applications={applications}
      onNavigateApplication={handleNavigateApplication}
    />
  );
}
