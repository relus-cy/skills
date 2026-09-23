from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "dsh-doc-audits" / "scripts" / "repo_docs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("repo_docs_verify", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load repo_docs module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def manifest(**overrides):
    value = {
        "schema_version": 1,
        "authority": {
            "architecture": "docs/architecture.md",
            "backlog": "docs/backlog.md",
        },
        "tiers": {
            "current": ["README.md", "AGENTS.md", "docs/architecture.md", "docs/backlog.md", "docs/subsystems/**"],
            "historical": ["docs/superpowers/**", ".agents/notes/archived/**"],
        },
        "agent_notes": {
            "root": ".agents/notes",
            "statuses": {
                "proposed": "proposed",
                "implemented": "implemented",
                "rejected": "rejected",
                "archived": "implemented",
            },
        },
        "budgets": {
            "AGENTS.md": {"metric": "unicode_chars", "max": 2000},
            "docs/architecture.md": {"metric": "unicode_chars", "max": 4000},
        },
        "impact_mappings": [
            {
                "name": "backend-api",
                "code": ["api/**", "engine/**"],
                "docs": ["docs/subsystems/api.md", "docs/reference/api.md"],
                "level": "hard",
            }
        ],
        "audit": {
            "duplicate_min_chars": 120,
            "historical_authority_terms": ["current authority", "source of truth", "唯一权威", "权威文档"],
        },
    }
    value.update(overrides)
    return value


def create_valid_repo(repo: Path) -> None:
    write(repo / "README.md", "# Demo\n\nSee [architecture](docs/architecture.md).\n")
    write(repo / "AGENTS.md", "# Rules\n")
    write(repo / "docs" / "architecture.md", "# Architecture\n")
    write(repo / "docs" / "backlog.md", "# Backlog\n")
    write(repo / "docs" / "subsystems" / "api.md", "# API subsystem\n")
    write(repo / "docs" / "reference" / "api.md", "# API reference\n")
    write(repo / "docs" / "governance.yaml", json.dumps(manifest(), ensure_ascii=False, indent=2) + "\n")
    write(repo / ".agents" / "notes" / "README.md", "# Agent Notes\n")


class VerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_docs = load_module()

    def test_verify_accepts_valid_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            create_valid_repo(repo)

            result = self.repo_docs.verify_repository(repo)

            self.assertTrue(result["ok"], result["findings"])
            self.assertEqual(result["findings"], [])

    def test_verify_accepts_encoded_space_anchor_and_external_links(self) -> None:
        with tempfile.TemporaryDirectory(prefix="docs audit 中文 ") as tmp:
            repo = Path(tmp)
            create_valid_repo(repo)
            write(repo / "docs" / "Some File.md", "# Heading\n")
            write(
                repo / "README.md",
                "# Demo\n\n[local](#demo) [encoded](docs/Some%20File.md#heading) "
                "[external](https://example.com/docs).\n",
            )

            result = self.repo_docs.verify_repository(repo)

            self.assertTrue(result["ok"], result["findings"])

    def test_verify_reports_missing_authority_and_broken_relative_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            create_valid_repo(repo)
            (repo / "docs" / "architecture.md").unlink()
            write(repo / "README.md", "# Demo\n\nSee [missing](docs/missing.md).\n")

            result = self.repo_docs.verify_repository(repo)
            codes = {finding["code"] for finding in result["findings"]}

            self.assertFalse(result["ok"])
            self.assertIn("authority-missing", codes)
            self.assertIn("markdown-link-broken", codes)

    def test_verify_rejects_agent_note_status_and_implemented_spec_speak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            create_valid_repo(repo)
            write(
                repo / ".agents" / "notes" / "implemented" / "architecture" / "2026-09-23-example.md",
                "# Agent Note: Example\n\nStatus: proposed\n\n## Problem\nX\n\n## Proposal\nY\n\n"
                "## Alternatives considered\nZ\n\n## Acceptance criteria\nA\n\n## Consequences\nC\n",
            )

            result = self.repo_docs.verify_repository(repo)
            codes = {finding["code"] for finding in result["findings"]}

            self.assertIn("agent-note-status-mismatch", codes)
            self.assertIn("agent-note-forbidden-heading", codes)
            self.assertIn("agent-note-required-heading-missing", codes)

    def test_verify_enforces_unicode_character_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            create_valid_repo(repo)
            data = manifest()
            data["budgets"]["AGENTS.md"]["max"] = 5
            write(repo / "docs" / "governance.yaml", json.dumps(data, ensure_ascii=False))

            result = self.repo_docs.verify_repository(repo)

            self.assertIn("document-budget-exceeded", {f["code"] for f in result["findings"]})

    def test_verify_ignores_markdown_under_manifest_exclusions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            create_valid_repo(repo)
            data = manifest()
            data["exclude"] = ["tests/fixtures/**"]
            write(repo / "docs" / "governance.yaml", json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            write(repo / "tests" / "fixtures" / "drifted" / "README.md", "# Drifted\n\n[missing](docs/missing.md)\n")

            result = self.repo_docs.verify_repository(repo)

            self.assertTrue(result["ok"], result["findings"])
            self.assertNotIn("markdown-link-broken", {f["code"] for f in result["findings"]})


class AuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_docs = load_module()

    def test_audit_reports_duplicate_long_paragraphs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            create_valid_repo(repo)
            paragraph = "This durable operational contract is intentionally repeated to prove that corpus auditing detects duplicated prose across current owners. " * 2
            write(repo / "docs" / "architecture.md", f"# Architecture\n\n{paragraph}\n")
            write(repo / "docs" / "subsystems" / "api.md", f"# API\n\n{paragraph}\n")

            result = self.repo_docs.audit_repository(repo)

            self.assertIn("duplicate-prose", {f["code"] for f in result["findings"]})

    def test_audit_reports_historical_document_named_as_current_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            create_valid_repo(repo)
            write(repo / "docs" / "superpowers" / "plans" / "old.md", "# Old\n")
            write(
                repo / "docs" / "architecture.md",
                "# Architecture\n\nThe current authority is docs/superpowers/plans/old.md.\n",
            )

            result = self.repo_docs.audit_repository(repo)

            self.assertIn("historical-authority-leak", {f["code"] for f in result["findings"]})


class ImpactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_docs = load_module()

    def _git(self, repo: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            text=True,
            capture_output=True,
        )
        return completed.stdout.strip()

    def test_hard_mapping_fails_when_code_changes_without_owner_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            create_valid_repo(repo)
            self._git(repo, "init", "-b", "main")
            self._git(repo, "config", "user.name", "Test")
            self._git(repo, "config", "user.email", "test@example.com")
            write(repo / "api" / "main.py", "VALUE = 1\n")
            self._git(repo, "add", ".")
            self._git(repo, "commit", "-m", "base")
            base = self._git(repo, "rev-parse", "HEAD")
            write(repo / "api" / "main.py", "VALUE = 2\n")
            self._git(repo, "add", ".")
            self._git(repo, "commit", "-m", "change code")

            result = self.repo_docs.impact_repository(repo, base=base)

            self.assertFalse(result["ok"])
            self.assertIn("hard-doc-impact-missing", {f["code"] for f in result["findings"]})

    def test_hard_mapping_passes_when_owner_doc_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            create_valid_repo(repo)
            self._git(repo, "init", "-b", "main")
            self._git(repo, "config", "user.name", "Test")
            self._git(repo, "config", "user.email", "test@example.com")
            write(repo / "api" / "main.py", "VALUE = 1\n")
            self._git(repo, "add", ".")
            self._git(repo, "commit", "-m", "base")
            base = self._git(repo, "rev-parse", "HEAD")
            write(repo / "api" / "main.py", "VALUE = 2\n")
            write(repo / "docs" / "subsystems" / "api.md", "# API subsystem\n\nVALUE changed.\n")
            self._git(repo, "add", ".")
            self._git(repo, "commit", "-m", "change code and docs")

            result = self.repo_docs.impact_repository(repo, base=base)

            self.assertTrue(result["ok"], result["findings"])


if __name__ == "__main__":
    unittest.main()
