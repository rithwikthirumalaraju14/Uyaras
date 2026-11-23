"""Named PRD acceptance coverage for V1 completion work."""
from test_uyaras import setup, post, quote
from sqlalchemy import select
from sqlalchemy.orm import Session
from uyaras.models import Product, Variant, Inventory, User, DeliveryRule, OrderEvent, Outbox
from uyaras.schemas import ActionInput
from uyaras.checkout import order_action, lock_order


def test_prd15_catalog_configurable_filters_and_pagination(setup):
    engine, client = setup
    c = client()
    with Session(engine) as db, db.begin():
        category = db.scalar(select(Product.category_id))
        for i in range(27):
            p = Product(name=f"Capsule {i}", slug=f"capsule-{i}", category_id=category, status="published", fabric="Cotton")
            db.add(p); db.flush()
            v = Variant(sku=f"CAP-{i}", product_id=p.id, size="XXL", colour="Azure", price=40000+i, regular_price=50000)
            db.add(v); db.flush(); db.add(Inventory(sku=v.sku, on_hand=2))
    result = c.get('/api/v1/products?size=XXL&q=Capsule&page_size=10').json()
    assert result['total'] == 27 and result['pages'] == 3 and len(result['items']) == 10
    assert result['items'][0]['fabric'] == 'Cotton'
    assert 'XXL' in c.get('/api/v1/catalog/facets').json()['sizes']
    assert len(c.get('/api/v1/products?size=XXL&page=3&page_size=10').json()['items']) == 7


def test_prd15_cod_pin_value_product_and_cart_estimate(setup):
    engine, client = setup
    c = client('cod-rules@example.test')
    q, sku = quote(c)
    estimate = post(c, '/cart/estimate', {'pin':'520001','method':'COD'})
    assert estimate['totals'] == q['totals'] and not estimate['stock_reserved']
    post(c, '/cart/estimate', {'pin':'111111'}, 409)
    with Session(engine) as db, db.begin():
        db.get(Product, db.get(Variant, sku).product_id).cod_allowed = False
    post(c, '/cart/estimate', {'pin':'520001','method':'COD'}, 409)
    post(c, '/cart/estimate', {'pin':'520001','method':'Prepaid'})
    with Session(engine) as db, db.begin():
        db.get(Product, db.get(Variant, sku).product_id).cod_allowed = True
        db.get(DeliveryRule, '520001').cod = False
    post(c, '/cart/estimate', {'pin':'520001','method':'COD'}, 409)
    with Session(engine) as db, db.begin():
        rule = db.get(DeliveryRule, '520001'); rule.cod = True; rule.cod_max = 1
    post(c, '/cart/estimate', {'pin':'520001','method':'COD'}, 409)


def test_prd_cancellation_request_approval_and_audit(setup):
    engine, client = setup
    c = client('cancel@example.test')
    q, sku = quote(c)
    o = post(c, '/checkout/orders', {'quote_id': q['id']}, headers={'Idempotency-Key':'cancel-request'})
    o = post(c, f"/orders/{o['id']}/cancel", {'reason':'x' * 300})
    assert o['status'] == 'Cancellation Requested'
    owner = client('owner@example.test', owner=True)
    post(owner, f"/admin/orders/{o['id']}", {'action':'process'}, 409)
    rejected = post(owner, f"/admin/orders/{o['id']}", {'action':'reject_cancel', 'reason':'Customer asked to keep this order'})
    assert rejected['status'] == 'Confirmed'
    o = post(c, f"/orders/{o['id']}/cancel", {'reason':'Wrong size selected'})
    o = post(owner, f"/admin/orders/{o['id']}", {'action':'cancel'})
    assert o['status'] == 'Cancelled'
    with Session(engine) as db:
        assert db.get(Inventory, sku).reserved == 0
        events = db.scalars(select(OrderEvent).where(OrderEvent.order_id == o['id'])).all()
        assert any(e.source == 'customer' and e.actor == o['user_id'] for e in events)
        assert any(e.source == 'staff' and e.detail['before']['status'] == 'Cancellation Requested' for e in events)
        message = db.scalar(select(Outbox).where(Outbox.user_id == o['user_id']))
        assert message.channel == 'email' and message.template == 'order_update'


