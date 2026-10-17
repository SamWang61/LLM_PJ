"""Temporary private Cloud Run command override for deterministic race checks.

No HTTP control endpoint exists. Only a short-lived, fixture-scoped Atlas control
record can pause a PURCHASE after stock/order/item writes, before commit. The
normal container command is restored after the probe. Never run in production.
"""
import os
import time
from datetime import datetime, timezone

if (os.environ.get('K_SERVICE') != 'vibecart-acceptance-pr21'
        or os.environ.get('CLOUD_ACCEPTANCE_MODE') != 'true'
        or os.environ.get('CLOUD_ACCEPTANCE_DB') != 'vibecart_acceptance_pr21'
        or os.environ.get('CLOUD_PREVIEW_READ_ONLY') != 'false'):
    raise RuntimeError('Private acceptance command only')

from VibeCart_AI.services.sku_cart_service import CartService
original = CartService._behavior


def paused_behavior(self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    if args[3] != 'PURCHASE' or self.db.name != 'vibecart_acceptance_pr21':
        return result
    uid = args[0]
    user = self.db.users.find_one({'_id': uid})
    if not user or not user.get('acceptance_run', '').startswith('ren-txn-'):
        return result
    control = self.db.acceptance_probe_controls.find_one_and_update(
        {'user_id': uid, 'phase': 'armed', 'expires_at': {'$gt': datetime.now(timezone.utc)}},
        {'$set': {'phase': 'reached', 'reached_at': datetime.now(timezone.utc)}})
    if control:
        if control.get('mode') == 'driver_error':
            from pymongo.errors import AutoReconnect
            self.db.acceptance_probe_controls.update_one({'_id': control['_id']},
                {'$set': {'phase': 'fault_injected'}})
            raise AutoReconnect('Controlled private acceptance driver exception')
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            row = self.db.acceptance_probe_controls.find_one({'_id': control['_id']})
            if row and row.get('phase') == 'release':
                return result
            time.sleep(.05)
        raise RuntimeError('Acceptance barrier timed out; transaction must abort')
    return result


CartService._behavior = paused_behavior
from gunicorn.app.base import BaseApplication
from cloud_runtime import create_cloud_app


class AcceptanceServer(BaseApplication):
    def load_config(self):
        for key, value in {'bind': '0.0.0.0:' + os.environ.get('PORT', '8080'),
                           'workers': 1, 'threads': 4, 'timeout': 60}.items():
            self.cfg.set(key, value)

    def load(self):
        return create_cloud_app()


AcceptanceServer().run()
