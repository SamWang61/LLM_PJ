import base64,json,os,secrets,subprocess,sys,tempfile,urllib.request,urllib.parse,zipfile,io
from pathlib import Path

def run(bundle,config):
    target=Path(tempfile.mkdtemp(prefix='sam-role95-'));deps=target/'deps'
    subprocess.run([sys.executable,'-m','pip','install','--quiet','--disable-pip-version-check','--target',str(deps),'beautifulsoup4==4.15.0','requests==2.34.2'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(bundle))) as archive:archive.extractall(target/'scripts')
    sys.path.insert(0,str(deps));sys.path.insert(0,str(target/'scripts'))
    from pymongo import MongoClient
    from bson import ObjectId
    from remote_d4_consumer_probe import verify_database_roles,DATABASE,require
    url='http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience='+urllib.parse.quote(config.pop('audience'),safe='')+'&format=full'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'Metadata-Flavor':'Google'}),timeout=20) as response:identity=response.read().decode()
    config.update(mongo_uri=os.environ['MONGO_URI'],id_token=identity,expect_bge=False)
    results=[];index_report={'scope':DATABASE,'restored':False};client=MongoClient(os.environ['MONGO_URI'],serverSelectionTimeoutMS=15000)
    verify_database_roles(client);db=client[DATABASE]
    before=list(db.users.list_indexes())
    require(not any(x.get('unique') and list(x['key'].items())==[('email',1)] for x in before),'Existing global email index blocks isolated dual-role data')
    marker='sam-dual-role-'+secrets.token_hex(8);config['fixture_marker']=marker
    index_name=marker+'-roles';created=False
    index_report['before']=[{'name':x['name'],'key':list(x['key'].items()),'unique':x.get('unique',False)} for x in before]
    index_report['temporary_index_scope']={'acceptance_run':marker}
    try:
        db.users.create_index([('email',1),('role',1)],name=index_name,unique=True,partialFilterExpression={'acceptance_run':marker});created=True
        for file in ['remote_dual_role_acceptance_probe.py','remote_reviews_acceptance_probe.py','remote_account_acceptance_probe.py','remote_transaction_acceptance_probe.py']:
            child=subprocess.run([sys.executable,str(target/'scripts'/file)],input=json.dumps(config),capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONPATH':str(deps)},timeout=720)
            try:report=json.loads(child.stdout)
            except Exception:report={'status':'failed','error_type':'ProbeReportUnavailable'}
            result={'file':file,'code':child.returncode,'report':report}
            if file=='remote_dual_role_acceptance_probe.py' and report.get('fixture_ids'):
                ids=[ObjectId(x) for x in report['fixture_ids']]
                independent={'users':db.users.count_documents({'_id':{'$in':ids}}),'auth_sessions':db.auth_sessions.count_documents({'user_id':{'$in':ids}}),'behavior_events':db.behavior_events.count_documents({'user_id':{'$in':ids}})}
                result['independent_cleanup']=independent
                if any(independent.values()):result['code']=1;report['status']='independent_cleanup_failed'
            results.append(result);print(json.dumps({'sam_preview_job_probe':result},ensure_ascii=False),flush=True)
    finally:
        try:
            if created:db.users.drop_index(index_name)
            after=list(db.users.list_indexes())
            index_report['after']=[{'name':x['name'],'key':list(x['key'].items()),'unique':x.get('unique',False)} for x in after]
            index_report['restored']=sorted(index_report['before'],key=lambda x:x['name'])==sorted(index_report['after'],key=lambda x:x['name'])
        except Exception as error:index_report['error_type']=type(error).__name__
        client.close()
        print(json.dumps({'sam_role95_index_cleanup':index_report}),flush=True)
    passed=len(results)==4 and index_report['restored'] and all(r['code']==0 and r['report'].get('status')=='passed' and r['report'].get('cleanup',{}).get('verified') for r in results)
    print(json.dumps({'sam_preview_job_complete':{'status':'passed' if passed else 'failed','probes':len(results),'acceptance_user_indexes_restored':index_report['restored']}}),flush=True)
    return 0 if passed else 1
