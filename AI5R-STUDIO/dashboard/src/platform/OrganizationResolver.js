import OrganizationContext from "./OrganizationContext";

function normalizePath(value) {
  if (!value || value === "/") {
    return "/";
  }
  return value.endsWith("/") && value.length > 1 ? value.slice(0, -1) : value;
}

export function resolveOrganization({ pathname, basePath, reservedRouteSegments = [] }) {
  const normalizedPathname = normalizePath(pathname);
  const normalizedBasePath = normalizePath(basePath);

  if (normalizedPathname === normalizedBasePath) {
    return null;
  }

  if (!normalizedPathname.startsWith(`${normalizedBasePath}/`)) {
    return null;
  }

  const remainder = normalizedPathname.slice(normalizedBasePath.length + 1);
  const [slug] = remainder.split("/");

  if (!slug || reservedRouteSegments.includes(slug)) {
    return null;
  }

  return new OrganizationContext({
    organizationId: slug,
    slug,
    displayName: slug.toUpperCase(),
    metadata: {},
  });
}
