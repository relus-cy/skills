# Matt compatibility verification — 0.3.0

Scope: the `dsh-doc-audits` source bundle in this repository. No chanapp files, installed skills, commits or remote publications are part of this change.

## Behavior and evidence

The repeatable acceptance artifact is [test_glossary_compat.py](../../tests/test_glossary_compat.py), using the [Matt fixture](../../tests/fixtures/matt-layout/README.md) in disposable Git repositories. It exercises CLI preparation/application and standalone generated verification without a tracker or external model.

| Failure or boundary | Evidence |
| --- | --- |
| Conventional glossary is missed or cannot be written | `test_default_discovery_preservation_and_legacy` covers both filenames and actual apply |
| Two glossaries silently select competing authority | `test_dual_defaults_remain_visible_without_silent_choice` checks preservation and unresolved candidates |
| Explicit custom path is ignored or rejected | `test_explicit_custom_path_and_same_plan_configuration` declares and writes root and nested paths |
| Renaming a configured glossary breaks repeated application | `test_glossary_move_repeat_is_already_applied` checks exact repeat and changed-state rejection |
| Missing explicit owner silently falls back | `test_explicit_missing_owner_does_not_fall_back` requires the missing-authority finding |
| Invalid paths or linked files widen the write boundary | Invalid configuration and linked-glossary cases reject them |
| Absent or malformed manifest produces an invented owner | No-manifest/malformed regression checks fallback only when no manifest exists |
| ADRs/agent guides become untiered or are overwritten | Matt scenario checks verify, bootstrap preservation and actual generated-verifier upgrade |
| ADR cannot supply the decision topic | Matt scenario passes ADR evidence through fresh-session validation |

## RED, GREEN and refactor

RED: `python -m unittest discover -s tests -p test_glossary_compat.py -v` initially ran six tests with 13 failing subcases. Failures exposed missing glossary discovery, preservation, custom writes, configuration validation and Matt tier coverage. Legacy behavior and linked-file rejection already passed; these are regression evidence, not newly implemented capabilities.

A second RED reproduced a custom glossary move succeeding once and then failing on repeat because the replacement manifest no longer named the old path. GREEN permits a no-write repeat only when the complete bound post-application state matches. Restoring the old path or changing the new document still rejects the plan.

The implementation shares glossary resolution across inspection, planning, guarded writes and verifier validation. Refactoring extracts the expected post-application binding for reuse by validation and application; it adds no new control schema. Pure reference, attribution and version edits use document/release checks rather than artificial TDD tests.

## Verification and limits

Final acceptance: `bash scripts/verify.sh` passed on 2026-10-01: 152 tests in 38.892 seconds, generation parity PASS, repository-local completion checks and CLI verify/audit each with zero errors and zero warnings, and whitespace checks PASS. The nine compatibility tests include the final malformed-policy and relocation regressions.

An independent verifier reviewed the change against HEAD, directly retrieved the fixture ADR's rationale and alternative, and probed forged post-state plans. Product files, metadata and frozen Notes remained rejected; an exact retired Markdown post-state returned `already-applied` without writes, and changed content was rejected. No additional confirmed defect remained in the reviewed scope.

The compatibility test's reader/reviewer JSON is explicitly synthetic: it tests accepted evidence paths and approval contracts, not independent semantic judgment. The fixture is not a completed real-project migration. External tracker contents, closure state and consumer repository changes remain outside this test scope.

The optional bundled skill-creator `quick_validate.py` could not start because this environment lacks `PyYAML`. No package was installed to run it. Repository skill-structure, release consistency and document checks provide the executed local validation instead.

## Consumer hand-back

Use version 0.3.0 of the complete bundle. The authoritative [glossary and Matt layout contract](../../dsh-doc-audits/references/repository-contract.md#glossary-authority) includes the partial manifest example: merge `authority.glossary: GLOSSARY.md` and the `GLOSSARY.md`, `docs/adr/**`, `docs/agents/**` current-tier entries into the existing configuration. Preserve unrelated policy. Existing repositories update these mappings through sync or migration; generated-only upgrade cannot rewrite them.

There is no `upgrade` CLI subcommand. After obtaining exact generated verifier bytes and preparing a proposal, run:

```bash
python <skill-dir>/scripts/repo_docs.py plan --repo <repo> --mode upgrade --proposal <control>/proposal.json --output <control>/plan.json --json
python <skill-dir>/scripts/repo_docs.py review-pack --repo <repo> --plan <control>/plan.json --output <control>/review-package.json --json
# Obtain an independent review of this exact package, then preview:
python <skill-dir>/scripts/repo_docs.py apply --repo <repo> --plan <control>/plan.json --review <control>/review.json --dry-run --json
```

Use a clean linked worktree, or add `--allow-in-place` only for an authorized clean ordinary checkout. Follow the [workflow](../../dsh-doc-audits/references/workflow.md#upgrade) for application and verification. Commit and installed-copy synchronization still require the owner's review of the diff.
