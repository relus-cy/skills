"""Snapshot-bound documentation plans and reviewed filesystem writes.

No model calls, arbitrary shell commands, credentials, commits or publication.
Review JSON is an attestation, not an authenticated identity or semantic proof.
"""
from __future__ import annotations

import copy
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
from typing import Any

VERSION = '0.2.0'
SCHEMAS = Path(__file__).resolve().parents[1] / 'schemas'
CONTROL = '.dsh-doc-audits'
# `*` also matches this file, so Git and gitignore-aware search skip the whole directory.
CONTROL_IGNORE = '# dsh-doc-audits control files; delete this directory once the migration is verified.\n*\n'
GENERATED = {'scripts/verify_docs.py', '.github/workflows/docs-governance.yml'}
MAX_JSON_BYTES = 16 * 1024 * 1024


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def read_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError('JSON input exceeds 16 MiB; split the migration')
    def pairs(items):
        output = {}
        for key, value in items:
            if key in output:
                raise ValueError(f'duplicate JSON key: {key}')
            output[key] = value
        return output
    value = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f'invalid JSON constant: {token}')))
    if not isinstance(value, dict):
        raise ValueError('JSON input must be an object')
    return value


def _validate(value: Any, schema: dict[str, Any], top: dict[str, Any], location='$') -> None:
    """Only the explicit JSON Schema subset used by this package; fail closed."""
    known = {'$schema','title','definitions','$ref','type','properties','required','additionalProperties',
             'items','minItems','minLength','pattern','enum','const','minimum','maximum','anyOf'}
    if set(schema) - known:
        raise ValueError(f'unsupported schema keyword: {sorted(set(schema)-known)}')
    if '$ref' in schema:
        ref = schema['$ref']
        if not ref.startswith('#/'):
            raise ValueError('only local schema references are supported')
        target = top
        for key in ref[2:].split('/'):
            target = target[key]
        _validate(value, target, top, location)
        return
    if 'anyOf' in schema:
        for option in schema['anyOf']:
            try:
                _validate(value, option, top, location)
                return
            except ValueError:
                pass
        raise ValueError(f'{location}: no allowed schema matched')
    kinds = {'object':dict, 'array':list, 'string':str, 'integer':int, 'boolean':bool, 'null':type(None)}
    expected = schema.get('type')
    if expected and (expected not in kinds or type(value) is not kinds[expected]):
        raise ValueError(f'{location}: expected {expected}')
    if 'const' in schema and (value != schema['const'] or type(value) is not type(schema['const'])):
        raise ValueError(f'{location}: wrong constant')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{location}: value outside enum')
    if isinstance(value, dict):
        missing = set(schema.get('required', [])) - value.keys()
        if missing:
            raise ValueError(f'{location}: missing {sorted(missing)}')
        properties = schema.get('properties', {})
        extra = schema.get('additionalProperties', True)
        for key, child in value.items():
            if key in properties:
                _validate(child, properties[key], top, f'{location}.{key}')
            elif extra is False:
                raise ValueError(f'{location}: unexpected field {key}')
            elif isinstance(extra, dict):
                _validate(child, extra, top, f'{location}.{key}')
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0):
            raise ValueError(f'{location}: not enough items')
        for i, child in enumerate(value):
            _validate(child, schema.get('items', {}), top, f'{location}[{i}]')
    if isinstance(value, str):
        import re
        if len(value.strip()) < schema.get('minLength', 0):
            raise ValueError(f'{location}: empty string')
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            raise ValueError(f'{location}: invalid format')
    if type(value) is int:
        if value < schema.get('minimum', value) or value > schema.get('maximum', value):
            raise ValueError(f'{location}: integer outside bounds')


def validate_schema(name: str, value: Any) -> None:
    schema = read_json(SCHEMAS / f'{name}.schema.json')
    _validate(value, schema, schema)


def _git(root: Path, *args: str, required=False) -> subprocess.CompletedProcess:
    env = {**os.environ, 'GIT_OPTIONAL_LOCKS':'0'}
    # An inherited Git environment must not retarget reads to another checkout.
    for key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_COMMON_DIR'):
        env.pop(key, None)
    try:
        result = subprocess.run(['git','-C',str(root),*args], capture_output=True,
                                timeout=30, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f'Git unavailable or timed out: {exc}') from exc
    if required and result.returncode:
        raise ValueError(f'Git read failed: {result.stderr.decode(errors="replace").strip()}')
    return result


