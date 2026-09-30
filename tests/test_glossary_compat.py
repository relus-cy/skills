"""Filesystem/CLI compatibility checks; reviewer records are fixture attestations only.

Failure modes: missing glossary discovery/preservation; ambiguous default selection;
explicit owner ignored; unsafe configured paths widening writes; linked write targets;
unclassified Matt docs; bootstrap/upgrade overwrites; ADR reader evidence rejected.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from test_reviewed_workflow import load_guard, git, write

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'dsh-doc-audits/scripts/repo_docs.py'
TEMPLATE = ROOT / 'dsh-doc-audits/assets/repo-governance/docs/governance.yaml'


class GlossaryCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        shutil.copytree(ROOT / 'tests/fixtures/matt-layout', self.root)
        self.config = json.loads(TEMPLATE.read_text())
        self.save_config()
        git(self.root, 'init', '-b', 'main')
        git(self.root, 'config', 'user.name', 'Fixture')
        git(self.root, 'config', 'user.email', 'fixture@example.invalid')
        self.commit()

    def save_config(self):
        write(self.root / 'docs/governance.yaml', json.dumps(self.config))

    def commit(self):
        git(self.root, 'add', '.')
        git(self.root, 'commit', '--allow-empty', '-m', 'fixture')

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, str(CLI), *args, '--repo', str(self.root), '--json'], capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout else {"error":result.stderr}

    def inventory_plan(self):
        # Public Python planning helper used by clients; real filesystem, no mocks.
        spec = importlib.util.spec_from_file_location('glossary_repo_docs', CLI)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.build_plan(self.root)

    def prepare(self, rel, *, manifest=None, mode='migrate', move_from=None, code=0):
        proposal = {'author_context_id':'fixture-author', 'authority_candidates':[{
            'id':'terms', 'path':('docs/adr/0001-terms.md' if mode == 'upgrade' else rel), 'tier':'reference', 'responsibility':'Terms',
            'evidence':['README.md'], 'current_sources':[], 'separation_reason':'Terms have their own owner.'}],
            'files':{'create':[], 'edit':[], 'move':[], 'demote_to_historical':[],
                     'preserve':['AGENTS.md', 'docs/adr/0001-terms.md', 'docs/agents/workflow.md']},
            'write_scope':[rel], 'link_repairs':[], 'verification':['Run documentation checks.'],
            'rollback':['Restore reviewed bytes.'], 'open_conflicts':[]}
        category = 'edit' if (self.root / rel).exists() else 'create'
        proposal['files'][category].append({'path':rel, 'content':'# Terms\n\nA term is a shared name.\n', 'reason':'Clarify terms.'})
        if move_from:
            proposal['files'][category] = []
            proposal['files']['move'] = [{'from':move_from, 'to':rel, 'reason':'Relocate the glossary.'}]
            proposal['write_scope'].append(move_from)
        if mode == 'upgrade':
            proposal['files'][category][0]['content'] = (ROOT / 'scripts/verify_docs.py').read_text()
        if manifest is not None:
            proposal['files']['edit'].append({'path':'docs/governance.yaml', 'content':json.dumps(manifest), 'reason':'Declare glossary.'})
            proposal['write_scope'].append('docs/governance.yaml')
        control = self.root / '.dsh-doc-audits'
        control.mkdir(exist_ok=True)
        write(control / '.gitignore', '*\n')
        write(control / 'proposal.json', json.dumps(proposal))
        return self.cli('plan', '--mode', mode, '--proposal', str(control / 'proposal.json'), '--output', str(control / 'plan.json'), code=code)

    def apply(self, plan, *, dry=False):
        control = self.root / '.dsh-doc-audits'
        review = {'schema_version':2, 'content_digest':plan['content_digest'], 'verdict':'approve',
                  'reviewer':{'kind':'human','identity':'fixture-reviewer','context_id':'fixture-reader'},
                  'missing_domains':[], 'over_split_owners':[], 'under_split_owners':[],
                  'authority_conflicts':[], 'required_changes':[], 'summary':'Synthetic fixture attestation, not semantic review.'}
        write(control / 'review.json', json.dumps(review))
        return self.cli('apply', '--plan', str(control / 'plan.json'), '--review', str(control / 'review.json'), '--allow-in-place', *(['--dry-run'] if dry else []))

    def test_default_discovery_preservation_and_legacy(self):
        for name in ['GLOSSARY.md', 'CONTEXT.md']:
            with self.subTest(name=name):
                other = 'CONTEXT.md' if name == 'GLOSSARY.md' else 'GLOSSARY.md'
                (self.root / other).unlink(missing_ok=True)
                write(self.root / name, '# Terms\n\nA stable name.\n')
                self.assertIn(name, self.cli('inspect')['documentation_surfaces'])
                plan = self.inventory_plan()
                self.assertIn(name, plan['preserve'])
                self.assertEqual(plan['authority_suggestions']['terminology'], name)
                self.commit()
                self.apply(self.prepare(name))

    def test_no_manifest_defaults_and_malformed_policy_fail_closed(self):
        (self.root / 'docs/governance.yaml').unlink()
        self.assertIn('GLOSSARY.md', self.cli('inspect')['documentation_surfaces'])
        self.assertEqual(self.inventory_plan()['authority_suggestions']['terminology'], 'GLOSSARY.md')
        write(self.root / 'docs/governance.yaml', 'not JSON')
        self.assertNotIn('GLOSSARY.md', self.cli('inspect')['documentation_surfaces'])
        self.assertIsNone(self.inventory_plan()['authority_suggestions']['terminology'])
        self.cli('verify', code=1)
        self.prepare('GLOSSARY.md', code=2)

    def test_dual_defaults_remain_visible_without_silent_choice(self):
        write(self.root / 'CONTEXT.md', '# Context\n\nExisting domain language.\n')
        plan = self.inventory_plan()
        self.assertTrue({'GLOSSARY.md','CONTEXT.md'} <= set(plan['preserve']))
        self.assertIsNone(plan['authority_suggestions']['terminology'])
        self.assertEqual(plan['authority_suggestions']['terminology_candidates'], ['GLOSSARY.md','CONTEXT.md'])

    def test_explicit_custom_path_and_same_plan_configuration(self):
        for rel in ['LANGUAGE.md', 'knowledge/terms.md']:
            with self.subTest(rel=rel):
                self.config['authority']['glossary'] = rel
                self.config['tiers']['current'].append(rel)
                self.apply(self.prepare(rel, manifest=self.config))
                self.assertIn(rel, self.cli('inspect')['documentation_surfaces'])
                plan = self.inventory_plan()
                self.assertEqual(plan['authority_suggestions']['terminology'], rel)
                self.assertIn(rel, plan['preserve'])
                self.commit()

    def test_glossary_move_repeat_is_already_applied(self):
        self.config['authority']['glossary'] = 'CUSTOM.md'
        self.save_config()
        write(self.root / 'CUSTOM.md', '# Terms\n\nShared terminology.\n')
        self.commit()
        self.config['authority']['glossary'] = 'OTHER.md'
        plan = self.prepare('OTHER.md', manifest=self.config, move_from='CUSTOM.md')
        self.apply(plan)
        self.assertEqual(self.apply(plan)['status'], 'already-applied')
        write(self.root / 'CUSTOM.md', '# Restored old path\n')
        control = self.root / '.dsh-doc-audits'
        self.cli('apply', '--plan', str(control / 'plan.json'), '--review', str(control / 'review.json'), '--allow-in-place', code=2)
        (self.root / 'CUSTOM.md').unlink()
        write(self.root / 'OTHER.md', '# Tampered terms\n')
        self.cli('apply', '--plan', str(control / 'plan.json'), '--review', str(control / 'review.json'), '--allow-in-place', code=2)
        self.cli('review-pack', '--plan', str(self.root / '.dsh-doc-audits/plan.json'), code=2)

    def test_explicit_missing_owner_does_not_fall_back(self):
        self.config['authority']['glossary'] = 'ABSENT.md'
        self.save_config()
        self.assertIsNone(self.inventory_plan()['authority_suggestions']['terminology'])
        self.assertNotIn('GLOSSARY.md', self.cli('inspect')['documentation_surfaces'])
        result = self.cli('verify', code=1)
        self.assertTrue(any(f['code'] == 'authority-missing' for f in result['findings']))

    def test_invalid_configured_paths_rejected(self):
        for rel in ['../terms.md', '/terms.md', './terms.md', 'docs//terms.md', 'code.py', '.git/terms.md', 'docs/*.md', 'docs/terms.md/', '.github/terms.md', None, 4]:
            with self.subTest(rel=rel):
                self.config['authority']['glossary'] = rel
                self.save_config()
                result = self.cli('verify', code=1)
                self.assertTrue(any(f['code'] == 'governance-invalid' for f in result['findings']), result)
                self.cli('inspect', code=2)

    def test_linked_glossary_writes_rejected(self):
        for kind in ['symlink', 'hardlink']:
            with self.subTest(kind=kind):
                path = self.root / 'GLOSSARY.md'
                path.unlink()
                if kind == 'symlink': path.symlink_to(self.root / 'README.md')
                else: os.link(self.root / 'README.md', path)
                self.prepare('GLOSSARY.md', code=2)

    def test_matt_verify_bootstrap_and_adr_reader_evidence(self):
        result = self.cli('verify')
        self.assertFalse(any(f['code'] == 'documentation-untiered' for f in result['findings']))
        preserved = {p:p.read_bytes() for p in self.root.rglob('*.md')}
        self.cli('bootstrap')
        self.assertTrue(all(p.read_bytes() == body for p, body in preserved.items()))
        self.commit()
        reader = {'schema_version':1, 'snapshot_digest':load_guard().snapshot(self.root)['digest'],
                  'reviewer':{'kind':'human','identity':'synthetic-reader','context_id':'reader'},'verdict':'pass',
                  'answers':[{'topic':t,'answer':'Fixture attestation only.', 'evidence':['docs/adr/0001-terms.md' if t == 'decision' else 'README.md']}
                             for t in ['purpose','architecture','subsystem','operations','decision','authority','verification']],
                  'limitations':['No independent semantic assessment; this checks accepted evidence paths only.']}
        control = self.root / '.dsh-doc-audits'
        write(control / '.gitignore', '*\n')
        write(control / 'reader.json', json.dumps(reader))
        self.cli('verify', '--completion', '--fresh-session', str(control / 'reader.json'))
        before = {p:p.read_bytes() for p in self.root.rglob('*.md')}
        plan = self.prepare('scripts/verify_docs.py', mode='upgrade')
        self.apply(plan, dry=True)
        self.assertTrue(all(p.read_bytes() == body for p, body in before.items()))
        self.apply(plan)
        self.assertTrue(all(p.read_bytes() == body for p, body in before.items()))
        verifier = self.root / 'scripts/verify_docs.py'
        for invalid in [False, True]:
            if invalid:
                self.config['authority']['glossary'] = 'code.py'
                self.save_config()
            result = subprocess.run([sys.executable, str(verifier), '--repo', str(self.root), '--json'], capture_output=True, text=True)
            self.assertEqual(result.returncode, int(invalid), result.stdout + result.stderr)
            findings = json.loads(result.stdout)['findings']
            self.assertFalse(any(f['code'] == 'documentation-untiered' for f in findings))
            if invalid: self.assertTrue(any(f['code'] == 'governance-invalid' for f in findings))
