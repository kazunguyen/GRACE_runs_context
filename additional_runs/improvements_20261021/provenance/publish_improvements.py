from pathlib import Path
import ast
import collections
import datetime
import hashlib
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

BASE = Path('D:/JUNIOR/LabThayTho')
NAMES = ['GRACE-H1-SecurityProjection', 'GRACE-H3-CalibratedCascade', 'GRACE-H3-BenchmarkEnsemble']
SHARE = BASE / 'SHARE_36_RUNS_CONTEXT8192_20261020_205918'
DEST = Path('additional_runs/improvements_20261021')
LIMIT = 100 * 1024 * 1024
EXTS = {'.json', '.jsonl', '.md', '.csv', '.txt', '.yaml', '.yml', '.ipynb'}
TASK = Path(__file__).resolve().parent / 'publish_improvements_state'
TASK.mkdir(exist_ok=True)

def git(root, *args, input=None, check=True):
    p = subprocess.run(['git', '-C', str(root), *args], input=input, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(f'git {args}: {p.stderr.decode("utf-8", "replace")[:1000]}')
    return p

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode())

def sha(data):
    return hashlib.sha256(data).hexdigest()

def secrets():
    values = set()
    for p in [BASE / '.env', *(BASE / n / '.env' for n in NAMES)]:
        if p.is_file():
            for line in p.read_text(encoding='utf-8-sig').splitlines():
                k, sep, v = line.partition('=')
                if sep and re.search(r'(?:API|TOKEN|SECRET|PASSWORD|PRIVATE_KEY)', k, re.I):
                    v = v.strip().strip('"\'')
                    if len(v) >= 10:
                        values.add(v)
    for n in NAMES:
        for p in (BASE / n / 'notebooks').glob('*.ipynb'):
            obj = json.loads(p.read_text(encoding='utf-8'))
            for cell in obj['cells']:
                src = ''.join(cell.get('source', []))
                for m in re.finditer(r'(?m)^\s*(?:FPT_API|API_KEY|OPENAI_API_KEY)\s*=\s*([\'\"])([^\n]*?)\1', src):
                    v = m[2]
                    if len(v) >= 10 and not any(t in v for t in ['REDACT', 'ENTER_', 'YOUR_', 'DAN_', 'your_']):
                        values.add(v)
    return values

SECRETS = secrets()

def public_bytes(p):
    data = p.read_bytes()
    out = data
    for v in SECRETS:
        out = out.replace(v.encode(), b'')
    if out != data and p.suffix != '.ipynb':
        raise RuntimeError(f'Credential-like value in non-notebook artifact: {p}')
    return out, out != data

def candidates(root):
    found = set()
    for dirname in ['runs', 'results', 'artifacts', 'archives', 'cache/responses', 'cache/prior_runs', 'exports']:
        d = root / dirname
        if not d.exists():
            continue
        for p in d.rglob('*'):
            if p.is_file() and p.suffix in EXTS and '__pycache__' not in p.parts and '.ipynb_checkpoints' not in p.parts:
                found.add(p)
    return sorted(found)

def source_files(root):
    paths = git(root, 'diff', '--name-only').stdout.decode().splitlines()
    paths += git(root, 'ls-files', '--others', '--exclude-standard').stdout.decode().splitlines()
    return sorted({root / p for p in paths if not p.startswith(('tools/joern/', 'exports/', 'runs/', 'cache/', 'artifacts/', 'archives/'))})

def check_sizes(root, paths):
    staged = git(root, 'diff', '--cached', '--name-only', '-z').stdout.decode().split('\0')
    all_paths = set(paths) | {root / p for p in staged if p}
    oversized = [p for p in all_paths if p.is_file() and p.stat().st_size > LIMIT]
    if oversized:
        ignore = root / '.gitignore'
        text = ignore.read_text(encoding='utf-8') if ignore.exists() else ''
        for p in oversized:
            rule = '/' + p.relative_to(root).as_posix()
            if rule not in text.splitlines():
                text += '\n' + rule + '\n'
            git(root, 'restore', '--staged', '--', p.relative_to(root).as_posix(), check=False)
        ignore.write_bytes(text.encode())
    return [p for p in paths if p not in oversized]

def stage(root, paths, force=False, pathspec_roots=None):
    paths = check_sizes(root, paths)
    normal = []
    def inspect(p):
        if not p.is_file():return None
        data, sanitized = public_bytes(p)
        return p.relative_to(root).as_posix(), sanitized, data if sanitized else None
    with ThreadPoolExecutor(max_workers=4) as pool:
        for start in range(0,len(paths),500):
            for result in pool.map(inspect,paths[start:start+500]):
                if result is None:continue
                rel,sanitized,data=result
                if sanitized:
                    if pathspec_roots:raise RuntimeError('Directory staging requires already-sanitized files')
                    oid = git(root, 'hash-object', '-w', '--stdin', input=data).stdout.decode().strip()
                    git(root, 'update-index', '--add', '--cacheinfo', '100644,' + oid + ',' + rel)
                    print('SANITIZED INDEX ONLY', root.name, rel, flush=True)
                else:normal.append(rel)
            if start % 3000 == 0:print('INSPECTED',root.name,min(start+500,len(paths)),'/',len(paths),flush=True)
    if normal:
        # One add handles all selected paths without Windows command-line limits.
        check_sizes(root, [root / p for p in normal])
        args = ['add'] + (['-f'] if force else []) + ['--pathspec-from-file=-', '--pathspec-file-nul']
        git(root, *args, input=('\0'.join(pathspec_roots or normal)+'\0').encode())
        print('STAGED', root.name, len(normal), flush=True)
    return paths