def relative_path(value: str) -> str:
    if (not isinstance(value, str) or not value or value.startswith(('/', '~'))
            or '\\' in value or ':' in value or any(ord(c)<32 for c in value)
            or any(c in value for c in '*?[]')
            or any(part in {'','.','..'} for part in value.split('/'))):
        raise ValueError(f'not a canonical relative path: {value!r}')
    if ".git" in value.split("/"):
        raise ValueError("Git metadata is outside the permitted path space")
    return value


def safe_path(root: Path, rel: str) -> Path:
    relative_path(rel)
    path = root
    for part in PurePosixPath(rel).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f'symlink boundary: {rel}')
    if not path.resolve().is_relative_to(root):
        raise ValueError(f'path escapes repository: {rel}')
    return path


def control_directory(root: Path) -> Path:
    """Create the control directory with its own .gitignore; project ignore files stay untouched."""
    control=safe_path(root,CONTROL)
    control.mkdir(exist_ok=True)
    try:
        # O_EXCL never follows a link and never replaces an existing ignore file.
        fd=os.open(control/'.gitignore',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
    except FileExistsError:
        return control
    with os.fdopen(fd,'w',encoding='utf-8') as stream:
        stream.write(CONTROL_IGNORE)
    return control


def _file_digest(content: bytes, mode: int, kind='file') -> str:
    return hashlib.sha256(f'{kind}:{mode:o}\0'.encode()+content).hexdigest()


def _fingerprint(path: Path) -> str:
    mode = stat.S_IMODE(path.lstat().st_mode)
    if path.is_symlink():
        return _file_digest(os.fsencode(os.readlink(path)), mode, 'symlink')
    if not path.is_file():
        # Git submodule: bind the recorded HEAD, never traverse it.
        head = _git(path, 'rev-parse','HEAD', required=True).stdout.strip()
        return _file_digest(head, mode, 'gitlink')
    hasher = hashlib.sha256(f'file:{mode:o}\0'.encode())
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def _snapshot_digest(value: dict[str, Any]) -> str:
    return digest({k:value[k] for k in ('root','head','branch','files')})


def snapshot(repo: str | Path) -> dict[str, Any]:
    root = Path(repo).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f'repository is not a directory: {root}')
    probe = _git(root, 'rev-parse','--show-toplevel')
    is_git = probe.returncode == 0
    head, branch, worktree, dirty, tracked_control = None, '', False, False, False
    if is_git:
        actual = Path(os.fsdecode(probe.stdout.strip())).resolve()
        if actual != root:
            raise ValueError(f'--repo must be the Git worktree root: {actual}')
        result = _git(root,'rev-parse','--verify','HEAD')
        head = result.stdout.decode().strip() if result.returncode == 0 else None
        branch = _git(root,'symbolic-ref','--quiet','--short','HEAD').stdout.decode().strip()
        gitdir = _git(root,'rev-parse','--absolute-git-dir', required=True).stdout.decode().strip()
        common = _git(root,'rev-parse','--git-common-dir', required=True).stdout.decode().strip()
        superproject = _git(root,'rev-parse','--show-superproject-working-tree', required=True).stdout.strip()
        commonpath = (root / common).resolve()
        worktree = Path(gitdir).resolve() != commonpath and not superproject
        cached = _git(root,'ls-files','-z','--cached', required=True).stdout.split(b'\0')
        tracked_control = any(os.fsdecode(p).startswith(CONTROL+'/') or os.fsdecode(p)==CONTROL for p in cached if p)
        status = _git(root,'status','--porcelain=v1','-z','--untracked-files=all', required=True).stdout.split(b'\0')
        i=0
        while i < len(status):
            row=status[i]; i+=1
            if not row: continue
            xy=row[:2]; rel=os.fsdecode(row[3:])
            if b'R' in xy or b'C' in xy: i+=1
            if xy==b'??' and rel.startswith(CONTROL+'/'): continue
            dirty=True
        paths = _git(root,'ls-files','-z','--cached','--others','--exclude-standard', required=True).stdout.split(b'\0')
        names = sorted(set(os.fsdecode(p) for p in paths if p))
    else:
        names=[]
        for folder, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if d not in {'.git',CONTROL}]
            for d in list(dirs):
                if (Path(folder)/d).is_symlink():
                    files.append(d); dirs.remove(d)
            names.extend((Path(folder)/name).relative_to(root).as_posix() for name in files)
    fingerprints={}
    for rel in names:
        if rel==CONTROL or rel.startswith(CONTROL+'/'): continue
        path=root/rel
        linked_parent = next((parent for parent in path.parents if parent != root and parent.is_relative_to(root) and parent.is_symlink()), None)
        if linked_parent is not None:
            fingerprints[linked_parent.relative_to(root).as_posix()] = _fingerprint(linked_parent)
            continue
        if path.exists() or path.is_symlink(): fingerprints[rel]=_fingerprint(path)
    value={'root':str(root),'head':head,'branch':branch,'git':is_git,'worktree':worktree,
           'dirty':dirty,'tracked_control':tracked_control,'files':fingerprints}
    value['digest']=_snapshot_digest(value)
    return value


