# OS-005 Context Manager

## Purpose

Context Manager provides runtime context storage for AI5R OS processes.

It allows digital processes to carry state, metadata, and operating context across the AI5R Operating System lifecycle.

## Responsibilities

- Create process context
- Retrieve process context
- Update context data
- Update context metadata
- Delete context
- List active contexts

## Context Model

Every context contains:

- context_id
- process_id
- scope
- data
- metadata
- created_at
- updated_at

## Compatibility Rule

Context Manager does not replace Process Manager, Lifecycle Manager, Event Bus, or Process Scheduler.

It extends the OS layer by providing runtime state continuity.
