# ADR-PLATFORM-001 - AI5ROS Platform Architecture Constitution

## Status

PROPOSED / ARCHITECTURE FREEZE CANDIDATE

## Context

AI5ROS is the Enterprise Platform. Products are independently deployable applications. LTSA is Product #1. Future products include Auditor, Manufacturing, Marketing, UMKM, and School.

Repository archaeology confirms reusable architecture already exists:

- Product Manifest: `AI5R-SDK/PRODUCT/product_manifest.py`, `PRODUCTS/LTSA-BRAIN/product.manifest.json`
- Product Registry: `AI5R-SDK/PRODUCT_REGISTRY/product_registry.py`
- Runtime Registry: `AI5R-SDK/ARCHITECTURE/runtime_registry.py`
- Factory / Factory Packs: `AI5R-SDK/PRODUCT_FACTORY`, `AI5R-SDK/FACTORY/PACKS`
- Product Assembly: `AI5R-SDK/PRODUCT_ASSEMBLY/product_assembly.py`
- Product Artifact: `AI5R-SDK/PRODUCT_ARTIFACT/product_artifact.py`
- Product Runtime: `AI5R-SDK/PRODUCT_RUNTIME/product_runtime.py`
- Runtime Manifests: `CORE-SERVICES/RUNTIME/package_manifest.json`, `runtime_schema.json`, `contract.json`
- Workspace Registry: `AI5R-STUDIO/dashboard/src/modules/ltsa/workspace/WorkspaceRegistry.js`
- Organization Registry: `CORE-SERVICES/API/organization_registry.py`

Current frontend `App.jsx` directly imports product implementations. This ADR freezes the target architecture that separates Platform from Product while reusing existing manifest, registry, runtime, factory, and workspace concepts.

## Decision

### 1. Platform Vision

AI5ROS is the Enterprise Platform for hosting independently deployable AI5R applications.

Canonical public URLs:

```text
/                  AI5ROS Landing
/ltsa              LTSA Application
/ltsa/{org}        LTSA Application scoped by Platform Organization Context
/auditor           Future Application
/manufacturing     Future Application
/marketing         Future Application
/umkm              Future Application
/school            Future Application
```

### 2. Platform Scope

The Platform is a thin shell. It owns application discovery, routing, organization context, and landing composition.

The Platform does not own product business logic, product workspace logic, product API logic, product databases, product runtime internals, or product navigation internals.

### 3. Platform Responsibilities

Platform owns:

- Landing
- Platform Shell
- Platform Context
- Manifest Loader
- Platform Registry
- Organization Resolver
- Organization Registry
- Application Router
- Application Adapter contract

### 4. Product Responsibilities

Products own:

- Application implementation
- Workspace
- Workspace Registry
- Product navigation
- Business logic
- API
- Database
- Runtime
- Domain objects
- Product-specific manifests and artifacts

### 5. Workspace Responsibilities

Workspace is Product-owned.

A Workspace owns:

- Internal tabs
- Internal workspace keys
- Internal navigation context
- Product UI flows
- Product-specific deep links below its application boundary

Platform must not own workspace state.

### 6. Organization Responsibilities

Organization is Platform-owned.

Organization Context originates from Platform and is injected into Product Applications. Products may consume Organization Context, but must not derive tenant or organization identity from browser URL parsing.

### 7. Platform Manifest

The Platform Manifest is the canonical loadable description of Platform applications and organizations.

It references released product/application manifests. It does not duplicate product internals.

Minimum fields:

```text
platform_id
version
applications[]
organizations[]
runtime_refs[]
```

### 8. Application Descriptor

An Application Descriptor is the generic Platform-facing description of a Product Application.

Minimum fields:

```text
application_id
product_id
slug
base_path
display_name
status
version
manifest_ref
organization_aware
reserved_route_segments
entry_contract
runtime_ref
```

Platform understands Application Descriptors only. It does not understand LTSA implementation details.

### 9. Manifest Loader

Manifest Loader is read-only.

It loads released manifests and registers descriptors into Platform Registry. It must not manufacture, mutate, deploy, start runtime, or write product state.

### 10. Platform Registry

Platform Registry stores generic Application Descriptors.

It follows the existing repository registry pattern:

```text
register()
get()
list_all()
```

It may reuse the registry style already present in ProductRegistry, RuntimeRegistry, and ArtifactRegistry.

### 11. Organization Registry

Organization Registry stores Platform Organization records.

Minimum fields:

```text
organization_id
slug
display_name
status
allowed_applications
metadata
```

It should follow the read-only aggregation discipline already present in `CORE-SERVICES/API/organization_registry.py`.

