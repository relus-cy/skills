"""Readiness regressions: file existence must not certify a semantic migration."""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from test_verification import load_module, create_valid_repo, write, manifest


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mod = load_module()
        create_valid_repo(self.root)

    def codes(self):
        return {f['code'] for f in self.mod.verify_repository(self.root)['findings']}

    def test_empty_manifest_is_rejected(self):
        write(self.root / 'docs/governance.yaml', '{}')
        self.assertIn('governance-invalid', self.codes())

    def test_invalid_manifest_types_fail_cleanly(self):
        for key, value in [('authority', []), ('tiers', []), ('impact_mappings', {}),
                           ('budgets', {'x': None}), ('audit', {'duplicate_min_chars': 'many'})]:
            with self.subTest(key=key):
                write(self.root / 'docs/governance.yaml', json.dumps(manifest(**{key: value})))
                self.assertIn('governance-invalid', self.codes())

    def test_current_authority_with_template_prompt_is_rejected(self):
        write(self.root / 'docs/architecture.md',
              '# Architecture\n\nStatus: current authority\n\nDescribe components here.\n')
        self.assertIn('current-authority-placeholder', self.codes())

    def test_current_authority_with_tbd_is_rejected(self):
        write(self.root / 'docs/architecture.md',
              '# Architecture\n\nStatus: current authority\n\nTBD — deployment.\n')
        self.assertIn('current-authority-placeholder', self.codes())

    def test_fenced_examples_and_quoted_history_are_not_placeholders(self):
        write(self.root / 'docs/architecture.md', '# Architecture\n\nStatus: current authority\n'
              '\nTasks use the enum `TODO` for pending work.\n\n```python\nTODO = 1\n```\n'
              '\n> TBD — original historical quote.\n')
        self.assertNotIn('current-authority-placeholder', self.codes())

    def test_scaffold_is_warning_until_completion(self):
        write(self.root / 'docs/architecture.md', '# Architecture\n\nStatus: scaffold\n\nDescribe components here.\n')
        normal = self.mod.verify_repository(self.root)
        self.assertTrue(normal['ok'], normal)
        self.assertIn('documentation-scaffold', {f['code'] for f in normal['findings']})
        self.assertTrue(hasattr(self.mod, 'verify_repository'))
        complete = self.mod.verify_repository(self.root, completion=True)
        self.assertFalse(complete['ok'])

    def test_completion_rejects_heading_only_owner(self):
        result = self.mod.verify_repository(self.root, completion=True)
        self.assertFalse(result['ok'])
        self.assertIn('current-authority-empty', {f['code'] for f in result['findings']})

    def test_generated_scaffold_never_claims_current_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.mod.bootstrap_repository(root)
            skeleton = Path(self.mod.SKILL_ROOT) / 'assets/skeletons/docs/architecture.md'
            for text in ((root / 'README.md').read_text(), skeleton.read_text()):
                self.assertIn('Status: scaffold', text)
                self.assertNotIn('Status: current authority', text)

    def test_standalone_rejects_empty_manifest(self):
        self.mod.bootstrap_repository(self.root)
        write(self.root / 'docs/governance.yaml', '{}')
        result = subprocess.run([sys.executable, str(self.root / 'scripts/verify_docs.py'),
                                 '--repo', str(self.root), '--json'], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('governance-invalid', {f['code'] for f in json.loads(result.stdout)['findings']})

    def test_force_cannot_overwrite_project_owned_docs(self):
        self.mod.bootstrap_repository(self.root)
        before = (self.root / 'README.md').read_bytes()
        with self.assertRaises(ValueError):
            self.mod.bootstrap_repository(self.root, force=True)
        self.assertEqual((self.root / 'README.md').read_bytes(), before)

    def test_manifest_with_invalid_extra_tier_fails_cleanly(self):
        data=manifest(); data['tiers']['unexpected']=None
        write(self.root/'docs/governance.yaml',json.dumps(data))
        self.assertIn('governance-invalid',self.codes())

    def test_bootstrap_rejects_symlink_target_before_any_write(self):
        external=Path(self.temp.name)/'outside'; external.mkdir()
        link=self.root/'scripts'; link.symlink_to(external,target_is_directory=True)
        before=(self.root/'README.md').read_bytes()
        with self.assertRaises(ValueError): self.mod.bootstrap_repository(self.root)
        self.assertEqual(list(external.iterdir()),[])
        self.assertEqual((self.root/'README.md').read_bytes(),before)

    def test_copied_subsystem_template_is_still_scaffold(self):
        template=Path(self.mod.SKILL_ROOT)/'assets/skeletons/docs/subsystems/_template.md'
        write(self.root/'docs/subsystems/copied.md',template.read_text())
        self.assertIn('documentation-scaffold',self.codes())

    def test_bullet_placeholder_blocks_current_authority(self):
        write(self.root/'docs/architecture.md','# Architecture\n\nStatus: current authority\n\n- TODO: describe deployment.\n')
        self.assertIn('current-authority-placeholder',self.codes())
