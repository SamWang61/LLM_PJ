"""N06: real faults on three disposable localhost mongod processes only.

No Atlas URI, .env or existing database is accepted. Failpoints are limited to
the generated appName. Flask's real routes run through its local WSGI client;
these results are not remote HTTPS, production outage or human acceptance.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId, Decimal128, json_util
from pymongo import MongoClient, monitoring
from pymongo.errors import PyMongoError
from werkzeug.security import generate_password_hash


def require(value, message):
    if not value:
        raise RuntimeError(message)


class Trace(monitoring.CommandListener, monitoring.ConnectionPoolListener):
    def __init__(self):
        self.rows = []
        self.cleared = 0
        self.lock = threading.Lock()

    def started(self, event):
        if event.command_name in {'insert', 'update', 'commitTransaction', 'abortTransaction'}:
            with self.lock:
                self.rows.append({'command': event.command_name,
                    'txn': int(event.command['txnNumber']) if 'txnNumber' in event.command else None,
                    'start': bool(event.command.get('startTransaction'))})

    def succeeded(self, event):
        pass

    def failed(self, event):
        with self.lock:
            self.rows.append({'failed': event.command_name,
                'code': event.failure.get('code') if isinstance(event.failure, dict) else None})

    def pool_cleared(self, event):
        with self.lock:
            self.cleared += 1

    def pool_created(self, event): pass
    def pool_ready(self, event): pass
    def pool_closed(self, event): pass
    def connection_created(self, event): pass
    def connection_ready(self, event): pass
    def connection_closed(self, event): pass
    def connection_check_out_started(self, event): pass
    def connection_check_out_failed(self, event): pass
    def connection_checked_out(self, event): pass
    def connection_checked_in(self, event): pass


def snapshot(db):
    result = {}
    for name in sorted(db.list_collection_names()):
        rows = list(db[name].find().sort('_id', 1))
        data = json_util.dumps(rows, sort_keys=True, separators=(',', ':')).encode()
        result[name] = {'count': len(rows), 'sha256': hashlib.sha256(data).hexdigest()}
    return result


def owned_database(name, run_id):
    require(name.startswith('ren_n06_' + run_id + '_') and name.isidentifier(), 'Foreign cleanup database refused')


def owned_data_path(path, root):
    require(path.resolve().parent == root.resolve() and path.name in {'node0', 'node1', 'node2'},
            'Foreign process data directory refused')


class Cluster:
    def __init__(self, exe):
        self.exe = Path(exe).resolve(strict=True)
        require(self.exe.name.lower() in {'mongod', 'mongod.exe'}, 'mongod binary required')
        self.root = Path(tempfile.mkdtemp(prefix='ren-n06-local-')).resolve()
        self.run_id = uuid4().hex[:12]
        self.set_name = 'renN06' + self.run_id
        self.processes, self.nodes, self.names, self.data_paths = [], [], [], []
        self.client = None
        self.cleaned = False

    def start(self):
        reserved = [socket.socket() for _ in range(3)]
        try:
            for sock in reserved:
                sock.bind(('127.0.0.1', 0))
            ports = [sock.getsockname()[1] for sock in reserved]
            for i, port in enumerate(ports):
                reserved[i].close()
                data = self.root / ('node' + str(i))
                data.mkdir()
                self.data_paths.append(data)
                options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                process = subprocess.Popen([str(self.exe), '--dbpath', str(data), '--port', str(port),
                    '--bind_ip', '127.0.0.1', '--replSet', self.set_name,
                    '--setParameter', 'enableTestCommands=1', '--wiredTigerCacheSizeGB', '0.25',
                    '--oplogSize', '16', '--logpath', str(self.root / ('node'+str(i)+'.log'))],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
                self.processes.append(process)
                self.nodes.append(MongoClient('mongodb://127.0.0.1:'+str(port)+'/?directConnection=true',
                    serverSelectionTimeoutMS=500, socketTimeoutMS=10000, appname='n06-controller'))
            for node in self.nodes:
                deadline = time.monotonic() + 20
                while True:
                    try:
                        node.admin.command('ping')
                        break
                    except PyMongoError:
                        require(time.monotonic() < deadline, 'Local mongod failed to start')
                        time.sleep(.15)
            self.nodes[0].admin.command('replSetInitiate', {'_id': self.set_name,
                'members': [{'_id': i, 'host': '127.0.0.1:'+str(port), 'priority': 1} for i,port in enumerate(ports)],
                'settings': {'electionTimeoutMillis': 1000, 'heartbeatIntervalMillis': 500}})
            self.uri = 'mongodb://' + ','.join('127.0.0.1:'+str(p) for p in ports) + '/?replicaSet=' + self.set_name
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=10000, appname='n06-controller',
                                      heartbeatFrequencyMS=500)
            self.client.admin.command('ping')
            deadline = time.monotonic() + 20
            while True:
                status = self.client.admin.command('replSetGetStatus')
                if sorted(m['state'] for m in status['members']) == [1, 2, 2]:
                    break
                require(time.monotonic() < deadline, 'Three healthy replica members required')
                time.sleep(.2)
        finally:
            for sock in reserved:
                sock.close()

    def failpoint(self, mode, data=None):
        for node in self.nodes:
            node.admin.command({'configureFailPoint': 'failCommand', 'mode': mode, **({'data': data} if data else {})})

    def close(self):
        try:
            for node in self.nodes:
                try: node.admin.command({'configureFailPoint': 'failCommand', 'mode': 'off'})
                except PyMongoError: pass
            if self.client is not None:
                for name in self.names:
                    owned_database(name, self.run_id)
                    self.client.drop_database(name)
                require(not any(n.startswith('ren_n06_'+self.run_id+'_') for n in self.client.list_database_names()),
                        'Fixture cleanup incomplete')
                self.client.close()
        finally:
            for node in self.nodes: node.close()
            for process in self.processes:
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait(timeout=5)
            require(all(p.poll() is not None for p in self.processes), 'Local process cleanup incomplete')
            for path in self.data_paths:
                owned_data_path(path, self.root)
                shutil.rmtree(path)
        self.cleaned = True


def one_case(cluster, case, names, create_app, CartService, *, sustained=False):
    name = 'ren_n06_'+cluster.run_id+'_'+case
    owned_database(name, cluster.run_id)
    cluster.names.append(name)
    control = cluster.client[name]
    for collection in names:
        control.create_collection(collection)
    control.carts.create_index('user_id', unique=True, partialFilterExpression={'status':'active'})
    control.cart_events.create_index([('user_id',1),('operation_id',1)], unique=True)
    control.orders.create_index([('user_id',1),('checkout_id',1)], unique=True)
    control.behavior_events.create_index('event_id', unique=True)
    uid, pid, sid, category = (ObjectId() for _ in range(4))
    password = uuid4().hex
    control.users.insert_one({'_id':uid,'schema_version':4,'status':'active','is_active':True,
        'role':'customer','email':case+'@n06.example.invalid','display_name':'N06 local fixture',
        'password_hash':generate_password_hash(password)})
    control.products.insert_one({'_id':pid,'schema_version':4,'status':'active','product_code':case,
        'product_name':'N06 local fixture','major_category_id':category,'minor_category_id':category,
        'category_path':['local','test'],'average_rating_display':0})
    control.product_skus.insert_one({'_id':sid,'schema_version':4,'product_id':pid,'status':'active',
        'sku_code':case,'variant_attributes':{},'price':Decimal128('10.00'),
        'stock_quantity':4,'available_quantity':4,'reserved_quantity':0,'safety_stock':0})
    trace = Trace()
    app_name = 'ren-n06-'+cluster.run_id+'-'+case
    client = MongoClient(cluster.uri, appname=app_name, event_listeners=[trace],
        serverSelectionTimeoutMS=2000, socketTimeoutMS=350, heartbeatFrequencyMS=500,
        maxPoolSize=3, waitQueueTimeoutMS=500)
    db = client[name]
    state = {'callbacks':0,'stepdown':False,'watch_fault':False,'rollback_witnesses':[]}

    class Observed(CartService):
        def _run(self, callback):
            def recorded(session):
                if state['watch_fault'] and state['callbacks']:
                    witness = snapshot(control)
                    require(witness == before, 'Retry began with partial writes')
                    state['rollback_witnesses'].append(witness)
                state['callbacks'] += 1
                return callback(session)
            try:
                return super()._run(recorded)
            except PyMongoError as error:
                state['last_mongo_error'] = type(error).__name__+': '+str(error)[:300]
                raise

        def _behavior(self, *args, **kwargs):
            if case == 'primary_change' and args[3] == 'PURCHASE' and not state['stepdown']:
                state['stepdown'] = True
                original = cluster.client.admin.command('hello')['primary']
                state['old_primary'] = original
                node = next(n for n in cluster.nodes if n.admin.command('hello').get('isWritablePrimary'))
                try: node.admin.command({'replSetStepDown':15,'force':True})
                except PyMongoError: pass
                deadline = time.monotonic() + 15
                while True:
                    hello = cluster.client.admin.command('hello')
                    if hello.get('isWritablePrimary') and hello.get('primary') != original:
                        state['new_primary'] = hello['primary']
                        break
                    require(time.monotonic() < deadline, 'New primary unavailable')
                    time.sleep(.1)
                require(state['old_primary'] != state['new_primary'], 'Primary did not change')
                state['stepdown_rollback_equal'] = snapshot(control) == before
                require(state['stepdown_rollback_equal'], 'Stepdown leaked partial transaction')
            return super()._behavior(*args, **kwargs)

    app = create_app({'TESTING':True,'SECRET_KEY':'disposable-n06-local-only','DATA_MODE':'v4',
        'MONGO_URI':cluster.uri,'MONGO_DB':name,'ENABLE_CHECKOUT':True,
        'AI_RECOMMENDATIONS_ENABLED':False,'AI_SUMMARY_ENABLED':False,'AI_FREE_QUESTION_ENABLED':False,
        'CART_SERVICE_FACTORY':lambda db,**kw: Observed(db,**kw)})
    from flask import g
    @app.before_request
    def local_db(): g.db = db
    browser = app.test_client()
    browser.get('/auth/login')
    with browser.session_transaction() as session: csrf = session['csrf_token']
    require(browser.post('/auth/login',data={'csrf_token':csrf,'email':case+'@n06.example.invalid',
                                           'password':password}).status_code == 302, 'Fixture login failed')
    browser.get('/auth/login')
    with browser.session_transaction() as session: csrf = session['csrf_token']
    headers = {'X-CSRF-Token':csrf}
    try:
        added = browser.post('/cart/add/'+str(pid),json={'sku_id':str(sid),'quantity':1,'operation_id':'n06-add'},headers=headers)
        require(added.status_code == 200, 'Fixture cart add failed')
        cart = control.carts.find_one({'user_id':uid})
        payload = {'cart_id':str(cart['_id']),'expected_revision':cart['revision'],'checkout_id':'n06-checkout'}
        before = snapshot(control)
        trace.rows.clear(); trace.cleared = 0; state['callbacks'] = 0
        config = {'failCommands':['insert'],'appName':app_name}
        if case == 'network_timeout': config.update(blockConnection=True,blockTimeMS=6500)
        elif case == 'socket_reset': config.update(closeConnection=True)
        elif case == 'write_conflict': config.update(errorCode=112,errorLabels=['TransientTransactionError'],blockConnection=True,blockTimeMS=100)
        elif case == 'pool_failure': config.update(errorCode=91,errorLabels=['TransientTransactionError'],blockConnection=True,blockTimeMS=100)
        elif case == 'commit_unknown': config.update(failCommands=['commitTransaction'],writeConcernError={
            'code':91,'codeName':'ShutdownInProgress','errmsg':'n06 local commit acknowledgement failure'},
            errorLabels=['UnknownTransactionCommitResult'])
        if case != 'primary_change': cluster.failpoint('alwaysOn' if sustained else {'times':1},config)
        state['watch_fault'] = True
        started = time.monotonic()
        try:
            failed = browser.post('/checkout',json=payload,headers=headers)
            elapsed = time.monotonic() - started
        finally:
            state['watch_fault'] = False
            cluster.failpoint('off')
        require(elapsed < (11 if sustained else 30), 'Fault exceeded local observation budget')
        attempts = state['callbacks']
        rows = list(trace.rows)
        cleared = trace.cleared
        if sustained:
            require(failed.status_code == 503, 'Sustained fault did not return 503')
            require(1 <= attempts <= 40, 'Sustained fault retried too many callbacks')
            after_fault = snapshot(control)
            if case == 'commit_unknown':
                commits = [row for row in rows if row.get('command')=='commitTransaction']
                require(attempts == 1 and len(commits) >= 2 and len({row['txn'] for row in commits}) == 1,
                        'Unknown commit replayed transaction body or changed transaction number')
            else:
                require(after_fault == before, 'Sustained fault left partial writes')
            require(any('failed' in row for row in rows), 'No Mongo command failure observed')
        elif case not in {'commit_unknown','primary_change'}:
            require(failed.status_code==200,'Single-fault automatic retry failed: '+case)
            after_fault = snapshot(control)
            require(attempts >= 2 and state['rollback_witnesses'], 'No post-abort retry snapshot')
            require(any('failed' in row for row in rows),'No actual Mongo command failure observed')
            if case in {'socket_reset','pool_failure'}: require(cleared>0,'No actual pool reset observed')
        else:
            require(failed.status_code==200,'Transparent recovery failed: '+case)
            after_fault = snapshot(control)
            if case=='commit_unknown':
                commits = [row for row in rows if row.get('command')=='commitTransaction']
                require(len(commits)>=2 and len({row['txn'] for row in commits})==1 and attempts==1,
                        'Unknown commit must retry same transaction, not callback')
            else: require(state['stepdown'] and state['stepdown_rollback_equal'] and attempts>=2,'Primary retry missing')
        # Keep the original process, Flask app, browser cookie and MongoClient.
        # Replacing the client here would hide a pool/topology recovery failure.
        require(db.client is client, 'Recovery must use the original MongoClient')
        recovery_started = time.monotonic()
        recovery_responses = []
        recovery_attempts = 0
        for recovery_attempts in range(1, 6):
            recovered = browser.post('/checkout',json=payload,headers=headers)
            recovery_responses.append(recovered.status_code)
            if recovered.status_code != 503:
                break
            if recovery_attempts < 5:
                time.sleep(.25)
        replay = browser.post('/checkout',json=payload,headers=headers)
        require(recovered.status_code==replay.status_code==200 and recovered.json['id']==replay.json['id'],
                'Same-key recovery/replay mismatch: recovery='+str(recovered.status_code)+
                ', replay='+str(replay.status_code)+', mongo='+str(state.get('last_mongo_error')))
        require(control.orders.count_documents({})==control.order_items.count_documents({})==1,'Duplicate/missing orders')
        require(control.product_skus.find_one({'_id':sid})['available_quantity']==3,'Stock not decremented once')
        require(control.behavior_events.count_documents({'event_type':'PURCHASE'})==1,'Duplicate purchase event')
        require(control.cart_events.count_documents({'event_type':'CHECKOUT'})==1,'Duplicate checkout receipt')
        expected_changed={'users','carts','orders','order_items','product_skus','cart_events','behavior_events'}
        after=snapshot(control)
        require(all(before[k]==after[k] for k in before if k not in expected_changed),'Unrelated collection changed')
        conflict=browser.post('/checkout',json={**payload,'expected_revision':999},headers=headers)
        require(conflict.status_code==409 and snapshot(control)==after,'Conflict replay wrote data')
        return {'case':case,'status':'passed','fault_http':failed.status_code,'fault_callbacks':attempts,
            'fault_spec':{k:v for k,v in config.items() if k!='appName'} if case!='primary_change'
                         else {'replSetStepDown':15,'force':True,'during':'PURCHASE after order/item writes'},
            'failed_commands':sum('failed' in r for r in rows),'pool_clears':cleared,
            'commit_attempts':sum(r.get('command')=='commitTransaction' for r in rows),
            'rollback_equal':all(w == before for w in state['rollback_witnesses']) if case!='commit_unknown' else None,
            'post_abort_snapshot_count':len(state['rollback_witnesses']),
            'post_abort_snapshots':state['rollback_witnesses'],'driver_commands':rows,
            'request_elapsed_seconds':round(elapsed,3),
            'fault_mode':'sustained server fault; bounded application retry' if sustained else 'single server fault; bounded application recovery',
            'unknown_commit_retried_same_transaction':case=='commit_unknown',
            'primary_changed':state['stepdown'],'primary_before':state.get('old_primary'),
            'primary_after':state.get('new_primary'),'recovery_http':recovered.status_code,'replay_http':replay.status_code,
            'replay_same_order':True,'recovery_client_replaced':False,'recovery_attempts':recovery_attempts,
            'recovery_http_attempts':recovery_responses,
            'recovery_elapsed_seconds':round(time.monotonic()-recovery_started,3),
            'recovery_worker':'original Flask app and MongoClient; no process/client restart',
            'conflicting_replay_http':conflict.status_code,'stock_decrements':1,
            'collection_count':len(before),'before':before,'after_fault':after_fault,'after_recovery':after,
            'unrelated_collections_unchanged':True,'validator_scope':'indexes only; not strict schema acceptance'}
    finally:
        client.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mongod',required=True,type=Path)
    parser.add_argument('--mode',choices=('single','sustained'),default='single')
    parser.add_argument('--case',choices=('network_timeout','socket_reset','write_conflict','pool_failure',
                                          'commit_unknown','primary_change'))
    parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    require(not args.report.exists(),'Existing evidence report must not be overwritten')
    root=args.repo.resolve(strict=True)
    sys.path.insert(0,str(root/'MuscleCore分析資料/website'))
    sys.path.insert(0,str(root))
    sys.path.insert(0,str(root/'VibeCart_AI/MongoDB'))
    import app as app_module
    from VibeCart_AI.services.sku_cart_service import CartService
    from schema_active_v4 import SCHEMAS
    cluster=Cluster(args.mongod)
    report={'schema_version':1,'checked_at':datetime.now(timezone.utc).isoformat(),'status':'failed',
        'scope':'three disposable localhost processes and local WSGI routes','remote_acceptance':False,
        'atlas_accessed':False,'mode':args.mode,'cases':[],'processes_stopped':False,'fixtures_removed':False,
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    try:
        cluster.start()
        with patch.object(app_module,'load_dotenv',lambda *a,**k:False),patch.dict(os.environ,{'APP_ENV_FILE':''}):
            cases = ('network_timeout','socket_reset','write_conflict','pool_failure','commit_unknown') if args.mode=='sustained' else (
                'network_timeout','socket_reset','write_conflict','pool_failure','commit_unknown','primary_change')
            if args.case:
                require(args.case in cases,'Case unavailable in selected mode')
                cases=(args.case,)
            for case in cases:
                print(json.dumps({'case':case,'phase':'start'}),flush=True)
                result=one_case(cluster,case,sorted(SCHEMAS),app_module.create_app,CartService,
                                sustained=args.mode=='sustained')
                report['cases'].append(result)
                print(json.dumps({k:v for k,v in result.items() if k not in {
                    'before','after_fault','after_recovery','post_abort_snapshots','driver_commands'}}),flush=True)
        report['status']='passed'
    except Exception as error:
        report['error_type']=type(error).__name__
        report['error']=str(error) if isinstance(error,RuntimeError) else 'Local matrix stopped; details in local logs'
    finally:
        try:
            cluster.close()
            report['processes_stopped']=report['fixtures_removed']=cluster.cleaned
        except Exception as error:
            report['status']='cleanup-failed'; report['cleanup_error_type']=type(error).__name__
        report['local_log_directory']=str(cluster.root)
        args.report.parent.mkdir(parents=True,exist_ok=True)
        with args.report.open('x',encoding='utf-8',newline='\n') as handle: json.dump(report,handle,ensure_ascii=False,indent=2);handle.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}))
    return 0 if report['status']=='passed' and cluster.cleaned else 1


if __name__=='__main__':
    raise SystemExit(main())
