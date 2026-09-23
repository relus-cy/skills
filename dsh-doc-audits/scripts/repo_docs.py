#!/usr/bin/env python3
"""Deterministic helpers for dsh-doc-audits.

The semantic migration remains an Agent task. This module inventories repositories,
creates migration plans, installs missing governance assets, and runs checks whose
answers are deterministic.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from fnmatch import fnmatchcase
from urllib.parse import unquote
from datetime import date
from pathlib import Path
from typing import Any, Iterable


VERSION = "0.1.0"
SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE_ROOT = SKILL_ROOT / "assets" / "repo-governance"

TARGET_FILES = (
    "README.md",
    "AGENTS.md",
    "docs/AGENTS.md",
    "docs/architecture.md",
    "docs/backlog.md",
    "docs/governance.yaml",
    "docs/subsystems/_template.md",
    "docs/runbooks/_template.md",
    "docs/reference/_template.md",
    ".agents/notes/README.md",
    ".agents/notes/proposed/_template.md",
    ".agents/notes/implemented/_template.md",
    ".agents/notes/rejected/.gitkeep",
    ".agents/notes/archived/.gitkeep",
    "scripts/verify_docs.py",
    ".github/workflows/docs-governance.yml",
)

DEFAULT_EXCLUDE_PATTERNS = (
    ".git/**",
    ".venv/**",
    "node_modules/**",
    "**/__pycache__/**",
)


KNOWN_HISTORICAL_SURFACES = (
    "docs/superpowers",
    "docs/releases",
    "docs/postmortems",
    "docs/postmortem",
    "docs/plans",
    "docs/reports",
    "docs/handoffs",
)


def _normalize_repo(repo: str | os.PathLike[str] | Path) -> Path:
    path = Path(repo).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"repository path does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"repository path is not a directory: {path}")
    return path


def _relative_files(repo: Path, exclude_patterns: Iterable[str] = ()) -> list[str]:
    patterns = (*DEFAULT_EXCLUDE_PATTERNS, *(str(pattern) for pattern in exclude_patterns))
    files: list[str] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(repo).as_posix()
        except ValueError:
            continue
        if any(_matches(rel, pattern) for pattern in patterns):
            continue
        files.append(rel)
    return sorted(files)


def _contains_token(repo: Path, paths: Iterable[str], tokens: Iterable[str]) -> bool:
    path_list = list(paths)
    token_tuple = tuple(tokens)
    skill_roots = {
        Path(rel).parts[0]
        for rel in path_list
        if Path(rel).name == "SKILL.md" and len(Path(rel).parts) > 1
    }
    for rel in path_list:
        parts = Path(rel).parts
        if parts and (parts[0] in {"docs", "tests", "test", ".agents", ".github"} or parts[0] in skill_roots):
            continue
        path = repo / rel
        if path.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".jsx"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:200_000]
        except OSError:
            continue
        if any(token in text for token in token_tuple):
            return True
    return False


def inspect_repository(repo: str | os.PathLike[str] | Path) -> dict[str, Any]:
    root = _normalize_repo(repo)
    files = _relative_files(root)
    meaningful = [
        p
        for p in files
        if Path(p).name not in {".gitkeep", ".DS_Store"}
    ]

    signals: list[str] = []
    if any(
        p in {"pyproject.toml", "requirements.txt", "setup.py", "setup.cfg"} or p.endswith(".py")
        for p in files
    ):
        signals.append("python")
    if any(p in {"package.json", "pnpm-lock.yaml", "yarn.lock"} or p.endswith((".js", ".ts", ".tsx", ".jsx")) for p in files):
        signals.append("javascript")
    if (root / "api").is_dir() or _contains_token(root, files, ("FastAPI", "Flask(", "django")):
        signals.append("web-api")
    if (root / "web").is_dir() or (root / "frontend").is_dir() or _contains_token(root, files, ("React", "Vue", "lightweight-charts")):
        signals.append("web-ui")

    historical = [surface for surface in KNOWN_HISTORICAL_SURFACES if (root / surface).exists()]
    doc_surfaces = [
        p
        for p in ("README.md", "AGENTS.md", "CONTEXT.md", "docs")
        if (root / p).exists()
    ]

    return {
        "project_name": root.name,
        "repository_state": "brownfield" if meaningful else "greenfield",
        "stack_signals": sorted(set(signals)),
        "documentation_surfaces": doc_surfaces,
        "historical_surfaces": historical,
        "file_count": len(files),
        "git_repository": (root / ".git").exists(),
    }


def build_plan(
    repo: str | os.PathLike[str] | Path,
    profile: str = "small-web-app",
) -> dict[str, Any]:
    root = _normalize_repo(repo)
    inventory = inspect_repository(root)
    existing = set(_relative_files(root))
    preserve = sorted(path for path in TARGET_FILES if path in existing)
    # Root entry points are project-owned and are preserved even though templates do not replace them.
    preserve.extend(path for path in ("README.md", "AGENTS.md", "CONTEXT.md") if path in existing and path not in preserve)
    create = sorted(path for path in TARGET_FILES if path not in existing)

    return {
        "schema_version": 1,
        "skill_version": VERSION,
        "mode": "bootstrap" if inventory["repository_state"] == "greenfield" else "migrate",
        "profile": profile,
        "project_name": inventory["project_name"],
        "inventory": inventory,
        "create": create,
        "preserve": sorted(preserve),
        "historical_surfaces": inventory["historical_surfaces"],
        "authority_suggestions": {
            "project_entry": "README.md",
            "agent_instructions": "AGENTS.md",
            "architecture": "docs/architecture.md",
            "backlog": "docs/backlog.md",
            "terminology": "CONTEXT.md" if (root / "CONTEXT.md").exists() else None,
        },
        "safety": {
            "overwrite_existing": False,
            "delete_historical": False,
            "modify_product_code": False,
        },
    }


def _render_template(text: str, repo: Path, profile: str) -> str:
    replacements = {
        "{{PROJECT_NAME}}": repo.name,
        "{{DATE}}": date.today().isoformat(),
        "{{SKILL_VERSION}}": VERSION,
        "{{PROFILE}}": profile,
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text


def bootstrap_repository(
    repo: str | os.PathLike[str] | Path,
    profile: str = "small-web-app",
    *,
    template_root: str | os.PathLike[str] | Path | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    root = _normalize_repo(repo)
    templates = Path(template_root).expanduser().resolve() if template_root is not None else DEFAULT_TEMPLATE_ROOT
    if not templates.is_dir():
        raise FileNotFoundError(f"template root does not exist: {templates}")

    result: dict[str, Any] = {
        "project_name": root.name,
        "profile": profile,
        "created": [],
        "updated": [],
        "preserved": [],
        "unchanged": [],
        "would_create": [],
        "would_update": [],
    }

    template_files = sorted(path for path in templates.rglob("*") if path.is_file())
    for source in template_files:
        rel = source.relative_to(templates)
        rel_text = rel.as_posix()
        target = root / rel
        rendered = _render_template(source.read_text(encoding="utf-8"), root, profile)

        if target.exists():
            current = target.read_text(encoding="utf-8")
            if current == rendered:
                result["unchanged"].append(rel_text)
            elif force:
                if dry_run:
                    result["would_update"].append(rel_text)
                else:
                    target.write_text(rendered, encoding="utf-8")
                    result["updated"].append(rel_text)
            else:
                result["preserved"].append(rel_text)
            continue

        if dry_run:
            result["would_create"].append(rel_text)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        result["created"].append(rel_text)

    return result



def _finding(code: str, severity: str, path: str, message: str, **extra: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "path": path,
        "message": message,
    }
    value.update(extra)
    return value


def _matches(path: str, pattern: str) -> bool:
    normalized = path.replace(os.sep, "/").lstrip("./")
    pattern = pattern.replace(os.sep, "/").lstrip("./")
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return normalized == prefix or normalized.startswith(prefix + "/")
    return fnmatchcase(normalized, pattern)


def _load_governance(root: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    path = root / "docs" / "governance.yaml"
    if not path.is_file():
        return None, [_finding(
            "governance-missing",
            "error",
            "docs/governance.yaml",
            "The repository has no governance manifest.",
        )]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [_finding(
            "governance-invalid",
            "error",
            "docs/governance.yaml",
            f"The governance manifest must be JSON-compatible YAML: {exc}",
        )]
    if not isinstance(data, dict):
        return None, [_finding(
            "governance-invalid",
            "error",
            "docs/governance.yaml",
            "The governance manifest root must be an object.",
        )]
    return data, []


def _markdown_link_findings(
    root: Path,
    exclude_patterns: Iterable[str] = (),
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    scheme_re = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
    for rel in _relative_files(root, exclude_patterns):
        if not rel.endswith(".md"):
            continue
        path = root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for raw in link_re.findall(line):
                target = raw.strip()
                if target.startswith("<") and ">" in target:
                    target = target[1:target.index(">")]
                else:
                    target = target.split(maxsplit=1)[0]
                if not target or target.startswith("#") or target.startswith("/") or scheme_re.match(target):
                    continue
                target = unquote(target.split("#", 1)[0].split("?", 1)[0])
                if not target:
                    continue
                resolved = (path.parent / target).resolve()
                try:
                    resolved.relative_to(root)
                except ValueError:
                    findings.append(_finding(
                        "markdown-link-outside",
                        "error",
                        rel,
                        f"Line {line_no} links outside the repository: {raw}",
                        line=line_no,
                    ))
                    continue
                if not resolved.exists():
                    findings.append(_finding(
                        "markdown-link-broken",
                        "error",
                        rel,
                        f"Line {line_no} links to a missing local target: {raw}",
                        line=line_no,
                    ))
    return findings


def _agent_note_findings(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    notes_config = config.get("agent_notes") or {}
    note_root_rel = str(notes_config.get("root") or ".agents/notes")
    note_root = root / note_root_rel
    statuses = notes_config.get("statuses") or {
        "proposed": "proposed",
        "implemented": "implemented",
        "rejected": "rejected",
        "archived": "implemented",
    }
    required = {
        "proposed": {"Problem", "Proposal", "Alternatives considered", "Acceptance criteria", "Risks"},
        "implemented": {"Problem", "Decision", "Alternatives considered", "Consequences"},
        "rejected": {"Problem", "Proposal", "Alternatives considered"},
        "archived": {"Problem", "Decision", "Alternatives considered", "Consequences"},
    }
    forbidden_implemented = {"Proposal", "Plan", "Migration plan", "Acceptance criteria"}

    if not note_root.exists():
        return findings

    for lifecycle, expected_status in statuses.items():
        lifecycle_root = note_root / lifecycle
        if not lifecycle_root.exists():
            continue
        for path in sorted(lifecycle_root.rglob("*.md")):
            if path.name in {"README.md", "_template.md"} or path.name.endswith(".zh.md"):
                continue
            rel = path.relative_to(root).as_posix()
            text = path.read_text(encoding="utf-8")
            status_match = re.search(r"(?m)^Status:\s*(.+?)\s*$", text)
            actual = status_match.group(1) if status_match else ""
            status_ok = actual == expected_status
            if lifecycle == "rejected":
                status_ok = actual == "rejected" or actual.startswith("rejected —") or actual.startswith("rejected -")
            if not status_ok:
                findings.append(_finding(
                    "agent-note-status-mismatch",
                    "error",
                    rel,
                    f"Folder {lifecycle!r} requires Status: {expected_status!r}; found {actual!r}.",
                ))

            headings = set(re.findall(r"(?m)^##\s+(.+?)\s*$", text))
            for heading in sorted(required.get(lifecycle, set()) - headings):
                findings.append(_finding(
                    "agent-note-required-heading-missing",
                    "error",
                    rel,
                    f"Agent Note in {lifecycle}/ is missing required heading: ## {heading}",
                ))
            if lifecycle in {"implemented", "archived"}:
                for heading in sorted(headings & forbidden_implemented):
                    findings.append(_finding(
                        "agent-note-forbidden-heading",
                        "error",
                        rel,
                        f"Implemented Agent Notes may not contain proposal-stage heading: ## {heading}",
                    ))
    return findings


def _budget_findings(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for rel, rule in (config.get("budgets") or {}).items():
        path = root / rel
        if not path.is_file():
            continue
        metric = (rule or {}).get("metric", "unicode_chars")
        maximum = (rule or {}).get("max")
        if metric != "unicode_chars" or not isinstance(maximum, int):
            findings.append(_finding(
                "document-budget-invalid",
                "error",
                rel,
                "Budgets must use metric 'unicode_chars' and an integer max.",
            ))
            continue
        count = len(path.read_text(encoding="utf-8"))
        if count > maximum:
            findings.append(_finding(
                "document-budget-exceeded",
                "error",
                rel,
                f"Document has {count} Unicode characters; maximum is {maximum}.",
                actual=count,
                maximum=maximum,
            ))
    return findings


def verify_repository(repo: str | os.PathLike[str] | Path) -> dict[str, Any]:
    root = _normalize_repo(repo)
    config, findings = _load_governance(root)
    if config is None:
        return {"ok": False, "findings": findings, "summary": {"errors": len(findings), "warnings": 0}}

    for name, rel in (config.get("authority") or {}).items():
        if rel is None:
            continue
        path = root / str(rel)
        if not path.exists():
            findings.append(_finding(
                "authority-missing",
                "error",
                str(rel),
                f"Authority {name!r} points to a missing path.",
                authority=name,
            ))

    exclude_patterns = list(config.get("exclude") or [])
    files = _relative_files(root, exclude_patterns)
    current_patterns = list((config.get("tiers") or {}).get("current") or [])
    historical_patterns = list((config.get("tiers") or {}).get("historical") or [])
    overlap = sorted(
        rel
        for rel in files
        if any(_matches(rel, p) for p in current_patterns)
        and any(_matches(rel, p) for p in historical_patterns)
    )
    for rel in overlap:
        findings.append(_finding(
            "tier-overlap",
            "error",
            rel,
            "A file may not belong to both current and historical tiers.",
        ))

    findings.extend(_markdown_link_findings(root, exclude_patterns))
    findings.extend(_agent_note_findings(root, config))
    findings.extend(_budget_findings(root, config))
    findings.sort(key=lambda item: (item["severity"], item["code"], item["path"], item["message"]))
    errors = sum(1 for finding in findings if finding["severity"] == "error")
    warnings = sum(1 for finding in findings if finding["severity"] != "error")
    return {"ok": errors == 0, "findings": findings, "summary": {"errors": errors, "warnings": warnings}}


def _current_markdown_files(root: Path, config: dict[str, Any]) -> list[Path]:
    patterns = list((config.get("tiers") or {}).get("current") or [])
    exclude_patterns = list(config.get("exclude") or [])
    return [
        root / rel
        for rel in _relative_files(root, exclude_patterns)
        if rel.endswith(".md") and any(_matches(rel, pattern) for pattern in patterns)
    ]


def audit_repository(repo: str | os.PathLike[str] | Path) -> dict[str, Any]:
    root = _normalize_repo(repo)
    verified = verify_repository(root)
    findings = list(verified["findings"])
    config, config_findings = _load_governance(root)
    if config is None:
        return verified
    findings.extend(config_findings)

    audit = config.get("audit") or {}
    minimum = int(audit.get("duplicate_min_chars", 180))
    occurrences: dict[str, list[str]] = {}
    for path in _current_markdown_files(root, config):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for paragraph in re.split(r"\n\s*\n", text):
            normalized = " ".join(paragraph.split())
            if len(normalized) < minimum or normalized.startswith("#") or normalized.startswith("```"):
                continue
            occurrences.setdefault(normalized, []).append(rel)
    for paragraph, paths in sorted(occurrences.items()):
        unique_paths = sorted(set(paths))
        if len(unique_paths) > 1:
            findings.append(_finding(
                "duplicate-prose",
                "warning",
                unique_paths[0],
                "A long prose block is duplicated across current documentation owners.",
                paths=unique_paths,
                excerpt=paragraph[:160],
            ))

    historical_patterns = list((config.get("tiers") or {}).get("historical") or [])
    historical_prefixes = sorted({pattern[:-3].rstrip("/") if pattern.endswith("/**") else pattern for pattern in historical_patterns})
    terms = [str(term).lower() for term in audit.get("historical_authority_terms", [])]
    for path in _current_markdown_files(root, config):
        rel = path.relative_to(root).as_posix()
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            lowered = line.lower()
            if terms and any(term in lowered for term in terms) and any(prefix in line for prefix in historical_prefixes):
                findings.append(_finding(
                    "historical-authority-leak",
                    "warning",
                    rel,
                    f"Line {line_no} names a historical tier as current authority.",
                    line=line_no,
                ))

    findings.sort(key=lambda item: (item["severity"], item["code"], item["path"], item["message"]))
    errors = sum(1 for finding in findings if finding["severity"] == "error")
    warnings = sum(1 for finding in findings if finding["severity"] != "error")
    return {"ok": errors == 0, "findings": findings, "summary": {"errors": errors, "warnings": warnings}}


def impact_repository(
    repo: str | os.PathLike[str] | Path,
    *,
    base: str,
    head: str = "HEAD",
) -> dict[str, Any]:
    root = _normalize_repo(repo)
    config, findings = _load_governance(root)
    if config is None:
        return {"ok": False, "changed_files": [], "findings": findings}
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only", f"{base}...{head}"],
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        message = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        findings.append(_finding("git-diff-failed", "error", ".", f"Unable to compute Git diff: {message}"))
        return {"ok": False, "changed_files": [], "findings": findings}

    changed = sorted(line.strip().replace(os.sep, "/") for line in completed.stdout.splitlines() if line.strip())
    for mapping in config.get("impact_mappings") or []:
        code_patterns = list(mapping.get("code") or [])
        doc_patterns = list(mapping.get("docs") or [])
        code_changed = sorted(path for path in changed if any(_matches(path, pattern) for pattern in code_patterns))
        if not code_changed:
            continue
        docs_changed = sorted(path for path in changed if any(_matches(path, pattern) for pattern in doc_patterns))
        if docs_changed:
            continue
        level = str(mapping.get("level") or "soft")
        severity = "error" if level == "hard" else "warning"
        code = "hard-doc-impact-missing" if level == "hard" else "soft-doc-impact-unreviewed"
        findings.append(_finding(
            code,
            severity,
            str(mapping.get("name") or "unnamed-mapping"),
            "Mapped code changed without any owning documentation changing.",
            changed_code=code_changed,
            expected_docs=doc_patterns,
        ))

    findings.sort(key=lambda item: (item["severity"], item["code"], item["path"], item["message"]))
    return {
        "ok": not any(finding["severity"] == "error" for finding in findings),
        "changed_files": changed,
        "findings": findings,
    }

def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        if isinstance(value, list):
            print(f"{key}:")
            for item in value:
                print(f"  - {item}")
        else:
            print(f"{key}: {value}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repository documentation governance helper")
    parser.add_argument("--version", action="version", version=VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="inventory a repository")
    inspect_parser.add_argument("--repo", required=True)
    inspect_parser.add_argument("--json", action="store_true")

    plan_parser = subparsers.add_parser("plan", help="create a migration/bootstrap plan")
    plan_parser.add_argument("--repo", required=True)
    plan_parser.add_argument("--profile", default="small-web-app")
    plan_parser.add_argument("--output")
    plan_parser.add_argument("--json", action="store_true")

    bootstrap_parser = subparsers.add_parser("bootstrap", help="install missing governance assets")
    bootstrap_parser.add_argument("--repo", required=True)
    bootstrap_parser.add_argument("--profile", default="small-web-app")
    bootstrap_parser.add_argument("--dry-run", action="store_true")
    bootstrap_parser.add_argument("--force", action="store_true")
    bootstrap_parser.add_argument("--json", action="store_true")

    verify_parser = subparsers.add_parser("verify", help="run deterministic governance checks")
    verify_parser.add_argument("--repo", required=True)
    verify_parser.add_argument("--json", action="store_true")

    audit_parser = subparsers.add_parser("audit", help="run deterministic and corpus audit checks")
    audit_parser.add_argument("--repo", required=True)
    audit_parser.add_argument("--json", action="store_true")

    impact_parser = subparsers.add_parser("impact", help="check code-to-doc impact mappings for a Git diff")
    impact_parser.add_argument("--repo", required=True)
    impact_parser.add_argument("--base", required=True)
    impact_parser.add_argument("--head", default="HEAD")
    impact_parser.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            payload = inspect_repository(args.repo)
        elif args.command == "plan":
            payload = build_plan(args.repo, profile=args.profile)
            if args.output:
                output = Path(args.output).expanduser().resolve()
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        elif args.command == "bootstrap":
            payload = bootstrap_repository(
                args.repo,
                profile=args.profile,
                dry_run=args.dry_run,
                force=args.force,
            )
        elif args.command == "verify":
            payload = verify_repository(args.repo)
        elif args.command == "audit":
            payload = audit_repository(args.repo)
        elif args.command == "impact":
            payload = impact_repository(args.repo, base=args.base, head=args.head)
        else:  # pragma: no cover - argparse enforces this
            parser.error(f"unsupported command: {args.command}")
            return 2
    except (FileNotFoundError, NotADirectoryError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _emit(payload, getattr(args, "json", False))
    if args.command in {"verify", "audit", "impact"} and payload.get("ok") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
