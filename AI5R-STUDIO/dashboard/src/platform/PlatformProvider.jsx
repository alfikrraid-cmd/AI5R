import { useMemo, useState } from "react";
import { PlatformContext } from "./PlatformContext";

const APPLICATIONS = [
  {
    applicationId: "platform-home",
    slug: "",
    basePath: "/",
    displayName: "AI5ROS",
    defaultPath: "/",
    status: "active",
  },
  {
    applicationId: "ltsa",
    slug: "ltsa",
    basePath: "/ltsa",
    displayName: "LTSA",
    defaultPath: "/ltsa/pump-workspace",
    status: "active",
  },
  {
    applicationId: "od",
    slug: "od",
    basePath: "/od",
    displayName: "Open Design",
    defaultPath: "/od",
    status: "active",
  },
];

export default function PlatformProvider({ children }) {
  const [currentApplication, setCurrentApplication] = useState(null);
  const [organizationContext, setOrganizationContext] = useState(null);

  const value = useMemo(
    () => ({
      currentApplication,
      organizationContext,
      applications: APPLICATIONS,
      organizations: [],
      setCurrentApplication,
      setOrganizationContext,
      navigateApplication: () => {},
    }),
    [currentApplication, organizationContext]
  );

  return <PlatformContext.Provider value={value}>{children}</PlatformContext.Provider>;
}

