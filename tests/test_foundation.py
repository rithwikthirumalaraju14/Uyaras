import json
import os
import sqlite3
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.catalog import PUBLIC_CATEGORIES
from app.database import DatabaseUnavailable
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]


class LocalStore:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.executescript((ROOT/'app/schema_0001.sql').read_text())

    def ready(self):
        return True

    def categories(self, page, page_size):
        return [dict(r) for r in self.conn.execute(PUBLIC_CATEGORIES,
                    {'limit': page_size, 'offset': (page-1)*page_size})]


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.store = LocalStore()
        self.addCleanup(self.store.conn.close)
        self.client = TestClient(create_app(self.store))
        self.addCleanup(self.client.close)

    def test_live_and_ready(self):
        for route, state in [('live', 'alive'), ('ready', 'ready')]:
            response = self.client.get('/health/'+route)
            self.assertEqual(response.json(), {'status': state})
            self.assertIn('x-request-id', response.headers)

    def test_ready_failure(self):
        self.store.ready = lambda: False
        r = self.client.get('/health/ready')
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()['error']['request_id'], r.headers['x-request-id'])

    def test_invalid_page(self):
        for query in ['page=0','page_size=101','page=x']:
            r = self.client.get('/api/v1/categories?'+query)
            self.assertEqual(r.status_code, 422)
            self.assertEqual(r.json()['error']['code'], 'invalid_input')

    def test_published_tree_and_pagination(self):
        self.store.conn.executemany('INSERT INTO category VALUES (?,?,?,?,?)', [
            ('1',None,'women','Women',1),('2',None,'men','Men',1),
            ('3','1','tops','Tops',1),('4',None,'hidden','Hidden',0),
            ('5','4','private-child','Hidden branch',1)])
        for page, slug in enumerate(['men','tops','women'], start=1):
            r = self.client.get('/api/v1/categories',params={'page':page,'page_size':1})
            self.assertEqual([x['slug'] for x in r.json()['items']], [slug])
        self.assertEqual(self.client.get('/api/v1/categories?page=4&page_size=1').json()['items'], [])

    def test_catalog_outage(self):
        def fail(*args):
            raise DatabaseUnavailable()
        self.store.categories = fail
        self.assertEqual(self.client.get('/api/v1/categories').status_code, 503)

    def test_sku_and_available_stock_constraints(self):
        db = self.store.conn
        db.execute("INSERT INTO product (id,slug,name) VALUES ('p','tee','Tee')")
        db.execute("INSERT INTO inventory_location VALUES ('w','LOCAL','Test')")
        db.execute("INSERT INTO variant VALUES ('v','p','TEST-M','M','Gray',100,TRUE)")
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO variant VALUES ('v2','p','TEST-M','S','Gray',100,TRUE)")
        for on_hand, reserved in [(-1,0),(1,-1),(1,2)]:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO inventory_balance VALUES ('v','w',?,?)",(on_hand,reserved))

    def test_contract_matches_live_methods(self):
        design = json.loads((ROOT/'docs/openapi.json').read_text())
        live = self.client.get('/openapi.json').json()
        for path, methods in live['paths'].items():
            for method, details in methods.items():
                self.assertEqual(design['paths'][path][method], {**details,'x-stage':'implemented'})

    def test_missing_route(self):
        self.assertEqual(self.client.get('/missing').json()['error']['code'], 'http_error')


@unittest.skipUnless(os.environ.get('DATABASE_URL'), 'PostgreSQL integration requires migrated DATABASE_URL')
class PostgresTest(unittest.TestCase):
    def test_migrated_database_and_catalog(self):
        with TestClient(create_app()) as client:
            self.assertEqual(client.get('/health/ready').status_code, 200)
            self.assertIsInstance(client.get('/api/v1/categories').json()['items'], list)
