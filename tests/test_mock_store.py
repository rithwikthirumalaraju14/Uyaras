import unittest
from fastapi.testclient import TestClient
from mock_store.main import app

class MockStoreTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_variants_have_zero_stock_and_distinct_skus(self):
        data = self.client.get('/mock/catalog').json()
        variants = [v for p in data['products'] for v in p['variants']]
        self.assertEqual(len(variants), 32)
        self.assertEqual(len({v['sku'] for v in variants}), len(variants))
        self.assertTrue(all(v['stock'] == 0 for v in variants))

    def test_region_is_only_proposed(self):
        data = self.client.get('/mock/catalog').json()
        self.assertEqual(data['regions_considered'], ['Andhra Pradesh','Telangana'])
        self.assertEqual(data['confirmed_pins'], [])
        self.assertIsNone(data['cod_eligible'])
        self.assertIsNone(data['shipping_fee_paise'])
        self.assertFalse(data['ordering_enabled'])
        self.assertEqual(self.client.post('/checkout/orders').status_code,404)

    def test_filter_and_preview(self):
        for audience in ('Men','Women'):
            products = self.client.get('/mock/catalog',params={'audience':audience}).json()['products']
            self.assertEqual([p['audience'] for p in products], [audience]*2)
        self.assertNotIn('__CATALOG_DATA__',self.client.get('/').text)
