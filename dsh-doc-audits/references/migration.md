# Migration Rules

## Report first

Before writes, produce a migration plan with:

- repository profile and evidence;
- current documents and their apparent jobs;
- proposed authority map;
- files to create, edit, move, or preserve;
- historical material and treatment;
- inbound links to repair;
- generated assets to install;
- explicit exclusions, especially product code;
- verification and rollback steps.

## Merge mode

Existing documents are evidence and project-owned content. Fill gaps, link to good material, and preserve files outside the selected governance scope. Do not overwrite, rename, or delete an existing document solely because a template prefers another name.

## Safe order

1. Add missing current owners.
2. Move or rewrite current facts into those owners.
3. Update README and AGENTS routing.
4. Demote historical plans and specs with status and current-owner links.
5. Repair inbound links.
6. Add repository-local verifier and CI.
7. Run deterministic and semantic audits.
8. Delete or archive only in a later reviewed cleanup.

## Idempotence

A repeated migration command must not duplicate files, paragraphs, links, notes, or status markers. Unchanged generated assets report `unchanged`; conflicting existing files report `preserved` unless explicit force applies to a known generated file.

## Authority conflicts

Stop semantic writes for a domain when source, tests, and current documentation disagree in a way that changes user-visible or operational meaning and the repository cannot resolve it. Record the conflict, evidence, affected owners, and the decision required. Continue independent domains.

## Rollback

Use small commits grouped by governance layer:

1. scaffold and manifest;
2. current authority docs;
3. routing and historical demotion;
4. verifier and CI.

A migration that changes product behavior belongs in a separate branch or plan.
