"""Scope and response-contract guards for the Atlas-writing remote probe."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from bson import ObjectId
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from remote_reviews_acceptance_probe import cleanup, fixture_scope, grids
from remote_d4_consumer_probe import recommendations


def test_cleanup_rejects_production_database_before_deleting_anything():
    with pytest.raises(RuntimeError, match='scope'):
        cleanup(SimpleNamespace(name='vibecart_ai'), 'sam-reviews-owned',
                [ObjectId()], [ObjectId()], [], [], [], None)


@pytest.mark.parametrize('marker,users,products', [
    ('other', [ObjectId()], [ObjectId()]),
    ('sam-reviews-owned', [], [ObjectId()]),
    ('sam-reviews-owned', [ObjectId()], ['untrusted-id']),
])
def test_cleanup_requires_marker_and_registered_object_ids(marker, users, products):
    with pytest.raises(RuntimeError):
        fixture_scope(SimpleNamespace(name='vibecart_acceptance_pr21'), marker, users, products)


def test_parser_keeps_personal_grid_separate_from_cross_category():
    html = '''<section aria-label="猜你喜歡6加4"><h2>猜你喜歡 · 6＋4</h2>
    <div class="product-grid"><article class="product-card"><h3><a href="/product/own">Own</a></h3>
    <span class="reason">Personal</span></article></div>
    <div class="product-grid"><article class="product-card"><h3><a href="/product/cross">Cross</a></h3>
    <span class="reason">Explore</span></article></div></section>'''
    assert recommendations(BeautifulSoup(html, 'html.parser')) == [('/product/own', 'Personal')]
    response = SimpleNamespace(status_code=200, headers={'Cache-Control': 'private, no-store'}, text=html)
    assert grids(response) == [['own'], ['cross']]
    response.headers = {'Cache-Control': 'public'}
    with pytest.raises(RuntimeError, match='cache'):
        grids(response)


def test_legacy_recommendation_parser_remains_supported():
    soup = BeautifulSoup('<section><h2>為你精選</h2><article class="product-card">'
                         '<h3><a href="/product/a">A</a></h3><p class="reason">R</p>'
                         '</article></section>', 'html.parser')
    assert recommendations(soup) == [('/product/a', 'R')]


def test_cleanup_checks_orphan_reviews_and_every_registered_scope():
    db = MagicMock()
    db.name = 'vibecart_acceptance_pr21'
    names = ['product_reviews', 'order_items', 'orders', 'behavior_events',
             'auth_sessions', 'users', 'product_skus', 'products']
    collections = {name: MagicMock() for name in names}
    db.__getitem__.side_effect = collections.__getitem__
    db.products = collections['products']
    for name in names:
        db[name].delete_many.return_value = SimpleNamespace(deleted_count=1)
        db[name].count_documents.return_value = 0
    users, products, skus, orders, lines = [[ObjectId()] for _ in range(5)]
    result = cleanup(db, 'sam-reviews-owned', users, products, skus, orders, lines, 'owned-index')
    assert result['verified']
    db.products.drop_index.assert_called_once_with('owned-index')
    db['product_reviews'].delete_many.assert_called_once_with({'$or': [
        {'product_id': {'$in': products}}, {'order_item_id': {'$in': lines}}]})
    for name in names:
        db[name].count_documents.assert_called_once()


def test_cleanup_cannot_pass_when_index_or_dependent_row_readback_fails():
    db = MagicMock()
    db.name = 'vibecart_acceptance_pr21'
    names = ['product_reviews', 'order_items', 'orders', 'behavior_events',
             'auth_sessions', 'users', 'product_skus', 'products']
    collections = {name: MagicMock() for name in names}
    db.__getitem__.side_effect = collections.__getitem__
    db.products = collections['products']
    for name in names:
        db[name].delete_many.return_value = SimpleNamespace(deleted_count=0)
        db[name].count_documents.return_value = 0
    db.products.drop_index.side_effect = RuntimeError('unavailable')
    assert not cleanup(db, 'sam-reviews-owned', [ObjectId()], [ObjectId()], [], [], [], 'owned-index')['verified']
    db.products.drop_index.side_effect = None
    db['order_items'].count_documents.return_value = 1
    assert not cleanup(db, 'sam-reviews-owned', [ObjectId()], [ObjectId()], [], [], [], None)['verified']
