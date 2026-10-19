"""Run real transaction suites on one disposable credential-free local replica set.

No .env/Atlas access; only a generated sam_d5/ren acceptance database may be dropped
by the suites. The sole Docker container created here is removed in finally.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4
import xml.etree.ElementTree as ET
from pymongo import MongoClient

ROOT=Path(__file__).resolve().parents[1]


def docker(*args):
    return subprocess.run(['docker',*args],check=True,capture_output=True,text=True).stdout.strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--junit',type=Path,required=True)
    args=parser.parse_args()
    name='codex-d5-'+uuid4().hex[:12]
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'status':'failed',
            'target':'disposable credential-free localhost replica set','container_removed':False}
    created=False
    # Reserve report before provisioning; never overwrite earlier acceptance evidence.
    with args.report.open('x',encoding='utf-8',newline='\n') as output:
        try:
            # Keep an exited container until finally so startup logs and exit
            # status survive long enough to diagnose a failed CI run.
            docker('run','-d','--name',name,'-p','127.0.0.1::27017','mongo:8',
                   '--replSet','rsD5Acceptance','--bind_ip_all',
                   '--setParameter','enableTestCommands=1')
            created=True
            port=docker('port',name,'27017/tcp')
            if not port.startswith('127.0.0.1:') or not port.split(':')[1].isdigit():
                raise ValueError('Unexpected local Mongo binding')
            uri='mongodb://'+port+'/?replicaSet=rsD5Acceptance&directConnection=true'
            for _ in range(60):
                try:
                    docker('exec',name,'mongosh','--quiet','--eval',
                           'rs.initiate({_id:"rsD5Acceptance",members:[{_id:0,host:"127.0.0.1:27017"}]})')
                    break
                except subprocess.CalledProcessError: time.sleep(.5)
            else: raise RuntimeError('Replica set initialization failed')
            with MongoClient(uri,serverSelectionTimeoutMS=1000) as client:
                for _ in range(60):
                    try:
                        if client.admin.command('hello').get('isWritablePrimary'): break
                    except Exception: pass
                    time.sleep(.5)
                else: raise RuntimeError('Local primary unavailable')
                env={**os.environ,'D5_TEST_MONGO_URI':uri,'REN_TEST_MONGO_URI':uri,'PYTHONIOENCODING':'utf-8'}
                result=subprocess.run([sys.executable,'-m','pytest',
                    '../../scripts/test_admin_audit_migration.py','tests',
                    '-q','-p','no:cacheprovider','--junitxml='+str(args.junit.resolve())],
                    cwd=ROOT/'MuscleCore分析資料/website',env=env)
                suite=ET.parse(args.junit).getroot()
                suites=[suite] if suite.tag=='testsuite' else list(suite.findall('testsuite'))
                counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
                report['tests']=counts
                report['remaining_databases']=sorted(client.list_database_names())
                clean=not any(n.startswith(('sam_d5_acceptance_','ren_acceptance_')) for n in report['remaining_databases'])
                report['fixtures_removed']=clean
                if result.returncode==0 and not any(counts[k] for k in ('failures','errors','skipped')) and clean:
                    report['status']='passed'
        except Exception as error:
            report['error_type']=type(error).__name__
            if isinstance(error, RuntimeError):
                report['error_message']=str(error)[:500]
        finally:
            if created:
                try:
                    info=json.loads(docker('inspect',name))[0]
                    if info.get('Name')!='/'+name: raise ValueError('Container identity changed')
                    if report['status']!='passed':
                        state=info.get('State',{})
                        report['container_state']={key:state.get(key) for key in
                            ('Status','ExitCode','OOMKilled','Error')}
                        try:
                            report['container_logs_tail']=docker('logs','--tail','30',name)[-12000:]
                        except Exception as diagnostic_error:
                            report['diagnostic_error_type']=type(diagnostic_error).__name__
                    docker('rm','-f',name)
                    report['container_removed']=True
                except Exception:
                    report['status']='cleanup-failed'
            json.dump(report,output,indent=2);output.write('\n')
    print(json.dumps(report))
    return 0 if report['status']=='passed' and report['container_removed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
