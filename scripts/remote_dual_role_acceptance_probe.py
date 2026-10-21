"""Same-email role acceptance using only registered disposable private-db users."""
import json,re,secrets,sys
from datetime import datetime,timezone
from bson import ObjectId
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from remote_d4_consumer_probe import DATABASE,verify_scope,verify_database_roles,require,login,page
from remote_member_transaction_checks import csrf_headers,replay_session

def cleanup(db,marker,ids):
    require(db.name==DATABASE and marker.startswith('sam-dual-role-') and len(ids)==6
            and all(isinstance(x,ObjectId) for x in ids),'Dual-role fixture cleanup scope mismatch')
    result={}
    for name,query in [('behavior_events',{'user_id':{'$in':ids}}),('auth_sessions',{'user_id':{'$in':ids}}),
                       ('users',{'_id':{'$in':ids},'acceptance_run':marker})]:
        try:
            result[name+'_deleted']=db[name].delete_many(query).deleted_count
            result[name+'_remaining']=db[name].count_documents(query)
        except Exception:result[name+'_remaining']='readback_failed'
    result['verified']=all(result.get(x+'_remaining')==0 for x in ['users','auth_sessions','behavior_events'])
    return result

def run(config):
    verify_scope(config)
    client=MongoClient(config['mongo_uri'],serverSelectionTimeoutMS=15000)
    verify_database_roles(client);db=client[DATABASE]
    marker=config.get('fixture_marker') or 'sam-dual-role-'+secrets.token_hex(8)
    require(isinstance(marker,str) and re.fullmatch(r'sam-dual-role-[a-f0-9]{16}',marker),'Unregistered dual-role fixture marker')
    ids=[ObjectId() for _ in range(6)]
    passwords={'customer':secrets.token_urlsafe(24),'admin':secrets.token_urlsafe(24)}
    hashes={r:generate_password_hash(p) for r,p in passwords.items()}
    emails=[marker+'-'+str(i)+'@example.invalid' for i in range(3)]
    base=config['service_url'].rstrip('/');sessions=[]
    report={'status':'failed','probe_id':marker,'revision':config['revision'],'image':config['image'],
            'scope':'six disposable same-email/role identities; no real people or real passwords','fixture_ids':[str(x) for x in ids]}
    def signin(email,password,session=None,**extra):
        if session is None:
            import requests
            session=requests.Session();session.headers['Authorization']='Bearer '+config['id_token'];sessions.append(session)
        csrf=page(session,base+'/auth/login').select_one('input[name="csrf_token"]')
        require(csrf is not None,'Login CSRF missing')
        response=session.post(base+'/auth/login',data={'email':email,'password':password,'csrf_token':csrf['value'],**extra},timeout=45,allow_redirects=False)
        return session,response
    def signout(session):
        csrf=page(session,base+'/').select_one('form[action="/auth/logout"] input[name="csrf_token"]')
        require(csrf is not None,'Logout CSRF missing')
        response=session.post(base+'/auth/logout',data={'csrf_token':csrf['value']},timeout=45,allow_redirects=False)
        require(response.status_code in (302,303),'Own logout failed')
        require(session.get(base+'/admin/',timeout=45,allow_redirects=False).status_code==302,'Logged-out admin accepted')
    try:
        now=datetime.now(timezone.utc)
        docs=[{'_id':ids[i*2+j],'schema_version':4,'email':email,'role':role,'auth_provider':'local',
               'display_name':'同Email隔離驗收','password_hash':hashes[role],'is_active':True,'status':'active',
               'acceptance_run':marker,'created_at':now,'updated_at':now}
              for i,email in enumerate(emails) for j,role in enumerate(['customer','admin'])]
        db.users.insert_many(docs)
        rows=[]
        for i,email in enumerate(emails):
            for role in ['customer','admin']:
                session,response=signin(email,passwords[role]);require(response.status_code==302,'Role login failed')
                require(response.headers.get('Location')==('/admin/' if role=='admin' else '/'),'Role landing differs')
                admin=session.get(base+'/admin/',timeout=45,allow_redirects=False)
                require(admin.status_code==(200 if role=='admin' else 302),'Role boundary differs')
                csrf=page(session,base+'/').select_one('form[action="/auth/logout"] input[name="csrf_token"]')['value']
                before=db.users.find_one({'email':email,'role':role})['password_hash']
                require(session.get(base+'/auth/password',timeout=45,allow_redirects=False).status_code==403,'Password GET allowed')
                rejected=session.post(base+'/auth/password',data={'csrf_token':csrf,'password':'unrelated-test-only'},timeout=45,allow_redirects=False)
                require(rejected.status_code==403 and db.users.find_one({'email':email,'role':role})['password_hash']==before,'Password POST changed credential')
                signout(session);rows.append({'identity':i+1,'role':role,'login':302,'role_boundary':admin.status_code,'password_changes':403,'own_logout':True})
        report['six_roles']=rows
        first,_=signin(emails[0],passwords['customer']);old=replay_session(first)
        other,_=signin(emails[0],passwords['customer'])
        _,injected=signin(emails[0],passwords['customer'],first,role='admin')
        require(injected.headers.get('Location')=='/' and first.get(base+'/admin/',timeout=45,allow_redirects=False).status_code==302,'Posted role promoted customer')
        # Capture the session immediately before the same-browser role switch.
        old.close();old=replay_session(first)
        _,switched=signin(emails[0],passwords['admin'],first)
        require(switched.headers.get('Location')=='/admin/' and first.get(base+'/admin/',timeout=45).status_code==200,'Role switch failed')
        require(old.get(base+'/cart',timeout=45,allow_redirects=False).status_code==302,'Prior device session survived switch')
        require(other.get(base+'/cart',timeout=45,allow_redirects=False).status_code==200,'Other device was revoked')
        signout(first);signout(other);old.close()
        _,wrong=signin(emails[1],secrets.token_urlsafe(28));require(wrong.status_code==200,'Wrong password accepted')
        admin_id=ids[3]
        db.users.update_one({'_id':admin_id,'acceptance_run':marker},{'$set':{'password_hash':hashes['customer']}})
        anonymous,ambiguous=signin(emails[1],passwords['customer'])
        require(ambiguous.status_code==200 and anonymous.get(base+'/cart',timeout=45,allow_redirects=False).status_code==302,'Ambiguous password accepted')
        db.users.update_one({'_id':admin_id,'acceptance_run':marker},{'$set':{'password_hash':hashes['admin'],'status':'inactive','is_active':False}})
        _,disabled=signin(emails[1],passwords['admin']);require(disabled.status_code==200,'Disabled role accepted')
        report.update(status='passed',posted_role_ignored=True,role_switch_revokes_prior_device=True,other_device_preserved=True,
                      wrong_password_denied=True,ambiguous_password_denied=True,disabled_role_denied=True,
                      fixture_sessions_after_logout=db.auth_sessions.count_documents({'user_id':{'$in':ids}}))
        require(report['fixture_sessions_after_logout']==0,'Own session remains after logout')
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error) if isinstance(error,RuntimeError) else 'Dual-role probe failed')
    finally:
        report['cleanup']=cleanup(db,marker,ids)
        if not report['cleanup']['verified']:report['status']='cleanup_failed'
        for session in sessions:session.close()
        client.close()
    print(json.dumps(report,ensure_ascii=False))
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':
    try:raise SystemExit(run(json.load(sys.stdin)))
    except Exception as error:
        print(json.dumps({'status':'failed','error_type':type(error).__name__}));raise SystemExit(1)
