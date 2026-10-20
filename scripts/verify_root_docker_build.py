"""Opt-in Docker check: exact committed root context, fake canaries and offline boot.

Requires local Docker. Uses public committed sources and fake values only; never
reads .env, connects to Atlas, pushes an image or changes Cloud Run. The temporary
source context and build logs are retained under the system temporary directory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
from uuid import uuid4

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'scripts'))
import prepare_cloud_source as source

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--report', required=True, type=Path)
parser.add_argument('--commit', default='HEAD')
args = parser.parse_args()
report_path = args.report.resolve()
if report_path.exists():
    raise ValueError('Existing verification report must not be overwritten')
sha = subprocess.check_output(['git', 'rev-parse', '--verify', args.commit + '^{commit}'],
                              cwd=root, text=True).strip()
task = Path(tempfile.mkdtemp(prefix='vibecart-root-build-'))
context = task / 'context'
context.mkdir()
archive = task / 'source.tar.gz'
count, digest = source.package(archive, sha, 'repository')
with tarfile.open(archive, 'r:gz') as tar:
    tar.extractall(context, filter='data')
    expected_context = {item.name: hashlib.sha256(tar.extractfile(item).read()).hexdigest()
                        for item in tar.getmembers() if item.isfile()}
canaries = ['.env', 'docs/private.txt', 'VibeCart_AI/MongoDB/.env',
            source.WEBSITE + '/app/.env.test', source.WEBSITE + '/app/private.key',
            source.WEBSITE + '/app/static/internal.csv',
            source.WEBSITE + '/app/__pycache__/private.py',
            source.WEBSITE + '/app/node_modules/private.js']
for name in canaries:
    path = context / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('FAKE-CONTEXT-CANARY-NO-CREDENTIALS', encoding='utf-8')
probe = task / 'ContextProbe.Dockerfile'
probe.write_text('FROM scratch\nCOPY . /\n', encoding='utf-8')
export = task / 'export'

def build(args, log_name, *, classic=False):
    with (task / log_name).open('w', encoding='utf-8') as log:
        env = {**os.environ, 'DOCKER_BUILDKIT': '0'} if classic else os.environ
        result = subprocess.run(['docker', *args], stdout=log, stderr=subprocess.STDOUT, text=True, env=env)
    if result.returncode:
        raise RuntimeError('Docker command failed; log at ' + str(task / log_name))

report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'source_sha': sha,
          'archive_files': count, 'archive_sha256': digest, 'status': 'failed'}
image = 'vibecart-root-qa:' + sha[:12]
name = 'vibecart-root-boot-' + uuid4().hex[:12]
created = False
try:
    print('Checking actual Docker context exclusion', flush=True)
    build(['buildx', 'build', '--progress=plain', '--output', 'type=local,dest=' + str(export),
           '-f', str(probe), str(context)], 'context.log')
    actual_context = {str(p.relative_to(export)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in export.rglob('*') if p.is_file()}
    assert not any(p in actual_context for p in canaries)
    assert actual_context == expected_context
    report['context_files_exact'] = True
    report['fake_secret_canaries_excluded'] = len(canaries)
    print('Building repository-root Dockerfile', flush=True)
    build(['build', '--platform', 'linux/amd64', '--build-arg', 'INSTALL_AI=false',
           '-t', image, str(context)], 'image.log', classic=True)
    report['image_builder'] = 'classic Docker (DOCKER_BUILDKIT=0); BuildKit context export also verified'
    files_code = ('import hashlib,json; from pathlib import Path; r=Path("/srv/app"); '
                  'print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() '
                  'for p in r.rglob("*") if p.is_file()}))')
    files = json.loads(subprocess.check_output(['docker', 'run', '--rm', '--network=none',
        '--entrypoint', 'python', image, '-c', files_code], text=True))
    expected_runtime = {}
    for name_in_context, file_sha in expected_context.items():
        if name_in_context in {'Dockerfile', '.dockerignore'}:
            continue
        target = name_in_context[len(source.WEBSITE) + 1:] if name_in_context.startswith(source.WEBSITE + '/') else name_in_context
        expected_runtime[target] = file_sha
    assert files == expected_runtime
    report['runtime_files_exact'] = len(files)
    report['runtime_manifest_sha256'] = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    env = ['-e', 'MONGO_URI=mongodb+srv://vibecart-ai-free.odqe25w.mongodb.net/',
           '-e', 'SECRET_KEY=root-build-offline-smoke-secret-32chars']
    boot = ('import os; from cloud_runtime import create_cloud_app; '
            'a=create_cloud_app(); assert a.test_client().get("/health/live").status_code==200; '
            'assert os.getuid()==10001; print("offline-root-container-boot-ok")')
    subprocess.run(['docker', 'run', '--rm', '--network=none', *env,
                    '--entrypoint', 'python', image, '-c', boot], check=True)
    report['offline_factory_health'] = 200
    report['runtime_uid'] = 10001
    cid = subprocess.check_output(['docker', 'run', '-d', '--network=none', '--name', name,
                                  *env, '-e', 'PORT=9099', image], text=True).strip()
    created = True
    probe_code = 'import urllib.request; assert urllib.request.urlopen("http://127.0.0.1:9099/health/live", timeout=2).status==200'
    for _ in range(30):
        result = subprocess.run(['docker', 'exec', cid, 'python', '-c', probe_code],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError('Gunicorn PORT health check failed')
    report['gunicorn_custom_port_health'] = 200
    report['image'] = image
    report['image_id'] = subprocess.check_output(['docker', 'image', 'inspect', image,
                                                 '--format', '{{.Id}}'], text=True).strip()
    report['status'] = 'passed'
except Exception as error:
    report['error_type'] = type(error).__name__
    report['error'] = str(error)
    raise
finally:
    if created:
        info = json.loads(subprocess.check_output(['docker', 'inspect', name], text=True))[0]
        assert info['Id'] == cid and info['Name'] == '/' + name
        subprocess.run(['docker', 'rm', '-f', cid], check=True, stdout=subprocess.DEVNULL)
    report['test_container_removed'] = True
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open('x', encoding='utf-8', newline='\n') as out:
        json.dump(report, out, ensure_ascii=False, indent=2)
        out.write('\n')
    print(json.dumps(report, ensure_ascii=False))
