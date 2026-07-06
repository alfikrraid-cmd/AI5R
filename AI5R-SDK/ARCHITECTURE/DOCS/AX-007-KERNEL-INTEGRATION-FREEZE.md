# AX-007 — AI5R Kernel Integration Freeze

## Status

FROZEN

## Purpose

Freeze the AI5R Kernel Integration Architecture.

From this version forward, the Kernel SHALL become the canonical entry point for AI manufacturing.

## Canonical Execution Stack

AI5R Kernel
↓
Manufacturing Pipeline
↓
Workflow Engine
↓
Station Dispatcher
↓
Station Registry
↓
Manufacturing Stations

## Kernel Rule

The Kernel SHALL receive manufacturing requests, select workflow, invoke pipeline, and return manufacturing results.

The Kernel SHALL NOT directly execute stations.

## Pipeline Rule

The Manufacturing Pipeline SHALL create manufacturing context, invoke dispatcher, collect execution history, and return final context.

The Pipeline SHALL NOT resolve stations directly.

## Dispatcher Rule

The Station Dispatcher SHALL read workflow, resolve stations through registry, execute stations sequentially, stop on execution failure, and return updated context.

The Dispatcher SHALL NOT contain business logic.

## Registry Rule

The Station Registry SHALL register, unregister, resolve, and validate stations.

The Registry SHALL NOT execute stations.

## Station Rule

Every station SHALL inherit from BaseManufacturingStation.

Every station SHALL expose station_code, station_name, and execute(context).

Every station SHALL modify only the received context.

Stations SHALL NOT invoke other stations directly.

## Workflow Rule

Workflow is declarative.

Execution order SHALL be defined by workflow.

Controllers SHALL NOT hardcode execution order.

## Context Rule

ManufacturingContext is the only execution object shared between stations.

Stations communicate exclusively through context.

Global mutable state SHOULD be avoided.

## Product Rule

Products SHALL be manufactured through the Kernel.

Products SHALL NOT bypass Workflow, Dispatcher, Registry, Stations, or Pipeline.

## Domain Rule

Domains remain reusable manufacturing units.

Products are composed from one or more domains.

## Evolution Rule

Future extensions SHALL be implemented by adding stations, workflows, or kernel services.

Existing contracts SHALL remain backward compatible.

## Frozen Decision

AI5R Kernel v1.0 is now frozen.

Future platform evolution SHALL preserve this architecture unless superseded by a future Architecture Freeze document.
