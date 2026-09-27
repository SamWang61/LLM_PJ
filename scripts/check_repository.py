"""離線發佈檢查 / Offline publication checks (no database access)."""
from pathlib import Path
import ast
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

def main():
    raw = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT)
    paths = [Path(p.decode('utf-8')) for p in raw.split(b'\0') if p]
    if not paths:
        print('No tracked/staged files; stage reviewed files first.')
        return 1
    errors = []
    text_count = 0
    for rel in paths:
        p = ROOT / rel
        name = p.name.lower()
        if (name.startswith('.env') and name != '.env.example') or any(part in {'.venv', '__pycache__', '.codex', '.backup-state', 'node_modules'} for part in rel.parts):
            errors.append(f'{rel}: forbidden private/generated path')
        if p.suffix.lower() in {'.pem', '.key', '.p12', '.mp4', '.pdf', '.zip'} or p.stat().st_size >= 100 * 1024 * 1024:
            errors.append(f'{rel}: private or externally managed artifact')
        if p.suffix.lower() not in {'.md', '.py', '.html', '.css', '.yml', '.yaml', '.json', '.xml', '.txt', '.bat', '.csv'} and not name.startswith('.'):
            continue
        try:
            text = p.read_text(encoding='utf-8-sig')
        except UnicodeError:
            errors.append(f'{rel}: invalid UTF-8')
            continue
        text_count += 1
        if p.suffix == '.py':
            try:
                ast.parse(text)
            except SyntaxError:
                errors.append(f'{rel}: invalid Python syntax')
        patterns = [r'gh[pousr]_[A-Za-z0-9]{30,}', r'github_pat_[A-Za-z0-9_]{40,}',
                    r'AKIA[0-9A-Z]{16}', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
        if any(re.search(pattern, text) for pattern in patterns):
            errors.append(f'{rel}: possible credential (value withheld)')
        if p.suffix == '.md':
            for target in re.findall(r'\]\(([^\n]+?)\)', text):
                target = target.strip('<>').split('#', 1)[0]
                if not target or re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                    continue
                if not (p.parent / unquote(target)).exists():
                    errors.append(f'{rel}: missing local link {target}')
    for message in errors:
        print(message)
    print(f'{len(paths)} files; {text_count} UTF-8 texts; {len(errors)} errors')
    return int(bool(errors))

if __name__ == '__main__':
    sys.exit(main())
