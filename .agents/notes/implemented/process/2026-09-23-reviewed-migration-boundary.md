# Agent Note: Reviewed migration boundary

Status: implemented

## Problem

A green structural scaffold can be mistaken for completed semantic migration. Broad overwrite flags and stale plans can also replace project-owned work. Encoding one application's directory tree would reduce reuse and increase the agent's standing context.

## Decision

The agent supplies evidence-backed owner candidates and exact document edits. Scripts gather checkout facts, seal the prepared plan, export a compact review package and enforce approved scope. Ordinary in-place application requires explicit permission; fresh-context or human review remains a declared external judgment. Scaffolds have a distinct status and cannot pass completion.

The standalone verifier is generated from the same source checks as the CLI. No remote model, project-specific architecture generator, production command execution or automatic publication is introduced.

## Alternatives considered

**Fixed project templates.** Predictable names would simplify snapshot tests but bias other projects toward one application. Tests instead exercise generic invariants and filesystem behavior.

**Prompt-only enforcement.** A short reminder would be easy to maintain but could not reliably catch a stale checkout, altered plan or path escape.

**Authenticated review platform.** Signing and identity infrastructure could strengthen provenance but would add credential handling and host coupling beyond this skill's scope. Records explicitly remain attestations.

## Consequences

The main skill stays short, with detail loaded only for the selected workflow. Major migrations gain an explicit plan/review/apply boundary. Scripts cannot prove semantic accuracy, the identity of an external reviewer, or all-file crash atomicity. Separate model evaluation remains necessary for stronger assurance.