def doctor(repo: str | Path) -> dict[str, Any]:
    snap=snapshot(repo)
    blockers=[]
    if not snap['git']: blockers.append('git-initialization-required')
    if snap['dirty']: blockers.append('working-tree-dirty')
    if snap['tracked_control']: blockers.append('control-directory-must-not-be-tracked')
    if not snap['worktree']: blockers.append('isolated-worktree-or-explicit-in-place-permission-required')
    version=_git(Path(snap['root']), '--version', required=True).stdout.decode().strip()
    root=Path(snap['root'])
    return {'repository':{'root':snap['root'],'head':snap['head'],'branch':snap['branch'],
                          'worktree':snap['worktree'],'dirty':snap['dirty'],
                          'snapshot_digest':snap['digest'],'file_count':len(snap['files'])},
            'runtime':{'python':sys.version.split()[0],'git':version},
            'documentation':{'root_agents':(root/'AGENTS.md').is_file(),
                             'governance_manifest':(root/'docs/governance.yaml').is_file()},
            'capabilities':{'can_plan':True,'can_apply':not blockers,'blocking_reasons':blockers}}


def _writable(root: Path, rel: str) -> Path:
    path=safe_path(root,rel)
    allowed=(rel in {'README.md','AGENTS.md','CONTEXT.md','docs/governance.yaml'} | GENERATED
             or (rel.startswith('docs/') and rel.endswith('.md'))
             or (rel.startswith('.agents/notes/') and rel.endswith('.md')))
    if not allowed or rel.startswith('.agents/notes/archived/'):
        raise ValueError(f'outside documentation write boundary: {rel}')
    if path.exists() and (not path.is_file() or path.stat().st_nlink>1):
        raise ValueError(f'write target is not an ordinary single-link file: {rel}')
    return path


def _compile_changes(root: Path, proposal: dict[str, Any]) -> list[dict[str, Any]]:
    writes: dict[str, tuple[str | None,int]]={}
    def put(rel, content, mode=None):
        path=_writable(root,rel)
        if rel in writes: raise ValueError(f'duplicate write: {rel}')
        writes[rel]=(content, stat.S_IMODE(path.stat().st_mode) if path.exists() else (mode or 0o644))
    for category in ('create','edit','demote_to_historical'):
        for item in proposal['files'][category]:
            path=_writable(root,item['path'])
            if category=='edit' and item['path'].startswith(('docs/superpowers/','docs/plans/','docs/reports/','docs/handoffs/','docs/releases/','docs/postmortem')):
                raise ValueError('historical bodies are preserved; use metadata-only demotion')
            if category=='create' and path.exists(): raise ValueError(f'create target exists: {item["path"]}')
            if category!='create' and not path.exists(): raise ValueError(f'edit target missing: {item["path"]}')
            if category=='demote_to_historical':
                before=path.read_text(encoding='utf-8')
                if not item['content'].endswith(before) or 'Status: historical' not in item['content'][:-len(before) if before else None]:
                    raise ValueError('demotion must prepend status/owner metadata and preserve the original body')
            put(item['path'],item['content'])
    for item in proposal['files']['move']:
        source=_writable(root,item['from']); target=_writable(root,item['to'])
        if item['from'].startswith(('docs/superpowers/','docs/plans/','docs/reports/','docs/handoffs/','docs/releases/','docs/postmortem')):
            raise ValueError('first-pass migration preserves historical paths')
        if not source.exists() or target.exists(): raise ValueError('move requires existing source and absent target')
        content=source.read_text(encoding='utf-8')
        if 'content' in item and item['content']!=content: raise ValueError('move content cannot silently rewrite source')
        item['content']=content
        put(item['from'],None)
        put(item['to'],content,stat.S_IMODE(source.stat().st_mode))
    scope=proposal['write_scope']
    if len(scope)!=len(set(scope)) or set(scope)!=set(writes):
        raise ValueError('write_scope must exactly enumerate all changed paths, including both sides of moves')
    for rel in proposal['files']['preserve']:
        safe_path(root,rel)
        if rel in writes: raise ValueError(f'preserve conflicts with write: {rel}')
    changes=[]
    for rel,(content,mode) in sorted(writes.items()):
        path=root/rel
        changes.append({'path':rel,'content':content,'mode':mode,
                        'before_digest':_fingerprint(path) if path.exists() else None,
                        'after_digest':_file_digest(content.encode(),mode) if content is not None else None})
    return changes