### 12. Application Router

Application Router resolves browser URLs to generic applications.

It owns only top-level routing:

```text
/                  -> Landing
/{application}     -> Application
/{application}/{x} -> Application + optional OrganizationContext
```

It must not parse product workspace routes beyond reserved-route collision checks.

### 13. Platform Context

Platform Context contains:

```text
currentApplication
organizationContext
applications
organizations
navigateApplication()
```

It must not contain product workspace state.

### 14. Application Adapter

Application Adapter bridges generic Platform descriptors to Product Application entries.

The Adapter is the only acceptable boundary where an implementation component is attached to an Application Descriptor.

Platform routes to adapter contracts, not product internals.

### 15. Workspace Registry

Workspace Registry remains Product-owned.

For LTSA, the existing `WorkspaceRegistry.js` remains the owner of LTSA workspace paths such as:

```text
/ltsa/pump-workspace
/ltsa/pump/{assetTag}
/ltsa/pump/{assetTag}/knowledge
/ltsa/pump/{assetTag}/monitoring
```

### 16. Routing Rules

Routing rules:

```text
/                       Platform Landing
/{app}                  Application
/{app}/{organization}   Application with OrganizationContext
/{app}/{reserved}/...   Product workspace route
```

For LTSA, reserved segments include:

```text
pump
pump-workspace
pump-workspace-legacy
pm-workspace
```

Thus:

```text
/ltsa/tap          -> LTSA + organization tap
/ltsa/pump/641-P-5 -> LTSA workspace route, no platform org parsing
```

### 17. Manifest Lifecycle

Canonical manifest lifecycle:

```text
DRAFT
VALIDATED
RELEASED
REGISTERED
ACTIVE
RETIRED
```

Only RELEASED or ACTIVE manifests may be loaded by the production Platform Manifest Loader.

### 18. Product Lifecycle

Canonical product lifecycle reuses existing repository concepts:

```text
Specification
Factory
Artifact
Registry
Runtime
Operation
Evolution
Release
```

Factory manufactures Products. Platform loads released Products.

### 19. Organization Lifecycle

Canonical organization lifecycle:

```text
DEFINED
REGISTERED
ACTIVE
SUSPENDED
RETIRED
```

Organization registration is Platform-owned and independent of Product workspace routing.

### 20. Dependency Rules

Allowed:

```text
Platform -> Application Descriptor
Platform -> Platform Manifest
Platform -> Organization Registry
Platform -> Application Adapter
Product -> Workspace Registry
Product -> Product API
Product -> Product Runtime
Factory -> Product Manifest / Artifact
```

### 21. Forbidden Dependencies

Forbidden:

```text
Platform -> LTSAWorkspace direct dependency
Platform -> LTSA business logic
Platform -> LTSA WorkspaceRegistry internals
Product -> Platform Router
Product -> Platform URL tenant parser
Workspace -> Platform Registry
Manifest Loader -> Factory manufacturing
Manifest Loader -> Runtime mutation
```

### 22. Extension Rules

New products integrate by manifest registration, not by editing Platform routing logic.

A new product must provide:

```text
Product Manifest
Application Descriptor
Application Adapter
Workspace Registry
Runtime reference
Release status
```

### 23. Registration Rules

Application registration requires:

```text
released product manifest
valid application descriptor
unique slug
unique base_path
declared reserved_route_segments
declared organization awareness
valid runtime reference
```

Organization registration requires:

```text
unique slug
status
allowed applications
display metadata
```

### 24. Ownership Matrix

| Area | Owner |
|---|---|
| Landing | Platform |
| Platform Shell | Platform |
| Application Router | Platform |
| Manifest Loader | Platform |
| Platform Registry | Platform |
| Organization Resolver | Platform |
| Organization Registry | Platform |
| Application Descriptor | Platform/Product boundary |
| Application Adapter | Boundary |
| Product Manifest | Product |
| Product Runtime | Product |
| Product API | Product |
| Product Database | Product |
| Product Workspace | Product |
| Workspace Registry | Product |
| Business Logic | Product |
| Factory Packs | Factory/Product manufacturing |
| Deployment Runtime | Runtime |

### 25. Deployment Boundary

Deployment is not redesigned by this ADR.

The Platform Shell and Products may be served by the existing dashboard SPA deployment. Runtime gateway, compose, nginx, n8n, database, and release pipeline remain outside this ADR's implementation scope.

### 26. Runtime Boundary

Runtime owns infrastructure execution and service health.

Platform Manifest loading is browser/application-shell behavior and must not replace runtime manifests such as:

