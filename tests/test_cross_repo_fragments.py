"""User-facing regressions for committed impact ranges and local section links."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_verification import create_valid_repo, write, manifest

ROOT = Path(__file__).resolve().parents[1]

class GovernanceCLIRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'docs'
        self.code = Path(self.tmp.name) / 'code'
        create_valid_repo(self.repo)
        self.code.mkdir()
        for repo in (self.repo, self.code):
            self.git(repo, 'init', '-q')
            self.git(repo, 'config', 'user.email', 'fixture@example.invalid')
            self.git(repo, 'config', 'user.name', 'Fixture')
        write(self.code / 'api/service.py', 'initial\n')
        config = manifest()
        config['impact_mappings'][0]['code_repository'] = 'external'
        write(self.repo / 'docs/governance.yaml', json.dumps(config))
        self.base = self.commit(self.repo)
        self.code_base = self.commit(self.code)

    def git(self, repo, *args):
        return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()

    def commit(self, repo):
        self.git(repo, 'add', '.')
        self.git(repo, 'commit', '-qm', 'fixture')
        return self.git(repo, 'rev-parse', 'HEAD')

    def cli(self, local=False, impact=False, extra=()):
        command = [sys.executable, str(ROOT / ('scripts/verify_docs.py' if local else 'dsh-doc-audits/scripts/repo_docs.py'))]
        if not local:
            command += ['impact' if impact else 'verify']
        command += ['--repo', str(self.repo), '--json']
        if impact:
            command += ['--base', self.base]
        result = subprocess.run(command + list(extra), text=True, capture_output=True)
        try:
            payload = json.loads(result.stdout)
        except ValueError:
            payload = {'stderr': result.stderr}
        return result.returncode, payload

    def external_args(self):
        return ['--code-repo', str(self.code), '--code-base', self.code_base]

    def test_external_change_requires_private_owner_commit(self):
        write(self.code / 'api/service.py', 'changed\n')
        self.commit(self.code)
        for local in (False, True):
            status, payload = self.cli(local, True, self.external_args())
            self.assertEqual(status, 1, payload)
            self.assertEqual([f['code'] for f in payload['findings']], ['hard-doc-impact-missing'])
        write(self.repo / 'docs/subsystems/api.md', '# API subsystem\nUpdated contract.\n')
        # An uncommitted documentation edit cannot satisfy committed ranges.
        self.assertEqual(self.cli(False, True, self.external_args())[0], 1)
        self.commit(self.repo)
        for local in (False, True):
            self.assertEqual(self.cli(local, True, self.external_args())[0], 0)

    def test_missing_external_context_cannot_pass(self):
        for local in (False, True):
            status, payload = self.cli(local, True)
            self.assertEqual(status, 2, payload)
            self.assertIn('code-repo', payload.get('error', payload.get('stderr', '')))

    def test_non_root_code_directory_and_incomplete_flags_rejected(self):
        for local in (False, True):
            for args in (['--code-repo', str(self.code)], ['--code-head', 'HEAD'],
                         ['--code-repo', str(self.code / 'api'), '--code-base', self.code_base]):
                status, payload = self.cli(local, True, args)
                self.assertEqual(status, 2, payload)
                self.assertIn('error', str(payload).lower())

    def test_independent_heads_and_local_mapping_are_respected(self):
        write(self.code / 'api/service.py', 'changed\n')
        self.commit(self.code)
        args = self.external_args() + ['--code-head', self.code_base, '--head', self.base]
        for local in (False, True):
            self.assertEqual(self.cli(local, True, args)[0], 0)
        config = manifest()
        config['impact_mappings'].append(dict(config['impact_mappings'][0], name='external-api', code_repository='external'))
        write(self.repo / 'docs/governance.yaml', json.dumps(config))
        write(self.repo / 'engine/local.py', 'changed\n')
        self.commit(self.repo)
        status, payload = self.cli(False, True, self.external_args() + ['--code-head', self.code_base])
        self.assertEqual(status, 1, payload)
        self.assertEqual([(f['path'], f['changed_code']) for f in payload['findings']], [('backend-api', ['engine/local.py'])])

    def test_inline_code_underscores_are_literal(self):
        write(self.repo / 'README.md', '# Demo\n## `get_bars_bundle`\n[api](#get_bars_bundle)\n`<a id="fake">`\n')
        for local in (False, True):
            status, payload = self.cli(local)
            self.assertEqual(status, 0, payload)
    def test_inline_html_examples_are_not_anchors(self):
        write(self.repo / 'README.md', '# Demo\n`<a id="fake">`\n[invalid](#fake)\n')
        for local in (False, True):
            status, payload = self.cli(local)
            self.assertEqual(status, 1, payload)
            self.assertEqual([f['code'] for f in payload['findings']], ['markdown-fragment-broken'])

    def test_html_comments_and_data_attributes_are_not_anchors(self):
        for markup in ('<!-- <a id="fake"> -->', '<!--\n<a id="fake">\n-->', '<a data-id="fake"></a>'):
            write(self.repo / 'README.md', markup + '\n[bad](#fake)\n')
            for local in (False, True):
                with self.subTest(markup=markup, local=local):
                    status, payload = self.cli(local)
                    self.assertEqual(status, 1, payload)
                    self.assertEqual([f['code'] for f in payload['findings']], ['markdown-fragment-broken'])

    def test_blockquoted_heading_is_a_link_target(self):
        write(self.repo / 'README.md', '> # Quote\n[ok](#quote)\n> > ## Nested\n[ok](#nested)\n')
        for local in (False, True):
            status, payload = self.cli(local)
            self.assertEqual(status, 0, payload)

    def test_documentation_subdirectory_is_an_input_error_without_manifest(self):
        for local in (False, True):
            status, payload = self.cli(local, True, self.external_args() + ['--repo', str(self.repo / 'docs')])
            self.assertEqual(status, 2, payload)
            self.assertIn('Git worktree root', str(payload))

    def test_invalid_code_repository_types_are_manifest_findings(self):
        for value in ([], {}, 'unknown'):
            config = manifest()
            config['impact_mappings'][0]['code_repository'] = value
            write(self.repo / 'docs/governance.yaml', json.dumps(config))
            for local in (False, True):
                with self.subTest(value=value, local=local):
                    status, payload = self.cli(local)
                    self.assertEqual(status, 1, payload)
                    self.assertEqual([f['code'] for f in payload['findings']], ['governance-invalid'])

    def test_thematic_break_does_not_turn_blocks_into_setext_headings(self):
        for block, anchor in (('- Alpha', '--alpha'), ('# Alpha', 'alpha-1'), ('<div>Alpha</div>', 'alpha')):
            write(self.repo / 'README.md', block + '\n---\n[bad](#' + anchor + ')\n')
            for local in (False, True):
                with self.subTest(block=block, local=local):
                    status, payload = self.cli(local)
                    self.assertEqual(status, 1, payload)
                    self.assertEqual([f['code'] for f in payload['findings']], ['markdown-fragment-broken'])

    def test_heading_fragments_and_explicit_anchors(self):
        write(self.repo / 'docs/reference/sections.md', '# 中文 `API`：Hello, world!\n# Repeat\n# Repeat\nSetext title\n---\n<a id="custom-id"></a>\n<a name="legacy"></a>\n```md\n# Ghost\n```\n')
        write(self.repo / 'README.md', '# Demo\n[local](#demo) [中文](docs/reference/sections.md#中文-apihello-world) [duplicate](docs/reference/sections.md#repeat-1) [setext](docs/reference/sections.md#setext-title) [id](docs/reference/sections.md#custom-id) [name](docs/reference/sections.md#legacy)\n')
        for local in (False, True):
            self.assertEqual(self.cli(local)[0], 0)
        write(self.repo / 'README.md', '# Demo\n[bad](#missing) [code](docs/reference/sections.md#ghost)\n')
        write(self.repo / 'docs/superpowers/old.md', '[old](../reference/sections.md#missing)\n')
        for local in (False, True):
            status, payload = self.cli(local)
            self.assertEqual(status, 1, payload)
            self.assertEqual(sorted((f['code'], f['severity']) for f in payload['findings']), [('markdown-fragment-broken', 'error'), ('markdown-fragment-broken', 'error'), ('markdown-fragment-broken', 'warning')])

if __name__ == '__main__':
    unittest.main()