def _validate_owners(root: Path, plan: dict[str, Any]) -> None:
    ids=set(); owners=set()
    after=dict(plan['repository_snapshot']['files'])
    for c in plan['changes']:
        if c['content'] is None: after.pop(c['path'],None)
        else: after[c['path']]=c['after_digest']
    for owner in plan['authority_candidates']:
        path=owner['path']; safe_path(root,path)
        if path not in after or not path.endswith('.md'): raise ValueError(f'owner lacks an existing or planned document: {path}')
        if path.startswith(('docs/superpowers/','.agents/notes/archived/')):
            raise ValueError('historical material cannot be the proposed current owner')
        if owner['id'] in ids or path in owners: raise ValueError('candidate ids and owner paths must be unique')
        ids.add(owner['id']); owners.add(path)
        for rel in owner['evidence']:
            if rel.startswith('decision:'):
                if rel[9:] not in plan['user_decisions']: raise ValueError('user-decision evidence was not recorded')
            else:
                evidence=safe_path(root,rel)
                if not evidence.is_file(): raise ValueError(f'missing candidate evidence: {rel}')
        for rel in owner['current_sources']:
            safe_path(root,rel)
            if rel not in plan['repository_snapshot']['files']: raise ValueError(f'missing current source: {rel}')
    for repair in plan['link_repairs']:
        if repair['path'] not in plan['write_scope']: raise ValueError('link repair must have a reviewed write')
        for target in repair['targets']:
            safe_path(root,target)
            if target not in after: raise ValueError(f'link repair target missing: {target}')


def prepare_plan(repo: str | Path, proposal: dict[str, Any] | None=None, *, profile='generic', mode='migrate') -> dict[str, Any]:
    snap=snapshot(repo); root=Path(snap['root'])
    base={'author_context_id':'unassigned','authority_candidates':[],
          'files':{'create':[],'edit':[],'move':[],'demote_to_historical':[],'preserve':[]},
          'write_scope':[],'link_repairs':[], 'verification':['Run repository-local checks, semantic review and fresh-session assessment.'],
          'rollback':['Restore reviewed file bytes only; never reset unrelated user work.'],
          'open_conflicts':[], 'user_decisions':{}}
    if proposal is not None:
        validate_schema('proposal',proposal)
        base.update(copy.deepcopy(proposal))
    plan={**base,'schema_version':1,'skill_version':VERSION,'mode':mode,'profile':profile,
          'state':'draft' if proposal is None else 'prepared','repository_snapshot':snap,
          'changes':[],'plan_digest':None}
    if proposal is not None:
        if not plan['authority_candidates']: raise ValueError('prepared plan needs model-authored authority candidates')
        plan['changes']=_compile_changes(root,plan)
        if not plan['changes']: raise ValueError('prepared plan has no writes; use audit for read-only work')
        if mode == 'upgrade' and any(c['path'] not in GENERATED for c in plan['changes']):
            raise ValueError('upgrade may refresh only the named generated verifier and workflow')
        _validate_owners(root,plan)
        plan['plan_digest']=digest({k:v for k,v in plan.items() if k!='plan_digest'})
    validate_schema('migration-plan',plan)
    return plan


