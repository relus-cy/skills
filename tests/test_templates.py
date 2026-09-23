from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "dsh-doc-audits"
ASSETS = SKILL / "assets" / "repo-governance"
MODULE_PATH = SKILL / "scripts" / "repo_docs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("repo_docs_templates", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load repo_docs module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TemplateTests(unittest.TestCase):
    def test_asset_tree_contains_complete_repository_contract(self) -> None:
        expected = {
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
        }
        actual = {
            path.relative_to(ASSETS).as_posix()
            for path in ASSETS.rglob("*")
            if path.is_file()
        }
        self.assertTrue(expected.issubset(actual), sorted(expected - actual))

    def test_governance_template_is_json_compatible_after_render(self) -> None:
        text = (ASSETS / "docs" / "governance.yaml").read_text(encoding="utf-8")
        rendered = (
            text.replace("{{PROJECT_NAME}}", "demo")
            .replace("{{DATE}}", "2026-09-23")
            .replace("{{SKILL_VERSION}}", "0.1.0")
            .replace("{{PROFILE}}", "small-web-app")
        )
        data = json.loads(rendered)
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["profile"], "small-web-app")
        self.assertIn("authority", data)
        self.assertIn("impact_mappings", data)

    def test_bootstrapped_repository_runs_its_local_verifier(self) -> None:
        repo_docs = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            result = repo_docs.bootstrap_repository(repo, profile="small-web-app")
            self.assertIn("scripts/verify_docs.py", result["created"])

            completed = subprocess.run(
                ["python", str(repo / "scripts" / "verify_docs.py"), "--repo", str(repo), "--json"],
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"], payload)

    def test_bootstrapped_local_verifier_honors_manifest_exclusions(self) -> None:
        repo_docs = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            repo_docs.bootstrap_repository(repo, profile="small-web-app")
            fixture = repo / "tests" / "fixtures" / "drifted" / "README.md"
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_text("# Drifted\n\n[missing](docs/missing.md)\n", encoding="utf-8")

            completed = subprocess.run(
                ["python", str(repo / "scripts" / "verify_docs.py"), "--repo", str(repo), "--json"],
                text=True,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"], payload)

    def test_bootstrapped_local_verifier_reports_non_object_manifest_cleanly(self) -> None:
        repo_docs = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            repo_docs.bootstrap_repository(repo, profile="small-web-app")
            (repo / "docs" / "governance.yaml").write_text("[]\n", encoding="utf-8")

            completed = subprocess.run(
                ["python", str(repo / "scripts" / "verify_docs.py"), "--repo", str(repo), "--json"],
                text=True,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 1, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertIn("governance-invalid", {finding["code"] for finding in payload["findings"]})
            self.assertNotIn("Traceback", completed.stderr)

    def test_bootstrapped_local_verifier_reports_corpus_audit_warnings(self) -> None:
        repo_docs = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            repo_docs.bootstrap_repository(repo, profile="small-web-app")
            paragraph = (
                "This durable operational contract is intentionally repeated so the repository-local "
                "verifier can detect duplicated current-state prose across two documentation owners. " * 2
            )
            (repo / "docs" / "architecture.md").write_text(
                "# Architecture\n\n" + paragraph +
                "\n\nThe current authority is docs/superpowers/plans/old.md.\n",
                encoding="utf-8",
            )
            subsystem = repo / "docs" / "subsystems" / "example.md"
            subsystem.write_text("# Example\n\n" + paragraph + "\n", encoding="utf-8")
            historical = repo / "docs" / "superpowers" / "plans" / "old.md"
            historical.parent.mkdir(parents=True, exist_ok=True)
            historical.write_text("# Old plan\n", encoding="utf-8")

            completed = subprocess.run(
                ["python", str(repo / "scripts" / "verify_docs.py"), "--repo", str(repo), "--json"],
                text=True,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            codes = {finding["code"] for finding in payload["findings"]}
            self.assertIn("duplicate-prose", codes)
            self.assertIn("historical-authority-leak", codes)

    def test_references_have_no_deep_reference_chain(self) -> None:
        for path in sorted((SKILL / "references").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\]\(references/", path.name)
            self.assertNotRegex(text, r"\]\([^)]*/references/", path.name)

    def test_repository_local_verifier_matches_rendered_asset(self) -> None:
        template = (ASSETS / "scripts" / "verify_docs.py").read_text(encoding="utf-8")
        expected = template.replace("{{SKILL_VERSION}}", "0.1.0")
        actual = (ROOT / "scripts" / "verify_docs.py").read_text(encoding="utf-8")
        self.assertEqual(actual, expected)

    def test_skill_body_stays_under_recommended_line_limit(self) -> None:
        line_count = len((SKILL / "SKILL.md").read_text(encoding="utf-8").splitlines())
        self.assertLess(line_count, 500)


if __name__ == "__main__":
    unittest.main()
