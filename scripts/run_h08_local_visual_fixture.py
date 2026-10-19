"""Disposable loopback-only H08 visual fixture; never connects to Atlas."""

import argparse
import json
import os
from pathlib import Path
import sys
from threading import Timer
from unittest.mock import patch

import mongomock
from bson import Decimal128, ObjectId
from flask import g, jsonify
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'MuscleCore分析資料' / 'website'))
from app import create_app  # noqa: E402
from app.services.sku_gateway import CartService  # noqa: E402


class OfflineCart(CartService):
    def _run(self, callback):
        # This visual fixture cannot prove MongoDB transaction behavior.
        return callback(None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lifetime-seconds', type=int, default=180)
    args = parser.parse_args()
    if not 15 <= args.lifetime_seconds <= 600:
        parser.error('Lifetime must be 15-600 seconds')

    db = mongomock.MongoClient().h08_visual_only
    uid, pid, sid, category = (ObjectId() for _ in range(4))
    db.users.insert_one({'_id': uid, 'schema_version': 4, 'status': 'active',
        'is_active': True, 'role': 'customer', 'email': 'h08-sim@example.invalid',
        'display_name': 'H08 模擬會員',
        'password_hash': generate_password_hash('h08-disposable-local-fixture')})
    db.products.insert_one({'_id': pid, 'schema_version': 4, 'status': 'active',
        'product_code': 'H08-SIM', 'product_name': 'H08 隔離測試商品',
        'major_category_id': category, 'minor_category_id': category,
        'category_path': ['local', 'visual'], 'average_rating_display': 4.0,
        'description': '僅供本機手機尺寸模擬，不代表正式商品。'})
    db.product_skus.insert_one({'_id': sid, 'schema_version': 4, 'product_id': pid,
        'status': 'active', 'sku_code': 'H08-SIM-1',
        'variant_attributes': {'規格': '1件'}, 'price': Decimal128('10.25'),
        'stock_quantity': 10, 'available_quantity': 10,
        'reserved_quantity': 0, 'safety_stock': 0})

    with patch.dict(os.environ, {'APP_ENV_FILE': ''}), patch('app.load_dotenv', lambda *a, **k: False):
        app = create_app({'TESTING': True, 'SECRET_KEY': 'disposable-h08-loopback-only',
            'DATA_MODE': 'v4', 'ENABLE_CHECKOUT': True,
            'CART_SERVICE_FACTORY': lambda database, **kw: OfflineCart(database, **kw),
            'AI_RECOMMENDATIONS_ENABLED': False, 'AI_SUMMARY_ENABLED': False,
            'AI_FREE_QUESTION_ENABLED': False})

    @app.before_request
    def fixture_db():
        g.db = db

    @app.get('/__h08_fixture_meta')
    def fixture_meta():
        return jsonify({'product_id': str(pid), 'scope': 'loopback mongomock visual fixture'})

    server = make_server('127.0.0.1', 0, app, threaded=True)
    timer = Timer(args.lifetime_seconds, server.shutdown)
    timer.daemon = True
    timer.start()
    print(json.dumps({'base_url': f'http://127.0.0.1:{server.server_port}',
        'scope': 'loopback mongomock visual fixture', 'lifetime_seconds': args.lifetime_seconds}), flush=True)
    try:
        server.serve_forever()
    finally:
        timer.cancel()
        server.server_close()


if __name__ == '__main__':
    main()