def validate_plan(plan: dict[str, Any]) -> None:
    validate_schema('migration-plan',plan)
    if plan['state']!='prepared' or plan['plan_digest']!=digest({k:v for k,v in plan.items() if k!='plan_digest'}):
        raise ValueError('plan is draft, unsealed or changed since preparation')
    if not plan['authority_candidates'] or not plan['changes']: raise ValueError('empty prepared plan')
    root=Path(plan['repository_snapshot']['root'])
    if plan['mode'] == 'upgrade' and any(c['path'] not in GENERATED for c in plan['changes']):
        raise ValueError('upgrade scope includes project-owned content')
    compiled={}
    for group in ('create','edit','demote_to_historical'):
        for item in plan['files'][group]:
            if item['path'] in compiled: raise ValueError('duplicate operation')
            compiled[item['path']]=item['content']
    for item in plan['files']['move']:
        if 'content' not in item or item['from'] in compiled or item['to'] in compiled:
            raise ValueError('invalid compiled move')
        compiled[item['from']]=None; compiled[item['to']]=item['content']
    paths=[c['path'] for c in plan['changes']]
    if len(paths)!=len(set(paths)) or set(paths)!=set(plan['write_scope']) or set(paths)!=set(compiled):
        raise ValueError('compiled changes and write scope differ')
    for change in plan['changes']:
        _writable(root,change['path'])
        if compiled[change['path']]!=change['content']: raise ValueError('compiled content differs from proposal')
        actual=_file_digest(change['content'].encode(),change['mode']) if change['content'] is not None else None
        if change['after_digest']!=actual: raise ValueError('compiled output digest mismatch')
        if change['before_digest']!=plan['repository_snapshot']['files'].get(change['path']):
            raise ValueError('compiled input digest mismatch')


def _review_assurance(plan, review, allow_self_review=False):
    validate_schema('review-result',review)
    if review['plan_digest']!=plan['plan_digest']: raise ValueError('review belongs to another plan')
    if review['verdict']!='approve' or any(review[k] for k in ('missing_domains','over_split_owners','under_split_owners','authority_conflicts','required_changes')):
        raise ValueError('review is not an unconditional approval; revise and request a fresh review')
    reviewer=review['reviewer']
    if reviewer['kind']=='self':
        if not allow_self_review: raise ValueError('self-review requires explicit --allow-self-review')
        return 'degraded-self-review'
    if reviewer['context_id']==plan['author_context_id']:
        raise ValueError('same-context review cannot claim independence')
    return 'declared-'+reviewer['kind']+'-review'


def review_package(repo, plan):
    validate_plan(plan)
    current=snapshot(repo)
    if current['digest']!=plan['repository_snapshot']['digest']: raise ValueError('plan snapshot is stale')
    root=Path(current['root']); differences=[]
    for change in plan['changes']:
        path=root/change['path']
        before=path.read_text(encoding='utf-8') if path.exists() else ''
        after=change['content'] or ''
        differences.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),
                                                fromfile='a/'+change['path'],tofile='b/'+change['path']))
    pack={'schema_version':1,'plan_digest':plan['plan_digest'],
          'repository':{'root':current['root'],'head':current['head'],'snapshot_digest':current['digest']},
          'author_context_id':plan['author_context_id'],'authority_candidates':plan['authority_candidates'],
          'operations':[{'kind':kind, **{k:v for k,v in item.items() if k!='content'}}
                        for kind in ('create','edit','move','demote_to_historical') for item in plan['files'][kind]],
          'preserve':plan['files']['preserve'],'write_scope':plan['write_scope'],
          'open_conflicts':plan['open_conflicts'],'verification':plan['verification'],'rollback':plan['rollback'],
          'diff':''.join(differences),
          'review_questions':['Are important fact domains missing?', 'Are any owners over-split or overlapping?',
                              'Are independent responsibilities incorrectly merged?', 'Are current and historical authorities unambiguous?',
                              'Do exact changes preserve evidence, links, operational meaning and write boundaries?'],
          'assurance':'Review is a declared external judgment; the tool does not authenticate reviewers or prove semantics.'}
    validate_schema('review-package',pack)
    return pack


