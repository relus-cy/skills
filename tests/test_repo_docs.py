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
    spec = importlib.util.spec_from_file_location("repo_docs", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load repo_docs module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class RepositoryInspectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_docs = load_module()

    def test_inspect_treats_gitkeep_only_repository_as_greenfield(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / ".gitkeep", "")

            result = self.repo_docs.inspect_repository(repo)

            self.assertEqual(result["repository_state"], "greenfield")

    def test_inspect_detects_brownfield_python_web_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "README.md", "# Sample\n")
            write(repo / "requirements.txt", "fastapi\n")
            write(repo / "api" / "main.py", "from fastapi import FastAPI\n")
            write(repo / "docs" / "superpowers" / "plans" / "old.md", "# Old plan\n")

            result = self.repo_docs.inspect_repository(repo)

            self.assertEqual(result["project_name"], repo.name)
            self.assertEqual(result["repository_state"], "brownfield")
            self.assertIn("python", result["stack_signals"])
            self.assertIn("web-api", result["stack_signals"])
            self.assertIn("docs/superpowers", result["historical_surfaces"])

    def test_inspect_does_not_infer_web_stack_from_documentation_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "README.md", "# Notes\n\nThis document compares FastAPI, Flask, React, and Vue.\n")
            write(repo / "docs" / "architecture.md", "# Architecture\n\nNo implementation exists yet.\n")
            write(repo / "tests" / "test_stack.py", "# FastAPI React comparison fixture\n")
            write(repo / "demo-skill" / "SKILL.md", "---\nname: demo-skill\ndescription: Use when testing.\n---\n")
            write(repo / "demo-skill" / "scripts" / "scan.py", "TOKENS = ('FastAPI', 'React')\n")

            result = self.repo_docs.inspect_repository(repo)

            self.assertNotIn("web-api", result["stack_signals"])
            self.assertNotIn("web-ui", result["stack_signals"])

    def test_build_plan_preserves_existing_docs_and_proposes_current_tiers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write(repo / "README.md", "# Existing\n")
            write(repo / "AGENTS.md", "# Existing rules\n")
            write(repo / "src" / "app.py", "print('x')\n")

            plan = self.repo_docs.build_plan(repo, profile="small-web-app")

            self.assertEqual(plan["mode"], "migrate")
            self.assertIn("README.md", plan["preserve"])
            self.assertIn("AGENTS.md", plan["preserve"])
            self.assertIn("docs/architecture.md", plan["create"])
            self.assertIn("docs/subsystems/_template.md", plan["create"])
            self.assertEqual(plan["profile"], "small-web-app")


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_docs = load_module()

    def test_bootstrap_creates_missing_files_and_preserves_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as templates_tmp:
            repo = Path(tmp)
            templates = Path(templates_tmp)
            write(repo / "README.md", "# Keep me\n")
            write(templates / "README.md", "# {{PROJECT_NAME}}\n")
            write(templates / "docs" / "architecture.md", "# {{PROJECT_NAME}} architecture\n")

            result = self.repo_docs.bootstrap_repository(
                repo,
                profile="small-web-app",
                template_root=templates,
            )

            self.assertEqual((repo / "README.md").read_text(encoding="utf-8"), "# Keep me\n")
            self.assertEqual(
                (repo / "docs" / "architecture.md").read_text(encoding="utf-8"),
                f"# {repo.name} architecture\n",
            )
            self.assertIn("docs/architecture.md", result["created"])
            self.assertIn("README.md", result["preserved"])

    def test_bootstrap_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as templates_tmp:
            repo = Path(tmp)
            templates = Path(templates_tmp)
            write(templates / "docs" / "AGENTS.md", "# Rules for {{PROJECT_NAME}}\n")

            first = self.repo_docs.bootstrap_repository(repo, template_root=templates)
            second = self.repo_docs.bootstrap_repository(repo, template_root=templates)

            self.assertEqual(first["created"], ["docs/AGENTS.md"])
            self.assertEqual(second["unchanged"], ["docs/AGENTS.md"])
            self.assertEqual(second["created"], [])

    def test_bootstrap_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as templates_tmp:
            repo = Path(tmp)
            templates = Path(templates_tmp)
            write(templates / "docs" / "architecture.md", "# Architecture\n")

            result = self.repo_docs.bootstrap_repository(repo, template_root=templates, dry_run=True)

            self.assertIn("docs/architecture.md", result["would_create"])
            self.assertFalse((repo / "docs" / "architecture.md").exists())


if __name__ == "__main__":
    unittest.main()
