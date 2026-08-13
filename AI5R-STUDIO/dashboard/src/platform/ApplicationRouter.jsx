import { useEffect, useMemo, useState } from "react";
import ApplicationAdapter from "./ApplicationAdapter";
import { resolveOrganization } from "./OrganizationResolver";
import { usePlatformContext } from "./PlatformContext";

function resolveApplication(pathname, applications) {
  if (pathname === "/") {
    return applications.find((application) => application.applicationId === "platform-home");
  }

  const [, slug] = pathname.split("/");
  return applications.find((application) => application.slug === slug) ?? applications[0];
}

export default function ApplicationRouter() {
  const platformContext = usePlatformContext();
  const { applications, setCurrentApplication, setOrganizationContext } = platformContext;
  const [pathname, setPathname] = useState(() => window.location.pathname);
  const application = useMemo(() => resolveApplication(pathname, applications), [applications, pathname]);
  const organizationContext = useMemo(
    () =>
      application?.organizationAware
        ? resolveOrganization({
            pathname,
            basePath: application.basePath,
            reservedRouteSegments: application.reservedRouteSegments,
          })
        : null,
    [application, pathname]
  );

  useEffect(() => {
    const handlePopState = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    setCurrentApplication(application);
    setOrganizationContext(organizationContext);
  }, [application, organizationContext, setCurrentApplication, setOrganizationContext]);

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
      organizationContext={organizationContext}
      platformContext={platformContext}
    />
  );
}
