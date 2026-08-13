import { createContext, useContext } from "react";

export const PlatformContext = createContext({
  currentApplication: null,
  organizationContext: null,
  applications: [],
  organizations: [],
  navigateApplication: () => {},
});

export function usePlatformContext() {
  return useContext(PlatformContext);
}
