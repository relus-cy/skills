# {{PROJECT_NAME}} architecture

Status: current authority
Last reviewed: {{DATE}}

## Purpose and boundaries

Record the system's purpose, users, external systems, and trust boundaries here. Keep product introduction in the root README and detailed component contracts in `docs/subsystems/`.

## Component map

Describe components in dependency order. For each component, state its responsibility, public boundary, dependencies, and owning path.

## Primary flows

Describe the few runtime or data flows a maintainer must understand before changing cross-module behavior. Link each detailed step to its subsystem owner.

## Storage and external dependencies

Name durable stores, queues, third-party services, generated artifacts, and ownership boundaries. Link exact schemas and settings to `docs/reference/`.

## Deployment and operations

Summarize environments and deployment topology. Link executable procedures to `docs/runbooks/`.

## Extension points and constraints

State where capabilities may be added, which contracts are frozen, and which changes require an Agent Note.
