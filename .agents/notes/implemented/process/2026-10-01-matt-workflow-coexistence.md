# Agent Note: Matt workflow coexistence

Status: implemented

## Problem

A hard-coded glossary name makes repositories using `GLOSSARY.md` invisible to parts of inspection and rejects their reviewed writes. Treating every decision home as Agent Notes would also impose a second lifecycle on projects already using ADRs. External tickets can close without transferring durable behavior into repository documentation.

## Decision

The manifest's optional `authority.glossary` owns glossary location; absent configuration recognizes both conventional root filenames without silently selecting an owner when both exist. The same resolver serves discovery and the write boundary. An explicit Markdown path is a narrow documentation exception and retains ordinary path and historical protections. Current and proposed manifests can support a reviewed glossary relocation in one change.

Matt-owned terminology, ADRs, agent guides and skill routing remain project-owned. Existing ADR retrieval uses the Agent Notes opt-out; there is no separate ADR parser or lifecycle engine. External tracker close-out is a semantic sync responsibility: durable contracts return to current owners, while tracker contents and state remain outside local verification. The [repository contract](../../../../dsh-doc-audits/references/repository-contract.md#matt-skills-coexistence) owns the operational rules.

This follows mainstream lightweight [ADR practice](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) for preserving decision context and alternatives. It follows the recognized [Diátaxis separation of explanation and reference](https://diataxis.fr/start-here/) by keeping rationale separate from current contracts. Matt's agent-oriented workflow is the emerging practice being accommodated, not a mandatory dependency or a replacement for DSH governance.

## Alternatives considered

**Rename every glossary to one fixed filename.** Simpler discovery would break existing repositories or fight their domain-modeling tools. Explicit ownership with compatible defaults avoids that migration requirement.

**Import Matt's whole workflow into dsh.** This would duplicate responsibility for specs, tickets and implementation, and require tracker access for a local documentation check. Compatibility only needs shared owners and a close-out boundary.

**Convert ADRs into Agent Notes.** Another lifecycle adds no retrieval value; the existing Markdown decision-evidence contract already admits ADRs.

**Make every root Markdown file writable.** That enlarges the write surface beyond the demonstrated glossary need. A named authority grants the specific exception while retaining guarded application.

## Consequences

Old `CONTEXT.md` layouts remain usable, and ambiguous dual glossaries need an explicit authority decision. Existing manifests add Matt tiers through a reviewed sync or migration; generated-asset upgrades preserve that project policy. Local checks can show structural compatibility but cannot verify external ticket closure or ADR semantics. Provenance and licensing are recorded in [lineage](../../../../dsh-doc-audits/references/lineage.md); no external workflow implementation is bundled.
