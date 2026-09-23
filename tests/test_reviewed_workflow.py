"""Actual filesystem/Git boundary tests. Review records here are synthetic fixtures."""
from __future__ import annotations
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'dsh-doc-audits/scripts/repo_docs.py'
GUARD = CLI.with_name('workflow_guard.py')


def load_guard():
    assert GUARD.exists(), 'reviewed workflow module has not been implemented'
    spec = importlib.util.spec_from_file_location('test_workflow_guard', GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, text=True,
                          capture_output=True).stdout.strip()


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.g = load_guard()
        self.tmp = tempfile.TemporaryDirectory(prefix='reviewed docs 中文 ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project'
        self.root.mkdir()
        write(self.root / 'README.md', '# Project\n\nAn existing application.\n')
        write(self.root / 'api/main.py', 'VALUE = 1\n')
        write(self.root / 'docs/old.md', '# Old\n\nExisting contract.\n')
        git(self.root, 'init', '-b', 'main')
        git(self.root, 'config', 'user.name', 'Fixture')
        git(self.root, 'config', 'user.email', 'fixture@example.invalid')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'fixture')
        self.proposal = {
            'author_context_id': 'fixture-author',
            'authority_candidates': [{
                'id': 'service-behavior', 'path': 'docs/subsystems/service.md',
                'tier': 'subsystem', 'responsibility': 'Current service contract',
                'evidence': ['api/main.py'], 'current_sources': ['docs/old.md'],
                'separation_reason': 'Operational behavior has a separate change boundary.'}],
            'files': {
                'create': [{'path': 'docs/subsystems/service.md', 'content':
                            '# Service\n\nStatus: current authority\n\nThe service exposes VALUE = 1.\n', 'reason': 'establish owner'}],
                'edit': [{'path': 'README.md', 'content': '# Project\n\nSee [service](docs/subsystems/service.md).\n',
                          'reason': 'route readers to owner'}],
                'move': [], 'demote_to_historical': [], 'preserve': ['api/main.py', 'docs/old.md']},
            'write_scope': ['README.md', 'docs/subsystems/service.md'],
            'link_repairs': [{'path': 'README.md', 'targets': ['docs/subsystems/service.md']}],
            'verification': ['Compare service documentation with api/main.py; do not start production.'],
            'rollback': ['Restore the captured original bytes for this reviewed change only.'],
            'open_conflicts': [],
        }

    def plan(self):
        return self.g.prepare_plan(self.root, proposal=self.proposal)

    def review(self, plan, **changes):
        value = {'schema_version': 1, 'plan_digest': plan['plan_digest'], 'verdict': 'approve',
                 'reviewer': {'kind': 'human', 'identity': 'synthetic-test-reviewer', 'context_id': 'fixture-review'},
                 'missing_domains': [], 'over_split_owners': [], 'under_split_owners': [],
                 'authority_conflicts': [], 'required_changes': [],
                 'summary': 'Synthetic fixture approval used only in deterministic tests.'}
        value.update(changes)
        return value

    def apply(self, plan=None, review=None, **kwargs):
        plan = plan or self.plan()
        return self.g.apply_plan(self.root, plan, review or self.review(plan), allow_in_place=True, **kwargs)

    def test_doctor_clean_and_no_writes(self):
        before = self.g.snapshot(self.root)
        result = self.g.doctor(self.root)
        self.assertFalse(result['repository']['dirty'])
        self.assertTrue(result['capabilities']['can_plan'])
        self.assertFalse(result['capabilities']['can_apply'])
        self.assertEqual(before, self.g.snapshot(self.root))

    def test_doctor_dirty_keeps_planning_available(self):
        write(self.root / 'api/main.py', 'VALUE = 2\n')
        result = self.g.doctor(self.root)
        self.assertTrue(result['repository']['dirty'])
        self.assertTrue(result['capabilities']['can_plan'])
        self.assertFalse(result['capabilities']['can_apply'])

    def test_doctor_non_git_is_read_only(self):
        root = Path(self.tmp.name) / 'empty'
        root.mkdir()
        result = self.g.doctor(root)
        self.assertTrue(result['capabilities']['can_plan'])
        self.assertFalse(result['capabilities']['can_apply'])
        self.assertFalse((root / '.git').exists())

    def test_doctor_recognizes_linked_worktree(self):
        worktree = Path(self.tmp.name) / 'worktree'
        git(self.root, 'worktree', 'add', '-b', 'docs', str(worktree))
        result = self.g.doctor(worktree)
        self.assertTrue(result['repository']['worktree'])
        self.assertTrue(result['capabilities']['can_apply'])

    def test_greenfield_cannot_prepare_owner_without_user_decision(self):
        root = Path(self.tmp.name) / 'unborn'
        root.mkdir()
        git(root, 'init', '-b', 'main')
        data = copy.deepcopy(self.proposal)
        data['authority_candidates'][0]['evidence'] = []
        data['authority_candidates'][0]['current_sources'] = []
        data['files']['edit'] = []
        data['files']['preserve'] = []
        data['write_scope'] = ['docs/subsystems/service.md']
        data['link_repairs'] = []
        # Even greenfield owners need an explicit user decision as evidence.
        with self.assertRaises(ValueError):
            self.g.prepare_plan(root, proposal=data)

    def test_draft_has_no_invented_owner(self):
        plan = self.g.prepare_plan(self.root)
        self.assertEqual(plan['state'], 'draft')
        self.assertEqual(plan['authority_candidates'], [])
        self.assertEqual(plan['files']['create'], [])
        self.assertIn('repository_snapshot', plan)
        self.assertIn('write_scope', plan)

    def test_plan_binds_generic_model_authored_owners(self):
        plan = self.plan()
        self.assertEqual(plan['state'], 'prepared')
        self.assertEqual(plan['authority_candidates'][0]['id'], 'service-behavior')
        self.assertEqual(len(plan['plan_digest']), 64)
        self.assertNotIn('kline', json.dumps(plan))

    def test_review_package_includes_exact_diff(self):
        plan = self.plan()
        pack = self.g.review_package(self.root, plan)
        self.assertEqual(pack['plan_digest'], plan['plan_digest'])
        self.assertIn('VALUE = 1', pack['diff'])
        self.assertIn('README.md', pack['diff'])
        self.assertTrue(pack['review_questions'])

    def test_model_candidate_without_evidence_rejected(self):
        self.proposal['authority_candidates'][0]['evidence'] = []
        with self.assertRaises(ValueError): self.plan()

    def test_missing_evidence_path_rejected(self):
        self.proposal['authority_candidates'][0]['evidence'] = ['not-here.py']
        with self.assertRaises(ValueError): self.plan()

    def test_unknown_schema_field_rejected(self):
        self.proposal['auto_push'] = True
        with self.assertRaises(ValueError): self.plan()

    def test_apply_dry_run_leaves_tree_unchanged(self):
        before = self.g.snapshot(self.root)
        result = self.apply(dry_run=True)
        self.assertEqual(result['status'], 'dry-run')
        self.assertEqual(before, self.g.snapshot(self.root))

    def test_apply_only_approved_files_and_repeat_noop(self):
        before_product = (self.root / 'api/main.py').read_bytes()
        plan = self.plan()
        result = self.apply(plan)
        self.assertEqual(result['status'], 'applied')
        self.assertEqual(sorted(result['changed_files']), sorted(self.proposal['write_scope']))
        self.assertEqual(before_product, (self.root / 'api/main.py').read_bytes())
        second = self.apply(plan)
        self.assertEqual(second['status'], 'already-applied')
        self.assertEqual(second['changed_files'], [])

    def test_in_place_requires_explicit_permission(self):
        plan = self.plan()
        with self.assertRaises(ValueError): self.g.apply_plan(self.root, plan, self.review(plan))

    def test_dirty_plan_cannot_apply(self):
        write(self.root / 'api/main.py', 'VALUE = 2\n')
        plan = self.plan()
        with self.assertRaises(ValueError): self.apply(plan)

    def test_stale_snapshot_rejected_before_writes(self):
        plan = self.plan()
        write(self.root / 'api/main.py', 'VALUE = 2\n')
        with self.assertRaises(ValueError): self.apply(plan)
        self.assertFalse((self.root / 'docs/subsystems/service.md').exists())

    def test_new_untracked_file_invalidates_plan(self):
        plan = self.plan()
        write(self.root / 'new.txt', 'concurrent work')
        with self.assertRaises(ValueError): self.apply(plan)

    def test_altered_plan_cannot_reuse_review(self):
        plan = self.plan()
        review = self.review(plan)
        plan['files']['edit'][0]['content'] = '# Unauthorized change\n'
        with self.assertRaises(ValueError): self.apply(plan, review)

    def test_revision_or_block_verdict_cannot_apply(self):
        plan = self.plan()
        for verdict in ['revise', 'block']:
            with self.subTest(verdict=verdict):
                with self.assertRaises(ValueError): self.apply(plan, self.review(plan, verdict=verdict))

    def test_approve_with_required_changes_rejected(self):
        plan = self.plan()
        with self.assertRaises(ValueError): self.apply(plan, self.review(plan, required_changes=['Fix overlap']))

    def test_missing_and_stale_reviews_rejected(self):
        plan = self.plan()
        with self.assertRaises(ValueError): self.g.apply_plan(self.root, plan, {}, allow_in_place=True)
        with self.assertRaises(ValueError): self.apply(plan, self.review(plan, plan_digest='0'*64))

    def test_self_review_requires_opt_in_and_is_labeled(self):
        plan = self.plan()
        review = self.review(plan, reviewer={'kind':'self','identity':'fixture-author','context_id':'fixture-author'})
        with self.assertRaises(ValueError): self.apply(plan, review)
        result = self.apply(plan, review, allow_self_review=True)
        self.assertEqual(result['review_assurance'], 'degraded-self-review')

    def test_same_context_cannot_claim_independence(self):
        plan = self.plan()
        review = self.review(plan, reviewer={'kind':'independent-agent','identity':'fixture-model','context_id':'fixture-author'})
        with self.assertRaises(ValueError): self.apply(plan, review)

    def test_open_conflicts_block_apply(self):
        self.proposal['open_conflicts'] = ['Runtime configuration conflicts with default.']
        plan = self.plan()
        with self.assertRaises(ValueError): self.apply(plan)

    def test_product_code_not_authorized_even_in_write_scope(self):
        self.proposal['files']['edit'].append({'path':'api/main.py','content':'VALUE = 9\n','reason':'not docs'})
        self.proposal['write_scope'].append('api/main.py')
        with self.assertRaises(ValueError): self.plan()

    def test_path_traversal_and_absolute_paths_rejected(self):
        for path in ['../outside.md','/tmp/out.md','docs/../api/main.py','docs\\out.md', 'docs//out.md', '.git/config']:
            with self.subTest(path=path):
                proposal = copy.deepcopy(self.proposal)
                proposal['files']['create'][0]['path'] = path
                proposal['write_scope'].append(path)
                with self.assertRaises(ValueError): self.g.prepare_plan(self.root, proposal=proposal)

    def test_symlink_write_target_rejected(self):
        external = Path(self.tmp.name) / 'outside'
        external.mkdir()
        (self.root / 'docs/subsystems').symlink_to(external, target_is_directory=True)
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'symlink')
        with self.assertRaises(ValueError): self.plan()
        self.assertEqual(list(external.iterdir()), [])

    def test_move_is_reviewed_and_preserves_exact_old_content(self):
        self.proposal['files']['preserve'].remove('docs/old.md')
        self.proposal['files']['move'] = [{'from':'docs/old.md','to':'docs/moved.md','reason':'rename current reference'}]
        self.proposal['write_scope'] += ['docs/old.md','docs/moved.md']
        content = (self.root / 'docs/old.md').read_bytes()
        result = self.apply()
        self.assertEqual(result['status'],'applied')
        self.assertFalse((self.root / 'docs/old.md').exists())
        self.assertEqual((self.root / 'docs/moved.md').read_bytes(), content)

    def test_demote_keeps_historical_body(self):
        self.proposal['files']['preserve'].remove('docs/old.md')
        before = (self.root / 'docs/old.md').read_text()
        self.proposal['files']['demote_to_historical'] = [{'path':'docs/old.md',
            'content':'Status: historical\nCurrent authority: [service](subsystems/service.md)\n\n'+before,
            'reason':'current owner established'}]
        self.proposal['write_scope'].append('docs/old.md')
        self.apply()
        self.assertTrue((self.root / 'docs/old.md').read_text().endswith(before))

    def test_demote_cannot_erase_original_body(self):
        self.proposal['files']['preserve'].remove('docs/old.md')
        self.proposal['files']['demote_to_historical'] = [{'path':'docs/old.md', 'content':'Status: historical\n', 'reason':'erase'}]
        self.proposal['write_scope'].append('docs/old.md')
        with self.assertRaises(ValueError): self.plan()

    def test_frozen_archive_cannot_be_written(self):
        self.proposal['files']['create'][0]['path'] = '.agents/notes/archived/test.md'
        self.proposal['write_scope'].append('.agents/notes/archived/test.md')
        with self.assertRaises(ValueError): self.plan()

    def test_caught_write_error_rolls_back(self):
        before = self.g.snapshot(self.root)
        original = self.g._replace_file
        calls = []
        def fail_once(path, content, mode):
            calls.append(str(path))
            if len(calls) == 2: raise OSError('injected disk failure')
            return original(path, content, mode)
        with patch.object(self.g, '_replace_file', side_effect=fail_once):
            with self.assertRaises(OSError): self.apply()
        self.assertEqual(before, self.g.snapshot(self.root))

    def test_control_files_do_not_dirty_or_invalidate_plan(self):
        plan = self.plan()
        write(self.root / '.dsh-doc-audits/plan.json', json.dumps(plan))
        self.assertFalse(self.g.doctor(self.root)['repository']['dirty'])
        self.assertEqual(self.apply(plan)['status'], 'applied')

    def test_tracked_control_directory_is_rejected(self):
        write(self.root / '.dsh-doc-audits/unexpected.py','x=1')
        git(self.root,'add','.')
        git(self.root,'commit','-m','tracked control is unsupported')
        self.assertFalse(self.g.doctor(self.root)['capabilities']['can_apply'])

    def test_completion_result_requires_current_snapshot_and_seven_answers(self):
        result = {'schema_version':1, 'snapshot_digest':self.g.snapshot(self.root)['digest'],
                  'reviewer':{'kind':'human','identity':'synthetic-reader','context_id':'reader'},
                  'verdict':'pass', 'answers':[], 'limitations':[]}
        with self.assertRaises(ValueError): self.g.validate_fresh_session(self.root,result)

    def test_cli_doctor_and_plan_are_read_only(self):
        before = self.g.snapshot(self.root)
        for command in ['doctor','plan']:
            completed = subprocess.run([sys.executable,str(CLI),command,'--repo',str(self.root),'--json'],capture_output=True,text=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertIsInstance(json.loads(completed.stdout),dict)
        self.assertEqual(before,self.g.snapshot(self.root))

    def test_cli_full_roundtrip(self):
        control = Path(self.tmp.name) / 'control'
        control.mkdir()
        proposal_path=control/'proposal.json'
        proposal_path.write_text(json.dumps(self.proposal))
        plan_path=control/'plan.json'
        def cli(*args):
            result=subprocess.run([sys.executable,str(CLI),*args,'--json'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr+result.stdout)
            return json.loads(result.stdout)
        plan=cli('plan','--repo',str(self.root),'--proposal',str(proposal_path),'--output',str(plan_path))
        pack=cli('review-pack','--repo',str(self.root),'--plan',str(plan_path))
        self.assertEqual(pack['plan_digest'],plan['plan_digest'])
        review_path=control/'review.json'
        review_path.write_text(json.dumps(self.review(plan)))
        result=cli('apply','--repo',str(self.root),'--plan',str(plan_path),'--review',str(review_path),'--allow-in-place')
        self.assertEqual(result['status'],'applied')

    def test_invalid_receipt_path_is_rejected_before_apply(self):
        plan=self.plan(); controls=Path(self.tmp.name)/'controls'; controls.mkdir()
        plan_path=controls/'plan.json'; plan_path.write_text(json.dumps(plan))
        review_path=controls/'review.json'; review_path.write_text(json.dumps(self.review(plan)))
        before=self.g.snapshot(self.root)
        result=subprocess.run([sys.executable,str(CLI),'apply','--repo',str(self.root),
            '--plan',str(plan_path),'--review',str(review_path),'--allow-in-place',
            '--output',str(self.root/'api/main.py'),'--json'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(before,self.g.snapshot(self.root))

    def test_existing_history_cannot_be_rewritten_as_an_edit(self):
        write(self.root/'docs/superpowers/plans/old.md','# Historic evidence\n')
        git(self.root,'add','.'); git(self.root,'commit','-m','history')
        self.proposal['files']['edit'].append({'path':'docs/superpowers/plans/old.md', 'content':'lost','reason':'rewrite'})
        self.proposal['write_scope'].append('docs/superpowers/plans/old.md')
        with self.assertRaises(ValueError): self.plan()

    def test_private_git_metadata_under_docs_is_never_writable(self):
        self.proposal['files']['create'][0]['path']='docs/.git/config.md'
        self.proposal['write_scope']=['README.md','docs/.git/config.md']
        self.proposal['authority_candidates'][0]['path']='docs/.git/config.md'
        self.proposal['link_repairs']=[]
        with self.assertRaises(ValueError): self.plan()

    def test_valid_fresh_session_contract_passes_and_stale_one_fails(self):
        value={'schema_version':1,'snapshot_digest':self.g.snapshot(self.root)['digest'],
               'reviewer':{'kind':'human','identity':'synthetic-reader','context_id':'reader'},'verdict':'pass',
               'answers':[{'topic':t,'answer':'Synthetic fixture answer.','evidence':['README.md']}
                   for t in ['purpose','architecture','subsystem','operations','decision','authority','verification']],
               'limitations':['No real independent model was used in this test.']}
        self.assertTrue(self.g.validate_fresh_session(self.root,value)['ok'])
        value['snapshot_digest']='0'*64
        with self.assertRaises(ValueError): self.g.validate_fresh_session(self.root,value)

    def test_no_duplicate_json_keys_accepted(self):
        path=Path(self.tmp.name)/'duplicate.json'
        path.write_text('{"verdict":"block","verdict":"approve"}')
        with self.assertRaises(ValueError): self.g.read_json(path)

    def test_hardlink_target_rejected(self):
        original=Path(self.tmp.name)/'original'
        original.write_text('shared bytes')
        (self.root/'README.md').unlink()
        os.link(original,self.root/'README.md')
        git(self.root,'add','.'); git(self.root,'commit','-m','hardlink')
        with self.assertRaises(ValueError): self.plan()
        self.assertEqual(original.read_text(),'shared bytes')

    def test_new_file_under_symlink_is_not_followed_during_snapshot(self):
        outside=Path(self.tmp.name)/'external'; outside.mkdir()
        write(outside/'hidden.md','unrelated outside bytes')
        git(self.root,'rm','-r','docs')
        (self.root/'docs').symlink_to(outside,target_is_directory=True)
        git(self.root,'add','.'); git(self.root,'commit','-m','symlink tree')
        snap=self.g.snapshot(self.root)
        self.assertNotIn('docs/hidden.md',snap['files'])
        self.assertIn('docs',snap['files'])

    def test_greenfield_with_recorded_user_decision(self):
        root=Path(self.tmp.name)/'empty-git'; root.mkdir(); git(root,'init','-b','main')
        proposal=copy.deepcopy(self.proposal)
        proposal['user_decisions']={'purpose':'The user approved a minimal service project.'}
        proposal['authority_candidates'][0]['evidence']=['decision:purpose']
        proposal['authority_candidates'][0]['current_sources']=[]
        proposal['files']['edit']=[]; proposal['files']['preserve']=[]
        proposal['write_scope']=['docs/subsystems/service.md']; proposal['link_repairs']=[]
        plan=self.g.prepare_plan(root,proposal)
        result=self.g.apply_plan(root,plan,self.review(plan),allow_in_place=True)
        self.assertEqual(result['status'],'applied')
        self.assertIsNone(plan['repository_snapshot']['head'])

    def test_review_package_does_not_duplicate_full_document_bodies(self):
        pack=self.g.review_package(self.root,self.plan())
        self.assertEqual(json.dumps(pack).count('The service exposes VALUE = 1.'),1)
        self.assertNotIn('changes',pack)
        self.assertIn('authority_candidates',pack)

    def test_upgrade_cannot_reset_project_owned_documentation(self):
        with self.assertRaises(ValueError):
            self.g.prepare_plan(self.root,self.proposal,mode='upgrade')
