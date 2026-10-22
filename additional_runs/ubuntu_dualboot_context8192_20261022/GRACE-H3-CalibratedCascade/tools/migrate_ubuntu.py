"""Copy H3 Cascade CPU state from Data to native Ubuntu, preserving existing files."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import time

EXCLUDED = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '.ipynb_checkpoints', 'bundles', 'exports', 'joern'}


def checksum(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def migrate(source, destination=None):
    if os.name != 'posix':
        raise RuntimeError('Run this migration after booting native Ubuntu.')
    source = Path(source).resolve()
    destination = Path(destination or Path.home() / '.local/share/grace-h3').expanduser().resolve()
    target = destination / 'GRACE-H3-CalibratedCascade'
    if not (source / 'grace_h3/workflow.py').is_file():
        raise ValueError(f'Not a Cascade project: {source}')
    if source == target or source in target.parents or target in source.parents:
        raise ValueError('Source is already the Ubuntu project; open its notebook directly.')
    marker = target / 'ubuntu-migration.json'
    if marker.exists():
        print(f'Existing Ubuntu state retained: {target}', flush=True)
        return target
    files = []
    for folder, directories, names in os.walk(source, followlinks=False):
        directories[:] = sorted(d for d in directories if d not in EXCLUDED and not d.endswith('.egg-info'))
        for name in sorted(names):
            path = Path(folder) / name
            if path.is_symlink() or name == '.env' or name.endswith(('.tmp', '.pyc')):
                continue
            files.append(path)
    destination.mkdir(parents=True, exist_ok=True)
    remaining = sum(p.stat().st_size for p in files if not (target / p.relative_to(source)).exists())
    if shutil.disk_usage(destination).free < remaining + 2 * 1024**3:
        raise RuntimeError('Insufficient native Ubuntu disk space: need the remaining copy plus 2 GiB scratch headroom.')
    print(f'Copy/resume {len(files)} files to {target}; existing differing files are never overwritten.', flush=True)
    started = last = time.monotonic()
    copied = reused = 0
    for number, path in enumerate(files, 1):
        dest = target / path.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if dest.stat().st_size != path.stat().st_size or checksum(dest) != checksum(path):
                raise RuntimeError(f'Existing Ubuntu file differs: {dest}. Preserve the Ubuntu state; select another destination for a fresh copy.')
            reused += 1
        else:
            temporary = dest.with_name(dest.name + '.migration-tmp')
            shutil.copy2(path, temporary)
            if checksum(temporary) != checksum(path):
                raise RuntimeError(f'Copy checksum failed: {path}')
            temporary.replace(dest)
            copied += 1
        if number % 500 == 0 or time.monotonic() - last >= 10 or number == len(files):
            print(f'Migration {number}/{len(files)} | copied={copied} reused={reused}', flush=True)
            last = time.monotonic()
    marker.write_text(json.dumps({'source': str(source), 'target': str(target), 'files': len(files),
                                 'copied': copied, 'reused': reused, 'seconds': time.monotonic() - started,
                                 'original_preserved': True, 'credentials_copied': False}, indent=2) + '\n')
    print(f'Open {target}/notebooks/prepare-cpu-ubuntu.ipynb', flush=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--destination', type=Path, default=Path.home() / '.local/share/grace-h3')
    args = parser.parse_args()
    migrate(args.source, args.destination)
