# dsh-doc-audits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a portable `dsh-doc-audits` Agent Skill repository with a dependency-free governance CLI, templates, references, tests, and CI.

**Architecture:** Keep the skill self-contained under `dsh-doc-audits/`. A standard-library Python CLI performs deterministic repository inspection and validation; the Skill instructions handle semantic ownership decisions. Target repositories receive their own verifier and CI assets so governance survives without the global skill.

**Tech Stack:** Markdown, Python 3.11+ standard library, `unittest`, GitHub Actions, Git.

**Spec:** `docs/superpowers/specs/2026-09-23-dsh-doc-audits-design.md`

## Global Constraints

- Skill directory and frontmatter name are exactly `dsh-doc-audits`.
- No runtime Python dependencies.
- Existing target files are preserved unless `--force` is explicit.
- Audit is read-only by default.
- Templates and references stay directly reachable from `SKILL.md`.
- DeepSeek-specific bilingual, Cordis, website, and pnpm mechanics are excluded.
- DeepSeek MIT attribution is retained.

## Review Focus

- Paths containing spaces and non-ASCII characters must work.
- A repository with existing docs must not be overwritten during bootstrap.
- A hard code-to-doc mapping must fail only when mapped code changed and none of its owning docs changed.
- Relative Markdown anchors and external URLs must not be misclassified as missing files.
- Re-running bootstrap must be idempotent.

---

### Task 1: Repository and skill contract

**Files:**
- Create: `README.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `AGENTS.md`, `CHANGELOG.md`
- Create: `dsh-doc-audits/SKILL.md`
- Create: `dsh-doc-audits/agents/openai.yaml`
- Test: `tests/test_skill_structure.py`

**Interfaces:**
- Produces: a spec-compliant skill directory and metadata discoverable by Agent Skills clients.

- [ ] Write structural tests for directory/name/frontmatter/reference rules.
- [ ] Run tests and confirm failure because the skill files do not exist.
- [ ] Add the minimal repository and skill files.
- [ ] Run structural tests and confirm pass.
- [ ] Commit.

### Task 2: Governance CLI core

**Files:**
- Create: `dsh-doc-audits/scripts/repo_docs.py`
- Test: `tests/test_repo_docs.py`

**Interfaces:**
- Produces: `inspect_repository`, `build_plan`, `bootstrap_repository`, `verify_repository`, `audit_repository`, and CLI subcommands.

- [ ] Write failing tests for greenfield bootstrap, brownfield planning, idempotence, and preservation.
- [ ] Run tests and confirm missing implementation failure.
- [ ] Implement inspect, plan, and bootstrap minimally.
- [ ] Add failing tests for links, Agent Notes, budgets, duplicate prose, historical authority, and diff impact.
- [ ] Implement verify, audit, and impact checks.
- [ ] Run the full suite and confirm pass.
- [ ] Commit.

### Task 3: Templates and references

**Files:**
- Create: `dsh-doc-audits/references/*.md`
- Create: `dsh-doc-audits/assets/repo-governance/**`
- Modify: `dsh-doc-audits/SKILL.md`
- Test: `tests/test_templates.py`

**Interfaces:**
- Consumes: the CLI template substitution contract.
- Produces: a complete target-repository governance scaffold.

- [ ] Write failing tests for required templates, placeholders, manifest validity, and generated verifier execution.
- [ ] Run tests and confirm missing templates fail.
- [ ] Add focused references and target templates.
- [ ] Wire the CLI to the asset tree.
- [ ] Run tests and confirm pass.
- [ ] Commit.

### Task 4: Integration fixtures and CI

**Files:**
- Create: `tests/fixtures/**`
- Create: `.github/workflows/ci.yml`
- Create: `Makefile`, `pyproject.toml`, `.gitignore`
- Create: `scripts/verify.sh`

**Interfaces:**
- Produces: one-command local and CI verification.

- [ ] Add integration tests for greenfield, brownfield, drifted, existing-docs, and no-doc-impact fixtures.
- [ ] Run tests and observe expected failures for uncovered cases.
- [ ] Complete CLI edge handling and fixtures.
- [ ] Add CI and local verification entry points.
- [ ] Run all checks.
- [ ] Commit.

### Task 5: Whole-repository verification and release package

**Files:**
- Modify: `README.md`, `CHANGELOG.md` as required by verified behavior.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: version `0.1.0` source archive and Git bundle.

- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `bash scripts/verify.sh`.
- [ ] Run the skill CLI against its own repository.
- [ ] Review the complete diff against the spec.
- [ ] Create release archives and record exact checks.
- [ ] Commit final fixes.
