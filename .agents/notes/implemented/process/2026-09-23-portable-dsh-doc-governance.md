# Agent Note: Portable DSH documentation governance

Status: implemented

## Problem

DeepSeek Harness provides a rigorous documentation governance model, but its `dsh-doc` workflow is coupled to bilingual pairing, Cordis package kinds, VitePress projection, TypeScript checks, and pnpm gates. Copying it directly into unrelated repositories would impose mechanisms those repositories do not own.

## Decision

`dsh-doc-audits` retains the governance core—one current owner per fact, explicit documentation tiers, executable fact checking, Agent Note lifecycle, corpus audits, document budgets, and repository gates—and reimplements the portable layer around Python standard-library tooling.

The skill adds bootstrap, brownfield migration, diff synchronization, audit, and upgrade modes. It installs a JSON-compatible YAML manifest, a repository-local verifier, and GitHub Actions scaffolding. Existing target files are preserved by default, semantic migrations remain agent-guided, and product code stays outside documentation migration scope.

## Alternatives considered

**Fork `dsh-doc` with only textual deletions.** Rejected because its remaining sections and checks reference DeepSeek-specific kinds, pair metadata, website projection, and gate names; deleting paragraphs would leave a brittle partial workflow.

**Use a generic documentation generator as the primary model.** Rejected because generation and brownfield convenience do not preserve the DSH distinction among current facts, rationale, historical process, and deterministic governance.

**Keep governance only in a global Skill.** Rejected because an unloaded or replaced skill would leave the repository unable to enforce its own rules.

## Consequences

Target repositories gain portable, dependency-free checks and can continue governance without the global skill. JSON-compatible YAML is less idiomatic than conventional YAML and does not support comments, but avoids parser dependencies. Semantic correctness still requires agent or human judgment; deterministic scripts deliberately cover only questions with stable answers.
