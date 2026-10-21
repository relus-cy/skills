from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "dsh-doc-audits"


class SkillStructureTests(unittest.TestCase):
    def test_skill_directory_and_frontmatter_match(self) -> None:
        path = SKILL / "SKILL.md"
        self.assertTrue(path.is_file(), f"missing {path.relative_to(ROOT)}")
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match, "SKILL.md must start with YAML frontmatter")
        frontmatter = match.group(1)
        self.assertRegex(frontmatter, r"(?m)^name:\s*dsh-doc-audits\s*$")
        description = re.search(r"(?m)^description:\s*(.+)$", frontmatter)
        self.assertIsNotNone(description)
        self.assertTrue(description.group(1).startswith("Use when "))
        self.assertLessEqual(len(description.group(1)), 1024)

    def test_skill_has_progressive_disclosure_directories(self) -> None:
        self.assertTrue((SKILL / "scripts").is_dir())
        self.assertTrue((SKILL / "references").is_dir())
        self.assertTrue((SKILL / "assets").is_dir())

    def test_skill_references_are_one_hop_from_skill_md(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        refs = re.findall(r"\]\((references/[^)#]+)", text)
        self.assertGreaterEqual(len(refs), 4)
        for ref in refs:
            self.assertTrue((SKILL / ref).is_file(), f"missing referenced file: {ref}")
            self.assertNotIn("/references/", ref)

    def test_openai_metadata_is_present(self) -> None:
        metadata = SKILL / "agents" / "openai.yaml"
        self.assertTrue(metadata.is_file())
        text = metadata.read_text(encoding="utf-8")
        self.assertIn('display_name: "DSH Doc Audits"', text)
        self.assertIn("$dsh-doc-audits", text)

    def test_version_is_consistent_across_release_surfaces(self) -> None:
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        cli = (SKILL / "scripts" / "repo_docs.py").read_text(encoding="utf-8")
        guard = (SKILL / "scripts" / "workflow_guard.py").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        governance = (ROOT / "docs" / "governance.yaml").read_text(encoding="utf-8")

        self.assertRegex(skill, r'(?m)^  version: "0\.5\.0"$')
        self.assertRegex(cli, r'(?m)^VERSION = "0\.5\.0"$')
        self.assertRegex(guard, r"(?m)^VERSION = '0\.5\.0'$")
        self.assertIn("## dsh-doc-audits 0.5.0", changelog)
        self.assertIn('"skill_version": "0.5.0"', governance)

    def test_installed_bundle_carries_license_and_attribution(self) -> None:
        self.assertIn("MIT License", (SKILL / "LICENSE").read_text(encoding="utf-8"))
        notices = (SKILL / "NOTICE.md").read_text(encoding="utf-8")
        self.assertIn("DeepSeek Harness", notices)
        self.assertIn("MIT License", notices)


if __name__ == "__main__":
    unittest.main()
