# Profile: Small Web App

Use for a single-repository web application with one API or server, one browser client, a small operations surface, and no complex package hierarchy.

## Suggested current owners

- `README.md`: product identity, quick start, test command, documentation map.
- `AGENTS.md`: concise task-to-document routing and hard constraints.
- `docs/architecture.md`: browser → API → domain/service → storage/external adapters → deployment.
- `docs/subsystems/`: data acquisition, core domain calculation, display/feed layer, authentication, background work, or other cohesive capabilities.
- `docs/runbooks/`: local development, deployment, health checks, backup/recovery, data repair, public release.
- `docs/reference/`: HTTP contracts, environment variables, data formats, cache semantics, limits.
- `CONTEXT.md`: optional domain glossary when recurring project-specific terms would otherwise drift.

## Suggested impact posture

Hard mappings:

- routes, schemas, and public response models → API reference and affected subsystem;
- environment validation and examples → configuration reference and deployment runbook;
- deploy/recovery scripts and CI → runbooks;
- durable schema or wire format → reference plus Agent Note when the choice is lasting.

Soft mappings:

- internal module refactors → architecture or subsystem review;
- UI-only layout changes → no documentation unless workflow, terminology, accessibility, or user-visible state changes.

## Migration emphasis

Small apps often accumulate a large README, one large API file, one large frontend file, and dated design plans. First split documentation authority without combining it with code modularization. Code boundaries may become a later architecture task once current contracts are explicit.
