import { useMemo, useState } from "react";
import { loadPlatformRegistry } from "./ManifestLoader";
import { PlatformContext } from "./PlatformContext";

const platformRegistry = loadPlatformRegistry();
const APPLICATIONS = platformRegistry.list();

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
