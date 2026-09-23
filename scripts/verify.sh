#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -n "$(git ls-files '*.pyc' '__pycache__')" ]]; then
  echo "Tracked Python bytecode is forbidden." >&2
  git ls-files '*.pyc' '__pycache__' >&2
  exit 1
fi

python - <<'PY'
import ast
from pathlib import Path

for path in sorted(Path('.').rglob('*.py')):
    if any(part in {'.git', '.venv', '__pycache__'} for part in path.parts):
        continue
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
print('python-ast: PASS')
PY

python -m unittest discover -s tests -v
python scripts/verify_docs.py --repo . --json
python skills/dsh-doc-audits/scripts/repo_docs.py verify --repo . --json
python skills/dsh-doc-audits/scripts/repo_docs.py audit --repo . --json
git diff --check

echo "verify: PASS"