def commit(root, message):
    staged = git(root, 'diff', '--cached', '--name-only', '-z').stdout.decode().split('\0')
    if not any(staged):
        return git(root, 'rev-parse', 'HEAD').stdout.decode().strip()
    check_sizes(root, [root / p for p in staged if p])
    print(git(root, 'diff', '--cached', '--stat').stdout.decode()[-1800:], flush=True)
    print(git(root, 'commit', '-m', message).stdout.decode()[-1000:], flush=True)
    return git(root, 'rev-parse', 'HEAD').stdout.decode().strip()

def archive():
    summary = {}
    for name in NAMES:
        root = BASE / name
        rows = []
        paths = candidates(root)
        # Also preserve configuration, source, notebooks and provenance required to interpret outputs.
        for dirname in ['configs', 'notebooks', 'provenance', 'docs', 'grace_h1', 'grace_h3', 'grace_h3v2']:
            d = root / dirname
            if d.exists():
                paths += [p for p in d.rglob('*') if p.is_file() and p.suffix in EXTS | {'.py'} and '__pycache__' not in p.parts]
        paths += [p for p in root.iterdir() if p.is_file() and (p.name == 'README.md' or p.name.startswith('requirements'))]
        paths = sorted(set(paths))
        size = 0
        def copy_one(p):
            before = p.stat()
            content, sanitized = public_bytes(p)
            after = p.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise RuntimeError(f'File changed during snapshot: {p}')
            rel = p.relative_to(root)
            target = SHARE / DEST / name / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            already_equal=target.exists() and sha(target.read_bytes())==sha(content)
            if not already_equal:
                target.write_bytes(content)
            if not already_equal and sha(target.read_bytes()) != sha(content):
                raise RuntimeError(f'Copy checksum mismatch: {target}')
            return {'source': str(p), 'path': rel.as_posix(), 'bytes': len(content), 'sha256': sha(content),
                    'source_sha256':sha(p.read_bytes()) if sanitized else sha(content),'notebook_api_key_redacted': sanitized}
        with ThreadPoolExecutor(max_workers=4) as pool:
            for start in range(0,len(paths),500):
                batch=list(pool.map(copy_one,paths[start:start+500]))
                rows.extend(batch);size+=sum(item['bytes'] for item in batch)
                if start % 5000 == 0:print(name,'copied',min(start+500,len(paths)),'/',len(paths),flush=True)
        manifest = {'schema':'grace_improvement_archive_v1', 'project':name, 'source_root':str(root),
                    'source_branch':git(root,'branch','--show-current').stdout.decode().strip(),
                    'source_commit':git(root,'rev-parse','HEAD').stdout.decode().strip(),
                    'created_local':datetime.datetime.now().isoformat(), 'files':rows,
                    'scope':'Textual run artifacts, raw response cache, manifests, historical outputs and source snapshot; excludes H2, weights, embeddings, graph cache and runtime binaries. Originals retained for resume.'}
        dump(SHARE / DEST / name / 'snapshot_manifest.json', manifest)
        summary[name] = {'files':len(rows), 'bytes':size, 'manifest':(DEST / name / 'snapshot_manifest.json').as_posix()}
        print(name, summary[name], flush=True)
    dump(TASK / 'archive_summary.json', summary)

def main():
    mode = sys.argv[1]
    if mode == 'inventory':
        data = {}
        for n in NAMES:
            r=BASE/n;paths=candidates(r)
            data[n] = {'files':len(paths),'bytes':sum(p.stat().st_size for p in paths),'oversized': [str(p) for p in paths if p.stat().st_size>LIMIT]}
        dump(TASK/'inventory.json',data);print(json.dumps(data,indent=2))
    elif mode == 'source':
        for n in NAMES:
            root=BASE/n
            if git(root,'diff','--cached','--name-only').stdout.strip():raise RuntimeError('Unexpected pre-existing staging')
            paths=source_files(root)
            print('SOURCE',n,[str(p.relative_to(root)) for p in paths],flush=True)
            stage(root,paths)
            commit(root,'chore(workflow): save notebooks and inference updates')
    elif mode == 'artifacts':
        for n in NAMES:
            root=BASE/n;paths=candidates(root)
            tracked=set(git(root,'ls-files','-z').stdout.decode().split('\0'))
            changed=set(git(root,'diff','--name-only','-z').stdout.decode().split('\0'))
            paths=[p for p in paths if p.relative_to(root).as_posix() not in tracked or p.relative_to(root).as_posix() in changed]
            print('ARTIFACTS',n,len(paths),flush=True)
            stage(root,paths,force=True)
            commit(root,'chore(results): archive inference artifacts')
    elif mode == 'archive':archive()
    elif mode == 'supplements':
        ledger=json.loads((SHARE/'bang_quan_ly_run_cai_tien.json').read_text(encoding='utf-8'))
        for n in NAMES:
            root=BASE/n;paths=[]
            for entry in ledger['llm_runs']:
                if entry['project']!=n:continue
                folder=root/entry['run']
                paths += [folder/'raw_responses_archive.jsonl',folder/'ledger_metrics.json']
            stage(root,paths,force=True)
            commit(root,'chore(results): add per-run raw response archives')
    elif mode == 'share-commit':
        paths=[p for p in (SHARE/DEST).rglob('*') if p.is_file()]
        paths += [SHARE/'bang_quan_ly_run_cai_tien.md',SHARE/'bang_quan_ly_run_cai_tien.json']
        paths += [SHARE/'README.md']
        stage(SHARE,paths,pathspec_roots=[DEST.as_posix(),'bang_quan_ly_run_cai_tien.md','bang_quan_ly_run_cai_tien.json','README.md'])
        commit(SHARE,'docs(results): archive improvements and run ledger')

if __name__ == '__main__':main()
