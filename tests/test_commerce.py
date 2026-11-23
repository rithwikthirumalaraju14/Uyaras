import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text as sql_text
from sqlalchemy.engine import make_url

from app.commerce import create_app
from app.store import Store, users


class CommerceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        url = 'sqlite:///'+str(Path(self.directory.name)/'test.db')
        if os.getenv('COMMERCE_TEST_DATABASE_URL'):
            base_url = os.environ['COMMERCE_TEST_DATABASE_URL']
            admin_engine = create_engine(base_url)
            schema = 'commerce_test_'+uuid.uuid4().hex
            with admin_engine.begin() as conn:
                conn.execute(sql_text('CREATE SCHEMA '+schema))
            def cleanup_schema():
                with admin_engine.begin() as conn:
                    conn.execute(sql_text('DROP SCHEMA '+schema+' CASCADE'))
                admin_engine.dispose()
            self.addCleanup(cleanup_schema)
            url = make_url(base_url).update_query_dict({'options': '-csearch_path='+schema}).render_as_string(hide_password=False)
        self.store = Store(url)
        self.addCleanup(self.store.engine.dispose)
        self.store.seed()
        self.app = create_app(self.store)
        self.alice = self.client('alice@example.test')
        self.bob = self.client('bob@example.test')
        self.store.owner('owner@example.test', 'owner-password-long')
        self.owner = TestClient(self.app)
        self.addCleanup(self.owner.close)
        self.start(self.owner)
        r = self.owner.post('/api/v1/auth/login', json={'email': 'owner@example.test', 'password': 'owner-password-long'})
        self.owner.headers['X-CSRF-Token'] = r.json()['csrf']
        self.sku = self.alice.get('/api/v1/products').json()['items'][0]['variants'][0]['sku']

    def start(self, client):
        client.headers['X-CSRF-Token'] = client.get('/api/v1/session').json()['csrf']

    def client(self, email):
        client = TestClient(self.app)
        self.addCleanup(client.close)
        self.start(client)
        r = client.post('/api/v1/auth/register', json={'name': email.split('@')[0], 'email': email, 'password': 'a-long-test-password'})
        self.assertEqual(r.status_code, 200, r.text)
        client.headers['X-CSRF-Token'] = r.json()['csrf']
        return client

    def post(self, client, path, data, expected=200, **kwargs):
        r = client.post('/api/v1'+path, json=data, **kwargs)
        self.assertEqual(r.status_code, expected, r.text)
        return r.json()

    def prepared(self, client=None, method='COD', qty=1):
        client = client or self.alice
        self.post(client, '/cart/items', {'sku': self.sku, 'quantity': qty})
        a = self.post(client, '/addresses', dict(name='Sample', phone='9999999999', line='Test Lane', city='Hyderabad', state='Telangana', pin='500001'))
        return self.post(client, '/checkout/quote', dict(address_id=a['id'], pin=a['pin'], method=method))

    def order(self, client=None, method='COD', qty=1):
        client = client or self.alice
        q = self.prepared(client, method, qty)
        return self.post(client, '/checkout/orders', {'quote_id': q['id']}, headers={'Idempotency-Key': 'key-'+q['id']})

    def advance(self, o):
        for action in ('process', 'pack', 'ship', 'deliver'):
            o = self.post(self.owner, '/admin/orders/'+o['id'], dict(action=action, tracking='TRACK-001'))
        return o

    def test_auth_rotation_csrf_ownership_and_roles(self):
        o = self.order()
        self.assertEqual(self.bob.get('/api/v1/orders/'+o['id']).status_code, 404)
        self.assertEqual(self.alice.get('/api/v1/admin/orders').status_code, 403)
        self.post(self.alice, '/cart/items', {'sku': self.sku, 'quantity': 1}, 403, headers={'X-CSRF-Token': 'invalid'})
        self.post(self.alice, '/cart/items', {'sku': self.sku, 'quantity': 1}, 403, headers={'Origin': 'https://untrusted.example'})
        token = self.alice.cookies.get('commerce_session')
        self.post(self.alice, '/auth/logout', {})
        self.assertNotEqual(token, self.alice.cookies.get('commerce_session'))
        self.assertEqual(self.alice.get('/api/v1/orders').status_code, 401)

    def test_quote_expiry_and_server_price(self):
        q = self.prepared()
        with self.store.transaction() as (_, s):
            s['products'][next(p['id'] for p in s['products'].values() if any(v['sku'] == self.sku for v in p['variants']))]['price'] += 100
        self.post(self.alice, '/checkout/orders', {'quote_id': q['id'], 'total': 1}, 409, headers={'Idempotency-Key': 'stale'})
        with self.store.transaction() as (_, s):
            self.assertFalse(s['orders'])
            self.assertEqual(s['stock'][self.sku]['reserved'], 0)

    def test_idempotency_and_snapshots(self):
        q = self.prepared()
        payload, headers = {'quote_id': q['id']}, {'Idempotency-Key': 'same-key'}
        first = self.post(self.alice, '/checkout/orders', payload, headers=headers)
        again = self.post(self.alice, '/checkout/orders', payload, headers=headers)
        self.assertEqual(first['id'], again['id'])
        self.post(self.alice, '/checkout/orders', {'quote_id': 'different'}, 409, headers=headers)
        with self.store.transaction() as (_, s):
            for p in s['products'].values():
                p.update(price=999999, name='Changed')
        self.assertEqual(first['lines'], self.alice.get('/api/v1/orders/'+first['id']).json()['lines'])

    def test_last_unit_concurrency(self):
        with self.store.transaction() as (_, s):
            s['stock'][self.sku]['on_hand'] = 1
        qa, qb = self.prepared(self.alice), self.prepared(self.bob)
        def place(pair):
            client, q = pair
            return client.post('/api/v1/checkout/orders', json={'quote_id': q['id']}, headers={'Idempotency-Key': q['id']}).status_code
        with ThreadPoolExecutor(2) as executor:
            results = list(executor.map(place, [(self.alice, qa), (self.bob, qb)]))
        self.assertEqual(sorted(results), [200, 409])
        with self.store.transaction() as (_, s):
            self.assertEqual(s['stock'][self.sku]['reserved'], 1)
            self.assertEqual(len(s['orders']), 1)

    def test_unsupported_pin_and_cod(self):
        self.post(self.alice, '/cart/items', {'sku': self.sku, 'quantity': 1})
        for pin in ['999999', '520001']:
            a = self.post(self.alice, '/addresses', dict(name='Sample', phone='9999999999', line='Test', city='City', state='State', pin=pin))
            self.post(self.alice, '/checkout/quote', dict(address_id=a['id'], pin=pin, method='COD'), 409)

    def test_signed_duplicate_and_late_payment(self):
        o = self.order(method='Prepaid')
        with self.store.transaction() as (_, s):
            s['orders'][o['id']]['expires'] = 0
        body = json.dumps(dict(order_id=o['id'], event_id='capture-1', amount=o['total'], currency='INR')).encode()
        signature = hmac.new(b'fixture-secret', body, hashlib.sha256).hexdigest()
        with patch.dict(os.environ, PAYMENT_WEBHOOK_SECRET='fixture-secret'):
            self.assertEqual(self.alice.post('/api/v1/payments/webhooks/sandbox', content=body, headers={'X-Signature': 'invalid'}).status_code, 401)
            for _ in range(2):
                self.assertEqual(self.alice.post('/api/v1/payments/webhooks/sandbox', content=body, headers={'X-Signature': signature}).status_code, 200)
        result = self.alice.get('/api/v1/orders/'+o['id']).json()
        self.assertTrue(result['reconciliation'])
        self.assertFalse(result['held'])
        self.assertEqual(result['status'], 'Payment expired')
        self.post(self.owner, '/admin/orders/'+o['id'], {'action': 'process'}, 409)
        self.post(self.owner, '/admin/orders/'+o['id'], {'action': 'refund', 'amount': o['total'], 'reference': 'MANUAL-REF-1'})
        self.post(self.owner, '/admin/orders/'+o['id'], {'action': 'refund', 'amount': 1, 'reference': 'MANUAL-REF-2'}, 409)

    def test_failed_payment_retry_and_expiry_release_once(self):
        o = self.order(method='Prepaid')
        self.post(self.alice, '/orders/'+o['id']+'/sandbox-payment', {'outcome': 'failed'})
        self.post(self.alice, '/orders/'+o['id']+'/payment-retry', {})
        with self.store.transaction() as (_, s):
            self.assertEqual(s['stock'][self.sku]['reserved'], 1)
            s['orders'][o['id']]['expires'] = 0
        for _ in range(2):
            self.alice.get('/api/v1/orders')
        with self.store.transaction() as (_, s):
            self.assertEqual(s['stock'][self.sku]['reserved'], 0)

    def test_cod_collection_remittance_and_partial_return(self):
        o = self.advance(self.order(qty=2))
        self.assertEqual(o['payment'], 'COD due')
        self.post(self.owner, '/admin/orders/'+o['id'], {'action': 'remit', 'reference': 'R'}, 409)
        self.post(self.owner, '/admin/orders/'+o['id'], {'action': 'collect', 'reference': 'COLLECTION-1'})
        self.post(self.owner, '/admin/orders/'+o['id'], {'action': 'remit', 'reference': 'REMIT-1'})
        r = self.post(self.alice, '/orders/'+o['id']+'/returns', {'sku': self.sku, 'quantity': 1, 'reason': 'Wrong fit'})
        self.post(self.alice, '/orders/'+o['id']+'/returns', {'sku': self.sku, 'quantity': 2, 'reason': 'Wrong fit'}, 409)
        for status in ['Approved', 'Received']:
            self.post(self.owner, '/admin/orders/'+o['id'], {'action': 'return', 'return_id': r['id'], 'status': status, 'reason': 'Inspected'})
        payload = dict(action='return', return_id=r['id'], status='Closed', reason='Restockable', amount=o['lines'][0]['price'], restock=True, reference='REF-1')
        self.post(self.owner, '/admin/orders/'+o['id'], {**payload, 'amount': o['total']}, 422)
        self.post(self.owner, '/admin/orders/'+o['id'], payload)
        self.post(self.owner, '/admin/orders/'+o['id'], payload, 409)
        with self.store.transaction() as (_, s):
            self.assertEqual(s['stock'][self.sku]['on_hand'], 9)
            self.assertEqual(s['stock'][self.sku]['reserved'], 0)

    def test_password_recovery_single_use_revokes_sessions(self):
        self.post(self.alice, '/auth/forgot-password', {'email': 'alice@example.test'})
        with self.store.transaction() as (_, s):
            token = next(n['token'] for n in s['outbox'] if n.get('kind') == 'password_reset')
        self.post(self.bob, '/auth/reset-password', {'token': token, 'password': 'changed-test-password'})
        self.assertEqual(self.alice.get('/api/v1/me').status_code, 401)
        self.post(self.bob, '/auth/reset-password', {'token': token, 'password': 'changed-again-password'}, 400)

    def test_hidden_category_cycle_and_variant_uniqueness(self):
        self.post(self.owner, '/admin/categories', dict(id='men', slug='men', name='Men', parent_id='men', published=True), 409)
        p = next(iter(self.owner.get('/api/v1/admin/products').json()['items'].values()))
        p['variants'].append(p['variants'][0])
        self.post(self.owner, '/admin/products', p, 409)
        self.post(self.owner, '/admin/categories', dict(id='men', slug='men', name='Men', parent_id=None, published=False))
        self.assertTrue(all(p['category'] != 'men' for p in self.alice.get('/api/v1/products').json()['items']))

    def test_reserved_stock_cannot_be_adjusted_away(self):
        self.order()
        self.post(self.owner, '/admin/stock', {'sku': self.sku, 'delta': -10, 'reason': 'Invalid reduction'}, 409)
        with self.store.transaction() as (_, s):
            self.assertEqual(s['stock'][self.sku], dict(on_hand=10, reserved=1, low_stock=3))

    def test_staff_cancellation_and_quote_consumption(self):
        q = self.prepared()
        order = self.post(self.alice, '/checkout/orders', {'quote_id': q['id']}, headers={'Idempotency-Key': 'first'})
        self.post(self.owner, '/admin/orders/'+order['id'], {'action': 'cancel', 'reason': 'Customer requested cancellation'})
        self.post(self.alice, '/cart/items', {'sku': self.sku, 'quantity': 1})
        self.post(self.alice, '/checkout/orders', {'quote_id': q['id']}, 409, headers={'Idempotency-Key': 'second'})
        with self.store.transaction() as (_, state):
            self.assertEqual(state['stock'][self.sku]['reserved'], 0)

    def test_role_enforcement_and_worker_expiry(self):
        from app.manage import work
        customer_id = self.alice.get('/api/v1/me').json()['user']['id']
        self.post(self.owner, '/admin/staff', {'id': customer_id, 'role': 'Analyst'})
        self.assertEqual(self.alice.get('/api/v1/admin/stock').status_code, 200)
        self.post(self.alice, '/admin/stock', {'sku': self.sku, 'delta': 1, 'reason': 'Forbidden'}, 403)
        self.post(self.alice, '/admin/staff', {'id': customer_id, 'role': 'Owner'}, 403)
        order = self.order(method='Prepaid')
        with self.store.transaction() as (_, state):
            state['orders'][order['id']]['expires'] = 0
        with patch.dict(os.environ, SMTP_HOST=''):
            work(self.store)
        with self.store.transaction() as (_, state):
            self.assertEqual(state['orders'][order['id']]['status'], 'Payment expired')
            self.assertEqual(state['stock'][self.sku]['reserved'], 0)

    def test_rate_limit_failed_logins_persists(self):
        # setUp already made one owner login from this same test IP.
        for _ in range(29):
            self.post(self.alice, '/auth/login', {'email': 'notfound@example.test', 'password': 'wrong-long-password'}, 401)
        self.post(self.alice, '/auth/login', {'email': 'notfound@example.test', 'password': 'wrong-long-password'}, 429)

    def test_persistence_and_public_pages(self):
        o = self.order()
        reopened = Store(self.store.url)
        self.addCleanup(reopened.engine.dispose)
        with reopened.transaction() as (_, s):
            self.assertIn(o['id'], s['orders'])
        for path in ['/', '/shop', '/account', '/cart', '/policies', '/admin', '/assets/app.js', '/art/M01-pine.webp']:
            self.assertEqual(self.alice.get(path).status_code, 200, path)
        self.assertEqual(self.alice.get('/api/v1/not-a-real-route').status_code, 404)


if __name__ == '__main__':
    unittest.main()
