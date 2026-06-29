# OSA Runtime Core Package

Version: 1.0.0  
Status: FINAL PACKAGE CANDIDATE

This package makes OSA bootable as a modular runtime service package.

## Workflows

- WF-OSA-RUNTIME-BOOT-001
- WF-OSA-RUNTIME-STATUS-001
- WF-OSA-RUNTIME-MODULES-001
- WF-OSA-RUNTIME-HEALTH-001
- WF-OSA-RUNTIME-EVENTS-001

## Import Steps

1. Open n8n.
2. Import each JSON file from `/workflows`.
3. Replace PostgreSQL credential placeholder with your real credential.
4. Activate the workflows.
5. Call `POST /webhook/osa/runtime/boot`.

## Important

GitHub is not required for runtime boot. PostgreSQL is the Single Source of Truth.