def test_prd_api_envelopes_address_edit_search_and_roles(setup):
    engine, client = setup
    c = client('customer@example.test')
    a = post(c, '/addresses', dict(name='Customer', phone='9999999999', line='Test lane', city='Vijayawada', state='AP', pin='520001'))
    edited = c.patch('/api/v1/addresses/'+a['id'], json={k:v for k,v in {**a, 'city':'New city'}.items() if k!='id'})
    assert edited.status_code == 200 and edited.json()['city'] == 'New city'
    other = client('other@example.test')
    denied = other.patch('/api/v1/addresses/'+a['id'], json={k:v for k,v in a.items() if k!='id'})
    assert denied.status_code == 404 and denied.json()['error']['code'] == 'not_found'
    assert denied.json()['request_id'] == denied.headers['x-request-id']
    for role in ['Administrator','Catalog Manager','Operations Manager','Support Agent','Read-only Analyst']:
        email=role.split()[0].lower()+'@example.test'
        staff=client(email)
        with Session(engine) as db, db.begin():
            db.scalar(select(User).where(User.email==email)).role=role
        assert staff.get('/api/v1/admin/dashboard').status_code == 200
        response=staff.post('/api/v1/admin/categories', json={'name':'Test '+role,'slug':role.lower().replace(' ','-')})
        assert response.status_code == (200 if role in ['Administrator','Catalog Manager'] else 403)
        assert staff.get('/api/v1/admin/staff').status_code == 403
    owner=client('owner@example.test', owner=True)
    result=owner.get('/api/v1/admin/customers?q=other@example.test&page_size=1').json()
    assert result['total']==1 and result['items'][0]['email']=='other@example.test'
    invalid=c.get('/api/v1/products?page=0')
    assert invalid.status_code==422 and invalid.json()['error']['code']=='validation_error'


def test_sensitive_mutation_rate_limit_and_recovery(setup):
    from uyaras.models import RateLimit
    from uyaras.security import digest
    from uyaras.db import now
    engine, client = setup
    c = client()
    key = digest('testclient' + 'mutation:' + digest(c.cookies.get('uyaras_session')))
    with Session(engine) as db, db.begin():
        db.add(RateLimit(key=key, count=300, expires=now()+900))
    response = c.post('/api/v1/cart/estimate', json={'pin':'520001'})
    assert response.status_code == 429
    assert response.headers['retry-after'] == '900'
    assert response.json()['error']['code'] == 'rate_limited'
    with Session(engine) as db, db.begin():
        db.get(RateLimit, key).expires = now()-1
    assert c.post('/api/v1/cart/estimate', json={'pin':'520001'}).status_code != 429


def test_email_retry_exhaustion_and_channel_isolation(setup, monkeypatch):
    from uyaras.manage import worker
    engine, client = setup
    client('notifications@example.test')
    with Session(engine) as db, db.begin():
        user = db.scalar(select(User).where(User.email=='notifications@example.test'))
        mail = Outbox(user_id=user.id, channel='email', subject='Order confirmed', message='Test', attempts=7)
        future = Outbox(user_id=user.id, channel='whatsapp', message='Deferred channel')
        db.add_all([mail, future]); db.flush()
        mail_id, future_id = mail.id, future.id
    monkeypatch.setenv('SMTP_HOST', 'smtp.example.test')
    monkeypatch.setenv('SMTP_FROM', 'store@example.test')
    def unavailable(*args, **kwargs):
        raise OSError('Unavailable')
    monkeypatch.setattr('smtplib.SMTP', unavailable)
    worker(engine, once=True)
    with Session(engine) as db:
        assert db.get(Outbox, mail_id).status == 'failed'
        assert db.get(Outbox, mail_id).attempts == 8
        assert db.get(Outbox, future_id).status == 'pending'
        assert db.get(Outbox, future_id).attempts == 0
