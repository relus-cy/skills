# Sources and adaptations

## Retained governance ideas

This skill generalizes these DeepSeek Harness documentation practices:

- one home per fact;
- root and subtree `AGENTS.md` as concise standing orders;
- architecture, subsystem, procedure, reference, decision, history, generated, and skill tiers;
- current-state prose outside dedicated history owners;
- Agent Note lifecycle and present-tense implemented records;
- executable fact checking;
- corpus audits for duplication, status rot, restated catalogs, and reasoning leakage;
- document budgets;
- deterministic repository gates.

## Removed DeepSeek-specific mechanics

The portable skill does not require:

- English/Chinese line-aligned pairs or sidecar hashes;
- Cordis plugin, library, bundle, or package-group kinds;
- DeepSeek package README sections;
- VitePress website projection;
- TypeScript type-equivalence fences;
- pnpm or DeepSeek-specific gate names;
- persistence-history formats unique to DeepSeek Harness.

## Added portable mechanics

- greenfield bootstrap and brownfield migration modes;
- a JSON-compatible YAML governance manifest;
- hard and soft Git diff mappings;
- dependency-free Python verification;
- optional profile hints without fixed output trees;
- prepared plans, compact review packages and exact-scoped application;
- explicit idempotence and existing-document preservation;
- fresh-session retrieval testing;
- an Agent Notes opt-out that requires another Markdown home for rationale (DSH requires Agent Notes);
- optional retention of shipped plans under declared historical tiers (DSH treats `docs/` scratch as expiring);
- a bootstrap core with tiers created when content first needs them (DSH repositories carry the full structure).

DeepSeek Harness is MIT-licensed. Repository attribution is recorded in `THIRD_PARTY_NOTICES.md`.

## Matt Pocock workflow compatibility

The optional layout reference is [mattpocock/skills at commit `d81f3a1`](https://github.com/mattpocock/skills/tree/d81f3a183412e71a5b1e84ca21bc1a35eea03a60), the installation snapshot checked on 2026-10-01. Its [domain-modeling skill](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/engineering/domain-modeling/SKILL.md) supplies the `GLOSSARY.md` and ADR conventions; [setup-matt-pocock-skills](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/engineering/setup-matt-pocock-skills/SKILL.md) supplies the agent-guide and skill-routing layout. The [license at that commit](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/LICENSE) is MIT, copyright 2026 Matt Pocock.

This bundle contains original compatibility rules, not copied Matt skill implementations, templates or workflow instructions. Matt is an optional workflow reference; DSH remains the documentation-governance method. The [repository contract](repository-contract.md#matt-skills-coexistence) owns the shared-file boundary and [sync](workflow.md#sync) owns durable write-back from external trackers. No Matt skill or tracker integration is installed or invoked by dsh.

## Additional workflow reference

The lightweight environment/review/verification boundary also reflects the user-selected engineering discussion at https://tw93.fun/2026-03-12/claude.html. It supplies workflow context, not a repository directory standard or a mandatory runtime dependency.