def _replace_file(path: Path, content: bytes, mode: int) -> None:
    fd,name=tempfile.mkstemp(prefix='.dsh-doc-write-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        os.chmod(name,mode)
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def apply_plan(repo, plan, review, *, dry_run=False, allow_in_place=False, allow_self_review=False):
    validate_plan(plan)
    assurance=_review_assurance(plan,review,allow_self_review)
    if plan['open_conflicts']: raise ValueError('unresolved authority conflicts; prepare a separate conflict-free scope')
    before=plan['repository_snapshot']; now=snapshot(repo); root=Path(now['root'])
    if now['root']!=before['root']: raise ValueError('plan belongs to another checkout')
    expected=copy.deepcopy(before)
    for c in plan['changes']:
        if c['content'] is None: expected['files'].pop(c['path'],None)
        else: expected['files'][c['path']]=c['after_digest']
    expected['digest']=_snapshot_digest(expected)
    result={'plan_digest':plan['plan_digest'],'review_assurance':assurance,
            'review_authentication':'not provided; reviewer record is an attestation',
            'migration_complete':False,'remaining':['semantic verification','fresh-session assessment'],
            'before_snapshot':before['digest'],'after_snapshot':expected['digest']}
    if now['digest']==expected['digest']:
        return {**result,'ok':True,'status':'already-applied','changed_files':[]}
    if now['digest']!=before['digest']: raise ValueError('repository changed after plan preparation; replan and rereview')
    if not now['git'] or now['dirty'] or before['dirty'] or now['tracked_control']:
        raise ValueError('apply requires a clean Git repository with untracked control artifacts')
    if not now['worktree'] and not allow_in_place:
        raise ValueError('use an isolated worktree or explicitly allow in-place writes')
    _validate_owners(root,plan)
    backups={}; directories=set()
    for c in plan['changes']:
        path=_writable(root,c['path'])
        backups[c['path']]=(path.read_bytes(),stat.S_IMODE(path.stat().st_mode)) if path.exists() else None
        folder=path.parent
        while folder!=root and not folder.exists(): directories.add(folder); folder=folder.parent
    if dry_run:
        return {**result,'ok':True,'status':'dry-run','changed_files':[],
                'would_change':[c['path'] for c in plan['changes']]}
    lock=control_directory(root)/'apply.lock'
    try:
        fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(fd)
    except FileExistsError as exc:
        raise ValueError('apply lock exists; inspect interrupted work before removing it') from exc
    changed=[]
    try:
        if snapshot(root)['digest']!=now['digest']: raise ValueError('repository changed during preflight')
        for c in plan['changes']:
            path=_writable(root,c['path']); path.parent.mkdir(parents=True,exist_ok=True)
            if c['content'] is None: path.unlink()
            else: _replace_file(path,c['content'].encode(),c['mode'])
            changed.append(c['path'])
        final=snapshot(root)
        if final['digest']!=expected['digest']:
            raise ValueError('unexpected filesystem change; rolling back only owned writes')
    except Exception:
        for rel in reversed(changed):
            path=root/rel; old=backups[rel]
            if old is None: path.unlink(missing_ok=True)
            else: _replace_file(path,old[0],old[1])
        for path in sorted(directories,key=lambda p:len(p.parts),reverse=True):
            try: path.rmdir()
            except OSError: pass
        raise
    finally:
        lock.unlink(missing_ok=True)
    return {**result,'ok':True,'status':'applied','changed_files':changed}


def validate_fresh_session(repo, value, *, allow_self_review=False):
    validate_schema('fresh-session-result',value)
    if value['snapshot_digest']!=snapshot(repo)['digest']: raise ValueError('fresh-session evidence is stale')
    if value['verdict']!='pass': raise ValueError('fresh-session assessment failed')
    topics=[item['topic'] for item in value['answers']]
    expected={'purpose','architecture','subsystem','operations','decision','authority','verification'}
    if len(topics)!=7 or set(topics)!=expected: raise ValueError('fresh-session result must answer all seven topics exactly once')
    root=Path(repo).resolve()
    for item in value['answers']:
        for rel in item['evidence']:
            path=safe_path(root,rel)
            if not path.is_file() or path.suffix!='.md': raise ValueError('fresh-session answers must cite existing documentation')
    if value['reviewer']['kind']=='self' and not allow_self_review:
        raise ValueError('self-simulation requires explicit --allow-self-review')
    return {'ok':True,'assurance':'degraded-self-simulation' if value['reviewer']['kind']=='self' else 'declared-fresh-session-pass',
            'authentication':'not provided; evidence is a reviewer attestation', 'limitations':value['limitations']}
