"""產生可稽核檔案清冊 / Generate an auditable file inventory.

Reads project text and hashes artifacts; never exports secret contents.
Local dependency/cache trees are counted separately and not traversed.
"""
from pathlib import Path
import csv
import hashlib
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.codex', '.backup-state'}
TEXT = {'.md', '.py', '.html', '.css', '.yml', '.yaml', '.txt', '.json', '.xml', '.bat', '.toml'}

def secret(path):
    name = path.name.lower()
    return (name.startswith('.env') and name != '.env.example') or any(x in name for x in ('credential', 'service-account', 'service_account')) or path.suffix.lower() in {'.pem', '.key', '.p12'}

def main():
    rows, excluded, issues = [], [], []
    def onerror(error):
        issues.append({'path': str(error.filename), 'error': type(error).__name__})
    for folder, dirs, files in os.walk(ROOT, onerror=onerror, followlinks=False):
        for name in list(dirs):
            p = Path(folder) / name
            if name in SKIP or p.is_symlink():
                excluded.append(p.relative_to(ROOT).as_posix())
                dirs.remove(name)
        for name in files:
            p = Path(folder) / name
            rel = p.relative_to(ROOT).as_posix()
            if rel.startswith('docs/inventory/'):
                continue
            try:
                size = p.stat().st_size
                if secret(p):
                    rows.append([rel, size, 'private / 機密', '', 'not read / 未讀取內容'])
                    continue
                with p.open('rb') as f:
                    digest = hashlib.file_digest(f, 'sha256').hexdigest()
                status = 'binary hashed / 二進位雜湊'
                if p.suffix.lower() in TEXT or name.startswith('.'):
                    content = p.read_text(encoding='utf-8-sig')
                    status = f'text read / 文字讀取 ({len(content.splitlines())} lines)'
                category = 'source / 原始碼' if p.suffix in {'.py', '.html', '.css', '.bat'} else 'document / 文件'
                if p.suffix.lower() in {'.pdf', '.mp4', '.mov', '.zip'}:
                    category = 'Drive artifact / 雲端大型附件'
                rows.append([rel, size, category, digest, status])
            except (OSError, UnicodeError) as error:
                issues.append({'path': rel, 'error': type(error).__name__})
    out = ROOT / 'docs/inventory'
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'files.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['path / 路徑', 'bytes / 大小', 'category / 類別', 'sha256', 'inspection / 讀取範圍'])
        w.writerows(sorted(rows))
    groups = {}
    for row in rows:
        if row[3]:
            groups.setdefault(row[3], []).append(row[0])
    result = {'files': len(rows), 'bytes': sum(r[1] for r in rows), 'excluded_trees': sorted(excluded), 'errors': issues,
              'identical_files': [p for p in groups.values() if len(p) > 1]}
    (out / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
