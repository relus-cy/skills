from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "dsh-doc-audits"
MODULE_PATH = SKILL / "scripts" / "repo_docs.py"
FIXTURES = ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("repo_docs_integration", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load repo_docs module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_fixture(name: str, target: Path) -> None:
    shutil.copytree(FIXTURES / name, target, dirs_exist_ok=True)


class ScenarioFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_docs = load_module()

    def test_all_named_scenario_fixtures_exist(self) -> None:
        for name in ("greenfield", "brownfield", "drifted", "existing-docs", "no-doc-impact"):
            self.assertTrue((FIXTURES / name).is_dir(), name)

    def test_brownfield_fixture_produces_migration_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            copy_fixture("brownfield", repo)

            plan = self.repo_docs.build_plan(repo, profile="small-web-app")

            self.assertEqual(plan["mode"], "migrate")
            self.assertIn("python", plan["inventory"]["stack_signals"])
            self.assertIn("docs/superpowers", plan["historical_surfaces"])

    def test_existing_docs_fixture_is_preserved_by_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            copy_fixture("existing-docs", repo)
            before_readme = (repo / "README.md").read_text(encoding="utf-8")
            before_agents = (repo / "AGENTS.md").read_text(encoding="utf-8")

            result = self.repo_docs.bootstrap_repository(repo)

            self.assertEqual((repo / "README.md").read_text(encoding="utf-8"), before_readme)
            self.assertEqual((repo / "AGENTS.md").read_text(encoding="utf-8"), before_agents)
            self.assertIn("README.md", result["preserved"])
            self.assertIn("AGENTS.md", result["preserved"])

    def test_drifted_fixture_reports_broken_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            copy_fixture("drifted", repo)

            result = self.repo_docs.verify_repository(repo)

            self.assertFalse(result["ok"])
            self.assertIn("markdown-link-broken", {item["code"] for item in result["findings"]})

    def test_no_doc_impact_fixture_passes_for_unmapped_test_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            copy_fixture("no-doc-impact", repo)
            subprocess.run(["git", "-C", str(repo), "init", "-b", "main"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, capture_output=True)
            base = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, text=True, capture_output=True).stdout.strip()
            path = repo / "tests" / "test_internal.py"
            path.write_text(path.read_text(encoding="utf-8") + "\n# internal-only change\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "test only"], check=True, capture_output=True)

            result = self.repo_docs.impact_repository(repo, base=base)

            self.assertTrue(result["ok"], result["findings"])
            self.assertEqual(result["findings"], [])


class RepositoryQualityTests(unittest.TestCase):
    def test_no_python_bytecode_is_tracked(self) -> None:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "*.pyc", "__pycache__"],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.stdout.strip(), "")

    def test_ci_and_local_entrypoints_exist(self) -> None:
        self.assertTrue((ROOT / ".github" / "workflows" / "ci.yml").is_file())
        self.assertTrue((ROOT / "scripts" / "verify.sh").is_file())
        self.assertTrue((ROOT / "Makefile").is_file())
        self.assertTrue((ROOT / "pyproject.toml").is_file())


if __name__ == "__main__":
    unittest.main()
