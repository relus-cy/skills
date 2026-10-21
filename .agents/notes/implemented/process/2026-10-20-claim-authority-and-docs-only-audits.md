# Agent Note: Claim authority and docs-only audits

Status: implemented

## Problem

The audit method told the agent to settle every code/prose mismatch from source and tests and then update the document. When code violated an approved decision, such as a security requirement or a published contract, that rule led the agent to weaken the decision so it matched the defect. The audit also assumed code was available. For a document set without code, such as a PRD collection, it had no evidence standard and no rule for calling text stale. `audit` reported `governance-missing` there, with no guidance to treat that as a skipped structural check.

The user also used `hai-audit-docs` from `hylarucoder/hai-stack`, which overlapped with this skill's triggers. Its distinct ideas were docs-only internal audits and claim-class authority. The user chose to absorb those ideas here and disable the overlapping skill.

## Decision

Before choosing a repair target, each audit finding names the source that settles its claim class. Current-behavior claims follow code and tests (documentation drift). Intended or contractual claims in an approved decision owner follow that decision; a mismatch is an implementation gap, reported but not repaired during an audit. A current owner that presents unimplemented approved behavior as current gets both findings: the gap, and a repair that states actual behavior and links the unmet decision. An unclear approval status is recorded as needs decision.

A docs-only audit covers only a document set that the user names. It looks for contradictions, terminology drift, boundary and sequence mismatches, and weak acceptance criteria. It calls text stale only with supersession evidence inside the set, and its report leaves runtime behavior unverified. A docs-only audit never asks the first-run collaboration question. The activation description names this scope, so docs-only requests reach this skill without widening it into general prose review.

The [audit rubric](../../../../skills/dsh-doc-audits/references/audit-rubric.md#claim-authority) owns the rules. They are semantic guidance only; no deterministic check was added.

## Alternatives considered

- **Keep "code wins" and rely on reviewer judgment.** Rejected: the default directs the repair toward weakening approved decisions.
- **Keep `hai-audit-docs` beside this skill.** Rejected: overlapping triggers split audits between two rule sets with different authority defaults.
- **Copy `hai-audit-docs` references into the bundle.** Rejected: the installed copy carried no license file. The rules were rewritten for this skill's tier model instead.
- **Run the CLI on manifest-less document sets.** Rejected: contradiction detection needs semantic judgment, and the extension policy adds checks only for concrete failures.

## Consequences

Audit reports carry a finding class (documentation drift, implementation gap, internal conflict, or needs decision). Docs-only reports do not certify runtime behavior. The trigger text is broader, but only for named docs-only sets; repository governance stays the main purpose.
