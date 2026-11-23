import os
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from mock_store.main import app


class RehearsalApiTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = patch.dict(os.environ, {'STUDIO_DEMO_DB': tmp.name+'/demo.sqlite3'})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_session_isolation_and_transactions(self):
        data = self.client.get('/mock/session').json()
        sku = data['products'][0]['variants'][0]['sku']
        headers = {'X-Studio-Demo':'1'}
        url = '/mock/action'
        item = {'type':'bag','sku':sku,'qty':2}
        self.assertEqual(self.client.post(url,json=item).status_code,403)
        self.assertEqual(self.client.post(url,headers=headers,json=item).status_code,200)
        self.assertEqual(self.client.post(url,headers=headers,json={**item,'qty':99}).status_code,409)
        self.assertEqual(self.client.get('/mock/session').json()['bags']['guest'][sku],2)
        with TestClient(app) as other:
            self.assertEqual(other.get('/mock/session').json()['bags']['guest'],{})

    def test_anonymous_mutation_and_staff_guard(self):
        headers={'X-Studio-Demo':'1'}
        payload={'type':'promo','code':'NEW','percent':25,'active':True}
        self.assertEqual(self.client.post('/mock/action',json=payload,headers=headers).status_code,401)
        self.client.get('/mock/session')
        self.assertEqual(self.client.post('/mock/action',json=payload,headers=headers).status_code,409)

    def test_signed_callback_and_atomic_last_unit(self):
        import hashlib
        import hmac
        import json
        from concurrent.futures import ThreadPoolExecutor
        self.client.get('/mock/session')
        headers={'X-Studio-Demo':'1'}
        def post(action):
            return self.client.post('/mock/action',json=action,headers=headers)
        sku='DEMO-M01-PINE-S'
        post({'type':'role','value':'Owner'})
        post({'type':'stock','sku':sku,'delta':-2,'reason':'Last unit fixture'})
        post({'type':'role','value':'Shopper'})
        post({'type':'signin','key':'demo'})
        post({'type':'bag','sku':sku,'qty':1})
        quote={'lines':[{'sku':sku,'name':'Everyday crew','colour':'Pine','size':'S','price':399,'qty':1}],
               'subtotal':399,'discount':0,'shipping':30,'tax':0,'total':429,'area':'Andhra Pradesh fixture','code':''}
        submit={'type':'order','pin':'AP-DEMO','method':'Prepaid','outcome':'pending',
                'address':'Studio Lane, sample address','expected':json.dumps(quote,separators=(',',':'))}
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(post,[{**submit,'key':'first'},{**submit,'key':'second'}]))
        self.assertEqual(sorted(r.status_code for r in responses),[200,409])
        order_id=next(r for r in responses if r.status_code==200).json()['result']
        raw=json.dumps({'order_id':order_id,'event_id':'event-1','amount':429,'currency':'INR'}).encode()
        sig=hmac.new(b'fixture-only',raw,hashlib.sha256).hexdigest()
        with patch.dict(os.environ,{'STUDIO_MOCK_WEBHOOK_SECRET':'fixture-only'}):
            url='/mock/provider/payment-event'
            self.assertEqual(self.client.post(url,content=raw).status_code,401)
            for _ in range(2):
                self.assertEqual(self.client.post(url,content=raw,headers={'X-Mock-Signature':sig}).status_code,200)
        order=self.client.get('/mock/session').json()['orders'][0]
        self.assertEqual(order['payment'],'Paid')
        self.assertEqual(order['receipts'],['event-1'])
