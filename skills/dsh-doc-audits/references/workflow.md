# Workflow

This file defines mode-specific execution. It is intentionally concise in the initial scaffold and is expanded together with tested CLI behavior.

## Common sequence

Inspect, classify owners, write a plan, apply the smallest safe change, run deterministic checks, audit semantics, then run a fresh-session retrieval test for major migrations.
