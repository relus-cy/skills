# Agent Note: Installable skills live in skills/

Status: implemented

## Problem

Skills sat at the repository root next to `docs/`, `tests/`, `scripts/` and `vendor/`, so it was unclear which directories an installer should take. The `dsh-doc-audits` bundle also depended on root files for its license and third-party attribution, so a copied bundle lost them.

Skillshare copies a skill's whole directory on install. Its `.skillignore` hides whole skills only, and it has no file-level exclusion for skills (checked against skillshare 0.25.3). Anything inside a bundle is installed and scanned by the install audit.

## Decision

Every installable skill is a complete bundle in `skills/<name>/` and refers to nothing outside it. Bundles carry their own `LICENSE` and notices where attribution applies. Tests, fixtures, development scripts, design records and the changelog stay at the repository root and are never installed; `mail-cli` tests moved to `tests/mail-cli/`. Vendored skills are generated into `skills/`.

This follows the layout of `hylarucoder/hai-stack` (`skills/<name>/`, with evals and scripts at the root) and `mattpocock/skills` (`skills/<category>/<name>/`, with scripts, docs and the plugin manifest at the root). Recipients of a skill get only the bundle, not its development history.

## Alternatives considered

- **Skills at the repository root (previous layout).** Installers and readers cannot tell bundles from repository tooling.
- **One project directory per skill, with the bundle nested inside and tests, tools and records beside it.** Tried and rejected on 2026-10-13: it duplicates repository scaffolding per skill and hands development material to people who only need the skill.
- **Tests and records inside each bundle.** They would be installed and audited with the skill.

## Consequences

Installers address one skill as `relus-cy/skills/skills/<name>` or discover all of them from the repository. Local installs must point at `skills/<name>/`. The repository verifier, version tests and documentation cover all skills from the root; `scripts/verify.sh` stays the single entry point.
