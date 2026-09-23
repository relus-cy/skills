# Governance Core

## Objective

A repository's documentation forms a control plane for people and agents. The control plane is reliable when each durable fact has one current owner, every derivative page links to that owner, and the repository can mechanically detect structural drift.

## Tier taxonomy

| Tier | Job | Typical location |
| --- | --- | --- |
| Standing orders | Rules needed in almost every agent session | Root and subtree `AGENTS.md` |
| Architecture | Ordered system map, composition, boundaries, dependencies, extension points | `docs/architecture.md` |
| Subsystem contract | Current semantics, types, lifecycle, failure behavior, public boundary | `docs/subsystems/` or package-local README |
| Runbook | Executable procedure, success signal, recovery, rollback | `docs/runbooks/` |
| Reference | Precise APIs, configuration, formats, fields, limits | `docs/reference/` or generated catalogs |
| Decision rationale | Durable why, alternatives, trade-offs, required verification | `.agents/notes/` |
| Historical evidence | Plans, reports, handoffs, releases, postmortems | Historical directories declared by the project |
| Generated material | Exhaustive projection of source | Generator-owned output with freshness checks |
| Skill | Reusable workflow and judgment standard | Global or repository skill directory |

Skills do not own product facts. Source, tests, current docs, generated catalogs, and decision records retain their own kinds of truth.

## One owner per fact

Before writing, answer four questions:

1. What exact fact is being stated?
2. Which tier's job is to own it?
3. What source, test, command, schema, or decision proves it?
4. Which other pages should link to it rather than repeat it?

When two pages carry the same current contract, select the nearest owner, move or rewrite the fact there, and replace the duplicate with a short link. Preserve distinct audience framing only when it does not restate the contract.

## Current state and history

Ordinary docs use present tense and describe the checkout that exists now. Keep migration narrative, superseded defaults, implementation chronology, investigations, and rejected directions in their historical owner. An implemented Agent Note may retain the original rationale and alternatives, but its paths, names, and current consequences remain accurate.

Never use an archived decision, old plan, handoff, or release note as the default current authority. Current docs may cite historical material deliberately to explain provenance.

## Fact checking

Operational claims require observed evidence:

- run commands exactly as written;
- inspect current source for defaults and supported values;
- verify API and data shapes from handlers, schemas, tests, or generators;
- record exact failure behavior when it affects users or operators;
- mark unavailable checks as unverified and name who or what can verify them.

When code and prose disagree, treat the mismatch as a finding. Do not silently choose convenient prose. Determine the current behavior from source and tests, update its owner, and preserve historical rationale separately.

## Budgets

Budgets prevent standing documents from absorbing every detail. Apply this order when a document exceeds its ceiling:

1. Relocate content that belongs to another tier.
2. Condense duplicate or low-value explanation.
3. Raise the ceiling only when the content genuinely belongs and the change records why.

For multilingual or mixed-language repositories, Unicode character counts are a stable dependency-free guardrail. Projects may replace the metric with a tested language-aware counter.

## Corpus warning signs

- duplicated rules or contracts;
- history mixed into current documentation;
- status inventories that source can generate;
- hand-copied API, schema, configuration, or test catalogs;
- implementation diary or reasoning transcript in a current reference;
- proposal-stage language in implemented decisions;
- one entry page that must explain every subsystem;
- generated output edited by hand;
- commands copied from memory and never executed;
- historical paths described as the current source of truth.