```text
CORE-SERVICES/RUNTIME/package_manifest.json
CORE-SERVICES/RUNTIME/contract.json
CORE-SERVICES/RUNTIME/runtime_schema.json
```

### 27. Factory Boundary

Factory manufactures Product artifacts.

Platform does not invoke Factory during routing. Platform loads released manifests produced after manufacturing/release.

### 28. Future Product Integration

Future products follow the same pattern:

```text
Product implementation
Product Manifest
Application Descriptor
Application Adapter
Platform Manifest registration
Organization eligibility
Workspace Registry
Runtime reference
```

No future product may require Platform to know its workspace internals.

### 29. Architecture Principles

Mandatory principles:

- Platform knows Applications.
- Platform never knows Product implementation.
- Products know Workspaces.
- Products never know Platform routing.
- Factory manufactures Products.
- Platform loads released Products.
- Manifest Loader is read-only.
- Organization is Platform-owned.
- Workspace is Product-owned.
- Business Logic is Product-owned.
- Platform contains no business logic.
- Registry patterns reuse existing `register/get/list_all` architecture.
- Workspace Registry remains Product-owned.
- Runtime and deployment are not redesigned by Platform routing.

### 30. Architecture Freeze Statement

This ADR freezes the AI5ROS Platform architecture:

```text
Browser
  |
  v
Application Router
  |
  v
Manifest Loader
  |
  v
Platform Registry
  |
  v
Organization Resolver
  |
  v
Organization Registry
  |
  v
Platform Context
  |
  v
Application Adapter
  |
  v
Application Entry
  |
  v
Workspace Registry
  |
  v
Workspace
```

Future implementation must conform to this dependency direction.

The Platform is a thin manifest-driven shell. Products are independently deployable applications. LTSA remains Product #1 and must not be redesigned to satisfy Platform ownership.

## Architecture Diagrams

```text
+-------------------+
| Browser           |
+---------+---------+
          |
          v
+-------------------+
| ApplicationRouter |
+---------+---------+
          |
          v
+-------------------+
| ManifestLoader    |  read-only
+---------+---------+
          |
          v
+-------------------+
| PlatformRegistry  |
+---------+---------+
          |
          v
+-------------------+
| Organization      |
| Resolver/Registry |
+---------+---------+
          |
          v
+-------------------+
| PlatformContext   |
+---------+---------+
          |
          v
+-------------------+
| ApplicationAdapter|
+---------+---------+
          |
          v
+-------------------+
| Product App       |
| LTSA / Future     |
+---------+---------+
          |
          v
+-------------------+
| WorkspaceRegistry |
+---------+---------+
          |
          v
+-------------------+
| Workspace         |
+-------------------+
```

## Ownership Diagram

```text
Platform
  owns Landing
  owns Platform Manifest
  owns Application Router
  owns Organization Context
  owns Registry loading

Product
  owns Application
  owns Workspace
  owns Workspace Registry
  owns Product API
  owns Business Logic
  owns Product Runtime

Factory
  owns Manufacturing
  owns Factory Packs
  owns Product Artifacts

Runtime
  owns Deployment Runtime
  owns Health
  owns Compose/Gateway execution
```

## Dependency Diagram

```text
Factory -> Product Manifest -> Application Descriptor -> Platform Registry
Runtime -> Runtime Manifest -> Platform Descriptor reference
Platform -> Application Adapter -> Product Application
Product Application -> Workspace Registry -> Workspace
```

Forbidden reverse dependencies:

```text
Product Application -/-> Platform Router
Workspace Registry   -/-> Platform Registry
Platform             -/-> Product Business Logic
Manifest Loader      -/-> Factory Manufacturing
```

## Lifecycle Diagram

```text
Product:
Specification -> Factory -> Artifact -> Registry -> Runtime -> Release

Manifest:
Draft -> Validated -> Released -> Registered -> Active -> Retired

Organization:
Defined -> Registered -> Active -> Suspended -> Retired

Application:
Described -> Registered -> Routable -> Active -> Retired
```

## Consequences

Positive:

- Platform/Product boundary becomes explicit.
- LTSA remains unchanged internally.
- Future products register through manifests.
- Landing can be registry-driven.
- Organization context becomes platform-owned.
- Existing registry/factory/runtime concepts are reused.

Tradeoffs:

- A generic Application Descriptor is required as the Platform/Product boundary.
- Current `App.jsx` direct imports must eventually be replaced by adapter registration.
- Existing Product Manifest JSON may need an additive application-facing section or companion descriptor.

## Architecture Freeze Recommendation

APPROVE.

This ADR should become the governing Constitution for AI5ROS Platform implementation after Chief Architect approval.
