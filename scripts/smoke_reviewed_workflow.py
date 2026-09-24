#!/usr/bin/env python3
"""Run real CLI operations in a disposable repository with SYNTHETIC review JSON.

This tests orchestration and evidence contracts; it does not evaluate a model.
"""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
CLI=ROOT/'dsh-doc-audits/scripts/repo_docs.py'


def main():
    with tempfile.TemporaryDirectory(prefix='dsh-smoke-') as directory:
        area=Path(directory); repo=area/'app'; repo.mkdir(); control=repo/'.dsh-doc-audits'
        observations=[]
        def run(args, expected=0):
            result=subprocess.run(args,capture_output=True,text=True,timeout=30)
            observations.append({'command':[str(a).replace(str(area),'<temp>') for a in args], 'exit_code':result.returncode})
            if result.returncode!=expected:
                raise RuntimeError(f'{args}: {result.returncode}\n{result.stdout}\n{result.stderr}')
            return result.stdout
        def git(*args):
            return run(['git','-C',str(repo),*args])
        def cli(*args, expected=0):
            return json.loads(run([sys.executable,str(CLI),*args,'--json'],expected))
        def put(path,text):
            path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text,encoding='utf-8')
        cli('bootstrap','--repo',str(repo))
        put(repo/'api/main.py','def answer():\n    return 42\n')
        put(repo/'README.md','# Example service\n\nA synthetic acceptance-test service.\n')
        put(repo/'docs/architecture.md','# Architecture\n\nStatus: current authority\n\nThe entry point is api/main.py.\n')
        put(repo/'docs/reference/verification.md','# Local verification\n\nRun the repository-local verifier from the root. It needs no installed skill.\n')
        git('init','-b','main');git('config','user.name','Synthetic Fixture');git('config','user.email','fixture@example.invalid')
        git('add','.');git('commit','-m','synthetic baseline')
        cli('doctor','--repo',str(repo))
        draft=cli('plan','--repo',str(repo),'--output',str(control/'draft.json'))
        assert draft['state']=='draft' and not draft['authority_candidates']
        body='# Answer service\n\nStatus: current authority\n\nThe function answer in api/main.py returns 42 and has no external dependencies.\n'
        proposal={'author_context_id':'synthetic-author','authority_candidates':[{
            'id':'answer-service','path':'docs/subsystems/answer.md','tier':'subsystem',
            'responsibility':'Document the answer function boundary.','evidence':['api/main.py'],
            'current_sources':['docs/architecture.md'],'separation_reason':'The architecture links to a local lookup contract.'}],
            'files':{'create':[{'path':'docs/subsystems/answer.md','content':body,'reason':'establish owner'}],
                     'edit':[{'path':'README.md','content':'# Example service\n\nSee [answer service](docs/subsystems/answer.md).\n','reason':'route to owner'}],
                     'move':[],'demote_to_historical':[],'preserve':['api/main.py']},
            'write_scope':['README.md','docs/subsystems/answer.md'],
            'link_repairs':[{'path':'README.md','targets':['docs/subsystems/answer.md']}],
            'verification':['Run standalone checks and a read-only source comparison.'],
            'rollback':['Restore only the two reviewed document paths.'],'open_conflicts':[]}
        put(control/'proposal.json',json.dumps(proposal))
        plan=cli('plan','--repo',str(repo),'--proposal',str(control/'proposal.json'),'--output',str(control/'plan.json'))
        pack=cli('review-pack','--repo',str(repo),'--plan',str(control/'plan.json'))
        assert pack['plan_digest']==plan['plan_digest']
        review={'schema_version':2,'content_digest':pack['content_digest'],'verdict':'approve',
                'reviewer':{'kind':'human','identity':'synthetic-test-reviewer','context_id':'synthetic-review'},
                'missing_domains':[],'over_split_owners':[],'under_split_owners':[],
                'authority_conflicts':[],'required_changes':[], 'summary':'SYNTHETIC fixture approval, never a real model review.'}
        put(control/'review.json',json.dumps(review))
        args=['apply','--repo',str(repo),'--plan',str(control/'plan.json'),'--review',str(control/'review.json'),'--allow-in-place']
        dry=cli(*args,'--dry-run');assert dry['status']=='dry-run'
        applied=cli(*args); repeated=cli(*args)
        assert (repo/'api/main.py').read_text()=='def answer():\n    return 42\n'
        # Readiness alone is insufficient for the global completion command.
        incomplete=cli('verify','--repo',str(repo),'--completion',expected=1)
        assert any(f['code']=='fresh-session-missing' for f in incomplete['findings'])
        state=cli('doctor','--repo',str(repo))
        fresh={'schema_version':1,'snapshot_digest':state['repository']['snapshot_digest'],
               'reviewer':{'kind':'human','identity':'synthetic-reader','context_id':'synthetic-reader-context'},
               'verdict':'pass', 'answers':[
                   {'topic':'purpose','answer':'A synthetic example service.','evidence':['README.md']},
                   {'topic':'architecture','answer':'An entry point with a documented service boundary.','evidence':['docs/architecture.md']},
                   {'topic':'subsystem','answer':'answer returns 42.','evidence':['docs/subsystems/answer.md']},
                   {'topic':'operations','answer':'Local deterministic checks are the only operation in this fixture.','evidence':['docs/reference/verification.md']},
                   {'topic':'decision','answer':'This fixture creates no durable design decision; the documentation standard says when a decision gets a record.','evidence':['docs/AGENTS.md']},
                   {'topic':'authority','answer':'Local docs rules separate current owners and historical records.','evidence':['docs/AGENTS.md']},
                   {'topic':'verification','answer':'Run scripts/verify_docs.py with Python.','evidence':['docs/reference/verification.md']}],
               'limitations':['Synthetic test data: no real human or independent model assessment occurred.']}
        put(control/'fresh.json',json.dumps(fresh))
        complete=cli('verify','--repo',str(repo),'--completion','--fresh-session',str(control/'fresh.json'))
        assert complete['ok']
        local=json.loads(run([sys.executable,str(repo/'scripts/verify_docs.py'),'--repo',str(repo),'--completion','--json']))
        assert local['ok']
        # The control directory's own .gitignore keeps every control file out of Git.
        assert git('status','--porcelain','--untracked-files=all','--','.dsh-doc-audits')==''
        output={'ok':True,'review_evidence':'synthetic-fixture','independent_model_evaluated':False,
                'apply_status':applied['status'],'repeat_status':repeated['status'],
                'completion_status':'contract-accepted','commands':observations}
        print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
