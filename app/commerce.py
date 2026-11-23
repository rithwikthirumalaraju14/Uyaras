"""Single-brand commerce API and server-rendered storefront."""
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .store import ROOT, Store, digest, password_hash, password_matches, resets, sessions, uid, users

ROLES = {'Owner', 'Catalog', 'Operations', 'Support', 'Analyst', 'Customer'}
PERMISSIONS = {'catalog': {'Owner', 'Catalog'}, 'stock': {'Owner', 'Catalog', 'Operations'}, 'orders': {'Owner', 'Operations'}, 'returns': {'Owner', 'Operations', 'Support'}, 'settings': {'Owner'}, 'read': ROLES - {'Customer'}}


def require(condition, message, status=409):
    if not condition:
        raise HTTPException(status, message)


def text(value, name, maximum=200, minimum=1):
    require(isinstance(value, str) and minimum <= len(value.strip()) <= maximum, f'Invalid {name}.', 422)
    return value.strip()


def integer(value, name, minimum=0, maximum=100000000):
    require(type(value) is int and minimum <= value <= maximum, f'Invalid {name}.', 422)
    return value


def password_input(value):
    require(isinstance(value, str) and 12 <= len(value) <= 128, 'Password must contain 12–128 characters.', 422)
    return value


def audit(s, u, action, target, before=None, after=None):
    s['audit'].append(dict(at=time.time(), actor=u['id'], action=action, target=target, before=before, after=after))


def event(s, o, message):
    o['timeline'].append(dict(at=time.time(), message=message))
    s['outbox'].append(dict(id=uid(), user_id=o['customer'], order_id=o['id'], message=message, status='pending', created=time.time()))


def release(s, o):
    if o['held']:
        for line in o['lines']:
            s['stock'][line['sku']]['reserved'] -= line['quantity']
        o['held'] = False


def expire(s):
    for o in s['orders'].values():
        if o['status'] == 'Pending payment' and o['expires'] <= time.time():
            release(s, o)
            o.update(status='Payment expired', payment='Failed')
            event(s, o, 'Payment reservation expired')


def visible_category(s, key, seen=None):
    seen = set() if seen is None else seen
    if key in seen:
        return False
    seen.add(key)
    cat = s['categories'].get(key)
    return bool(cat and cat['published'] and (not cat['parent_id'] or visible_category(s, cat['parent_id'], seen)))


def visible(s, p):
    return p['status'] == 'published' and visible_category(s, p['category'])


def variant(s, sku):
    for p in s['products'].values():
        for v in p['variants']:
            if v['sku'] == sku:
                return p, v
    raise HTTPException(404, 'Variant not found.')


def product_view(s, p):
    return {**p, 'variants': [{**v, 'available': s['stock'][v['sku']]['on_hand']-s['stock'][v['sku']]['reserved']} for v in p['variants']]}


def cart_view(s, key):
    lines = []
    for sku, qty in s['carts'].get(key, {}).items():
        p, v = variant(s, sku)
        lines.append(dict(sku=sku, name=p['name'], slug=p['slug'], size=v['size'], colour=v['colour'], price=p['price'], quantity=qty, available=s['stock'][sku]['on_hand']-s['stock'][sku]['reserved'], image=p['images'][0]['url'] if p['images'] else '', published=visible(s, p)))
    return dict(lines=lines, subtotal=sum(l['price']*l['quantity'] for l in lines))


def quote(s, key, data):
    pin = text(data.get('pin'), 'six-digit PIN', 6, 6)
    require(re.fullmatch(r'[1-9][0-9]{5}', pin), 'Enter a six-digit India PIN.', 422)
    rule = s['rules'].get(pin)
    require(rule, 'Delivery is unavailable for this PIN.')
    method = data.get('method')
    require(method in ('COD', 'Prepaid'), 'Choose a payment method.', 422)
    cart = cart_view(s, key)
    require(cart['lines'], 'Your cart is empty.')
    for line in cart['lines']:
        _, v = variant(s, line['sku'])
        require(line['published'] and v['active'] and line['quantity'] <= line['available'], 'Availability changed. Please update your cart.')
    subtotal = cart['subtotal']
    if method == 'COD':
        require(rule['cod'] and (not rule['cod_max'] or subtotal <= rule['cod_max']), 'COD is unavailable for this PIN or order value.')
    code = str(data.get('coupon', '')).strip().upper()
    discount = 0
    if code:
        promo = s['promotions'].get(code)
        now = time.time()
        require(promo and promo['active'] and (not promo['start'] or promo['start'] <= now) and (not promo['end'] or now <= promo['end']), 'Coupon is unavailable.')
        used = sum(o['coupon'] == code and o['status'] not in ('Cancelled', 'Payment expired', 'Payment failed') for o in s['orders'].values())
        require(subtotal >= promo['minimum'] and (not promo['limit'] or used < promo['limit']), 'Coupon minimum spend or usage limit not met.')
        discount = subtotal * promo['percent'] // 100
    shipping = 0 if rule['free_over'] and subtotal >= rule['free_over'] else rule['shipping']
    cod_fee = rule['cod_fee'] if method == 'COD' else 0
    tax = ((subtotal-discount)*rule['tax_bps']+5000)//10000
    lines = [{k: l[k] for k in ('sku', 'name', 'size', 'colour', 'price', 'quantity')} for l in cart['lines']]
    return dict(lines=lines, subtotal=subtotal, discount=discount, shipping=shipping, cod_fee=cod_fee, tax=tax, total=subtotal-discount+shipping+cod_fee+tax, currency='INR', pin=pin, method=method, coupon=code)


def create_app(store=None):
    db = store or Store()
    sandbox = os.getenv('PAYMENT_MODE', 'sandbox') == 'sandbox'

    @asynccontextmanager
    async def lifespan(app):
        yield

    api = FastAPI(title='Clothing commerce', version='1.0.0', lifespan=lifespan)
    api.state.store = db

    @api.middleware('http')
    async def headers(request, call_next):
        request.state.request_id = str(uuid4())
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:
            logging.getLogger('uvicorn.error').error('request_failed id=%s type=%s', request.state.request_id, type(exc).__name__)
            response = JSONResponse({'error': {'code': 'internal_error', 'message': 'The request could not be completed.', 'request_id': request.state.request_id}}, status_code=500)
        response.headers.update({'X-Request-ID': request.state.request_id, 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'same-origin', 'X-Frame-Options': 'DENY', 'Content-Security-Policy': "default-src 'self'; img-src 'self' https:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"})
        if request.url.path in ('/docs', '/docs/oauth2-redirect', '/redoc'):
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https://fastapi.tiangolo.com; object-src 'none'; frame-ancestors 'none'"
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        route = request.scope.get('route')
        logging.getLogger('uvicorn.error').info('request id=%s method=%s route=%s status=%s duration_ms=%s', request.state.request_id, request.method, getattr(route, 'path', 'unmatched'), response.status_code, round((time.monotonic()-started)*1000))
        return response

    @api.exception_handler(StarletteHTTPException)
    async def error(request, exc):
        return JSONResponse({'error': {'code': 'request_rejected', 'message': str(exc.detail), 'request_id': request.state.request_id}}, status_code=exc.status_code)

    @api.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse({'error': {'code': 'invalid_input', 'message': 'Check required fields and allowed values.', 'request_id': request.state.request_id}}, status_code=422)

    def identity(c, request, write=False):
        token = request.cookies.get('commerce_session', '')
        session = c.execute(select(sessions).where(sessions.c.id == digest(token), sessions.c.expires > time.time())).mappings().first()
        require(session, 'Please refresh the page and sign in.', 401)
        if write:
            require(secrets.compare_digest(request.headers.get('X-CSRF-Token', ''), session['csrf']), 'Invalid security token. Refresh the page.', 403)
            origin = request.headers.get('origin')
            expected = os.getenv('PUBLIC_ORIGIN', str(request.base_url).rstrip('/'))
            require(not origin or origin == expected, 'Untrusted request origin.', 403)
        user = c.execute(select(users).where(users.c.id == session['user_id'])).mappings().first() if session['user_id'] else None
        return dict(session), dict(user) if user else None

    def authorized(c, request, permission=None, write=False):
        sess, user = identity(c, request, write)
        require(user, 'Sign in to continue.', 401)
        if permission:
            require(user['role'] in PERMISSIONS[permission], 'This account does not have permission.', 403)
        return sess, user

    def new_session(c, response, user_id=None):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        c.execute(sessions.insert().values(id=digest(token), user_id=user_id, csrf=csrf, expires=time.time()+86400*7))
        response.set_cookie('commerce_session', token, httponly=True, secure=os.getenv('COOKIE_SECURE') == '1', samesite='lax', max_age=86400*7)
        return csrf

    def safe_user(u):
        return {k: u[k] for k in ('id', 'email', 'name', 'role')} if u else None

    @api.get('/health/live')
    def live():
        return {'status': 'alive'}

    @api.get('/health/ready')
    def ready():
        from sqlalchemy.exc import SQLAlchemyError
        try:
            with db.transaction():
                return {'status': 'ready'}
        except SQLAlchemyError:
            raise HTTPException(503, 'Database unavailable.')

    @api.get('/api/v1/session')
    def session(request: Request, response: Response):
        with db.transaction() as (c, s):
            expire(s)
            try:
                sess, u = identity(c, request)
                csrf = sess['csrf']
            except HTTPException:
                u = None
                csrf = new_session(c, response)
            return dict(user=safe_user(u), csrf=csrf, sandbox=sandbox)

    @api.post('/api/v1/auth/{action}')
    def auth(action: str, data: dict, request: Request, response: Response):
        with db.transaction() as (c, s):
            identity(c, request, True)
            # Persist attempts even when the following authentication fails.
            rate_key = digest((request.client.host if request.client else 'local')+action)
            attempts = s.setdefault('rate_limits', {}).setdefault(rate_key, [])
            attempts[:] = [x for x in attempts if x > time.time()-900]
            require(len(attempts) < 30, 'Too many attempts. Try again in 15 minutes.', 429)
            attempts.append(time.time())
        with db.transaction() as (c, s):
            sess, u = identity(c, request, True)
            if action == 'logout':
                c.execute(delete(sessions).where(sessions.c.id == sess['id']))
                return dict(user=None, csrf=new_session(c, response))
            if action in ('register', 'login', 'forgot-password'):
                email = text(data.get('email'), 'email', 254).lower()
                require(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email), 'Enter a valid email.', 422)
                found = c.execute(select(users).where(users.c.email == email)).mappings().first()
            if action == 'forgot-password':
                if found:
                    token = secrets.token_urlsafe(32)
                    c.execute(delete(resets).where(resets.c.user_id == found['id']))
                    c.execute(resets.insert().values(id=digest(token), user_id=found['id'], expires=time.time()+1800))
                    s['outbox'].append(dict(id=uid(), user_id=found['id'], kind='password_reset', token=token, status='pending', created=time.time()))
                return {'message': 'If the account exists, recovery instructions have been queued.'}
            if action == 'reset-password':
                token = text(data.get('token'), 'reset token', 100)
                row = c.execute(select(resets).where(resets.c.id == digest(token), resets.c.expires > time.time())).mappings().first()
                require(row, 'Recovery link is invalid or expired.', 400)
                password = password_input(data.get('password'))
                c.execute(users.update().where(users.c.id == row['user_id']).values(password=password_hash(password)))
                c.execute(delete(resets).where(resets.c.user_id == row['user_id']))
                c.execute(delete(sessions).where(sessions.c.user_id == row['user_id']))
                return {'message': 'Password changed. Sign in again.'}
            require(action in ('register', 'login'), 'Unknown authentication action.', 404)
            password = password_input(data.get('password'))
            if action == 'register':
                if found:
                    return JSONResponse({'error': {'message': 'Unable to register with these details.'}}, status_code=409)
                u = dict(id=uid(), email=email, password=password_hash(password), name=text(data.get('name'), 'name', 80), role='Customer')
                c.execute(users.insert().values(**u))
            else:
                # Run a password hash even for nonexistent users.
                valid = password_matches(password, found['password'] if found else password_hash('unused-placeholder'))
                if not found or not valid:
                    return JSONResponse({'error': {'message': 'Invalid email or password.'}}, status_code=401)
                u = dict(found)
            guest = s['carts'].pop(sess['id'], {})
            cart = s['carts'].setdefault(u['id'], {})
            for sku, qty in guest.items():
                cart[sku] = min(99, cart.get(sku, 0)+qty)
            c.execute(delete(sessions).where(sessions.c.id == sess['id']))
            return dict(user=safe_user(u), csrf=new_session(c, response, u['id']))

    @api.get('/api/v1/me')
    def me(request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request)
            return dict(user=safe_user(u), addresses=s['addresses'].get(u['id'], []))

    @api.patch('/api/v1/me')
    def profile(data: dict, request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request, write=True)
            name = text(data.get('name'), 'name', 80)
            c.execute(users.update().where(users.c.id == u['id']).values(name=name))
            return {**safe_user(u), 'name': name}

    @api.post('/api/v1/addresses')
    def address(data: dict, request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request, write=True)
            item = {k: text(data.get(k), k, 200) for k in ('name', 'phone', 'line', 'city', 'state', 'pin')}
            require(re.fullmatch(r'[1-9][0-9]{5}', item['pin']) and re.fullmatch(r'[0-9+ ()-]{10,20}', item['phone']), 'Enter a valid PIN and phone.', 422)
            items = s['addresses'].setdefault(u['id'], [])
            require(len(items) < 12, 'Maximum 12 saved addresses.')
            item['id'] = uid()
            items.append(item)
            return item

    @api.delete('/api/v1/addresses/{address_id}')
    def remove_address(address_id: str, request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request, write=True)
            s['addresses'][u['id']] = [a for a in s['addresses'].get(u['id'], []) if a['id'] != address_id]
            return {'ok': True}

    @api.get('/api/v1/categories')
    def categories():
        with db.transaction() as (_, s):
            return {'items': [v for k, v in s['categories'].items() if visible_category(s, k)]}

    @api.get('/api/v1/collections')
    def collections():
        with db.transaction() as (_, s):
            return {'items': [{**collection, 'product_ids': [pid for pid in collection['product_ids'] if pid in s['products'] and visible(s, s['products'][pid])]} for collection in s['collections'].values()]}

    @api.get('/api/v1/products')
    def products(q: str = '', category: str = '', collection: str = '', size: str = '', colour: str = '', sort: str = 'newest', available: bool = False, min_price: int = 0, max_price: int = 100000000, page: int = 1):
        require(page > 0, 'Invalid page.', 422)
        with db.transaction() as (_, s):
            expire(s)
            items = [product_view(s, p) for p in s['products'].values() if visible(s, p)]
            if collection:
                ids = s['collections'].get(collection, {}).get('product_ids', [])
                items = [p for p in items if p['id'] in ids]
            items = [p for p in items if (not q or q.lower() in (p['name']+' '+p['description']).lower()) and (not category or p['category'] == category) and min_price <= p['price'] <= max_price and any((not size or v['size'] == size) and (not colour or v['colour'] == colour) and (not available or v['available'] > 0) for v in p['variants'])]
            items.sort(key=lambda p: p['price'] if sort in ('price-asc', 'price-desc') else p['created'], reverse=sort != 'price-asc')
            return {'items': items[(page-1)*24:page*24], 'total': len(items), 'page': page}

    @api.get('/api/v1/products/{slug}')
    def product(slug: str):
        with db.transaction() as (_, s):
            p = next((p for p in s['products'].values() if p['slug'] == slug and visible(s, p)), None)
            require(p, 'Product not found.', 404)
            return product_view(s, p)

    @api.get('/api/v1/products/{product_id}/variants')
    def product_variants(product_id: str):
        with db.transaction() as (_, s):
            p = s['products'].get(product_id)
            require(p and visible(s, p), 'Product not found.', 404)
            return {'items': product_view(s, p)['variants']}

    @api.get('/api/v1/products/{product_id}/size-guide')
    def size_guide(product_id: str):
        with db.transaction() as (_, s):
            p = s['products'].get(product_id)
            require(p and visible(s, p), 'Product not found.', 404)
            return {'text': p['size_guide']}

    @api.get('/api/v1/cart')
    def cart(request: Request):
        with db.transaction() as (c, s):
            sess, u = identity(c, request)
            expire(s)
            return cart_view(s, u['id'] if u else sess['id'])

    @api.post('/api/v1/cart/items')
    def cart_item(data: dict, request: Request):
        with db.transaction() as (c, s):
            sess, u = identity(c, request, True)
            expire(s)
            sku = text(data.get('sku'), 'SKU', 100)
            qty = integer(data.get('quantity'), 'quantity', 0, 99)
            p, v = variant(s, sku)
            require(qty == 0 or (visible(s, p) and v['active'] and qty <= s['stock'][sku]['on_hand']-s['stock'][sku]['reserved']), 'Not enough available stock.')
            key = u['id'] if u else sess['id']
            bag = s['carts'].setdefault(key, {})
            if qty:
                bag[sku] = qty
            else:
                bag.pop(sku, None)
            return cart_view(s, key)

    @api.post('/api/v1/checkout/serviceability')
    def serviceability(data: dict):
        with db.transaction() as (_, s):
            rule = s['rules'].get(data.get('pin'))
            return {'serviceable': bool(rule), 'rule': rule}

    @api.post('/api/v1/checkout/quote')
    def checkout_quote(data: dict, request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request, write=True)
            expire(s)
            q = quote(s, u['id'], data)
            addresses = s['addresses'].get(u['id'], [])
            address = next((a for a in addresses if a['id'] == data.get('address_id')), None)
            require(address and address['pin'] == q['pin'], 'Choose a saved address matching this PIN.')
            quote_id = uid()
            s['quotes'][quote_id] = dict(user_id=u['id'], address=address.copy(), quote=q, expires=time.time()+300)
            return dict(id=quote_id, expires=s['quotes'][quote_id]['expires'], **q)

    @api.post('/api/v1/checkout/orders')
    def create_order(data: dict, request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request, write=True)
            expire(s)
            key = text(request.headers.get('Idempotency-Key'), 'idempotency key', 100)
            scoped = u['id']+':'+key
            fingerprint = digest(json.dumps(data, sort_keys=True))
            previous = s['requests'].get(scoped)
            if previous:
                require(previous['fingerprint'] == fingerprint, 'Idempotency key already used for a different request.')
                return s['orders'][previous['order_id']]
            saved = s['quotes'].get(data.get('quote_id'))
            require(saved and saved['user_id'] == u['id'] and saved['expires'] > time.time(), 'Quote expired. Review a new quote.')
            require(not saved.get('consumed'), 'This quote has already been used.')
            q = quote(s, u['id'], saved['quote'])
            require(q == saved['quote'], 'Price or availability changed. Review a new quote.')
            require(q['method'] != 'Prepaid' or sandbox, 'A live payment provider has not been configured.', 503)
            order_id = 'ORD-'+uid()[:12].upper()
            prepaid = q['method'] == 'Prepaid'
            o = dict(id=order_id, customer=u['id'], address=saved['address'], **q, status='Pending payment' if prepaid else 'Confirmed', payment='Pending' if prepaid else 'COD due', shipment='Not created', held=True, expires=time.time()+900, created=time.time(), timeline=[], returns=[], refund=0, collected=0, remitted=0, tracking='', delivered_at=None, reconciliation=False)
            for line in q['lines']:
                s['stock'][line['sku']]['reserved'] += line['quantity']
            s['orders'][order_id] = o
            saved['consumed'] = True
            s['carts'][u['id']] = {}
            s['requests'][scoped] = dict(fingerprint=fingerprint, order_id=order_id)
            event(s, o, 'Order placed; '+o['payment'])
            return o

    def owned(s, u, order_id, staff=False):
        o = s['orders'].get(order_id)
        require(o and (o['customer'] == u['id'] or (staff and u['role'] in PERMISSIONS['read'])), 'Order not found.', 404)
        return o

    @api.get('/api/v1/orders')
    def orders(request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request)
            expire(s)
            return {'items': sorted([o for o in s['orders'].values() if o['customer'] == u['id']], key=lambda o: o['created'], reverse=True)}

    @api.get('/api/v1/orders/{order_id}')
    def order(order_id: str, request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request)
            expire(s)
            return owned(s, u, order_id)

    def capture(s, o, event_id, amount, currency):
        require(o['method'] == 'Prepaid' and amount == o['total'] and currency == 'INR', 'Payment does not match the order.')
        fingerprint = digest(json.dumps([o['id'], amount, currency]))
        if event_id in s['inbox']:
            require(s['inbox'][event_id] == fingerprint, 'Payment event conflict.')
            return
        s['inbox'][event_id] = fingerprint
        if o['status'] == 'Pending payment':
            o.update(status='Confirmed', payment='Paid')
            event(s, o, 'Verified payment received')
        elif o['payment'] not in ('Paid', 'Partially refunded', 'Refunded'):
            o.update(payment='Paid', reconciliation=True)
            event(s, o, 'Late payment received; refund reconciliation required')

    @api.post('/api/v1/orders/{order_id}/sandbox-payment')
    def sandbox_payment(order_id: str, data: dict, request: Request):
        require(sandbox, 'Sandbox payments disabled.', 404)
        with db.transaction() as (c, s):
            _, u = authorized(c, request, write=True)
            expire(s)
            o = owned(s, u, order_id)
            require(o['status'] == 'Pending payment', 'Order is not awaiting payment.')
            if data.get('outcome') == 'success':
                capture(s, o, 'sandbox:'+order_id, o['total'], 'INR')
            elif data.get('outcome') == 'failed':
                release(s, o)
                o.update(status='Payment failed', payment='Failed')
                event(s, o, 'Sandbox payment failed')
            else:
                require(data.get('outcome') == 'pending', 'Invalid payment outcome.', 422)
            return o

    @api.post('/api/v1/payments/webhooks/sandbox')
    async def webhook(request: Request):
        secret = os.getenv('PAYMENT_WEBHOOK_SECRET')
        require(sandbox and secret, 'Sandbox webhook is not configured.', 503)
        raw = await request.body()
        require(hmac.compare_digest(request.headers.get('X-Signature', ''), hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()), 'Invalid signature.', 401)
        try:
            data = json.loads(raw)
            event_id = text(data.get('event_id'), 'event ID', 100)
            amount = integer(data.get('amount'), 'amount')
        except (ValueError, AttributeError):
            raise HTTPException(422, 'Invalid payment event.')
        with db.transaction() as (_, s):
            expire(s)
            o = s['orders'].get(data.get('order_id'))
            require(o, 'Order not found.', 404)
            capture(s, o, event_id, amount, data.get('currency'))
            return {'accepted': True}

    @api.post('/api/v1/orders/{order_id}/payment-retry')
    def retry_payment(order_id: str, request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request, write=True)
            o = owned(s, u, order_id)
            require(o['status'] in ('Payment failed', 'Payment expired') and o['payment'] == 'Failed', 'Payment cannot be retried.')
            for l in o['lines']:
                b = s['stock'][l['sku']]
                require(b['on_hand']-b['reserved'] >= l['quantity'], 'Stock is no longer available.')
                b['reserved'] += l['quantity']
            o.update(status='Pending payment', payment='Pending', held=True, expires=time.time()+900)
            event(s, o, 'Payment retry started')
            return o

    @api.post('/api/v1/orders/{order_id}/cancel')
    def cancel(order_id: str, data: dict, request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request, write=True)
            o = owned(s, u, order_id)
            require(o['status'] in ('Pending payment', 'Confirmed', 'Processing', 'Packed'), 'Order can no longer be cancelled.')
            reason = text(data.get('reason'), 'cancellation reason')
            release(s, o)
            o['status'] = 'Cancelled'
            if o['payment'] == 'Paid':
                o['reconciliation'] = True
            event(s, o, 'Cancelled: '+reason)
            return o

    @api.post('/api/v1/orders/{order_id}/returns')
    def return_request(order_id: str, data: dict, request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request, write=True)
            o = owned(s, u, order_id)
            require(o['status'] == 'Delivered' and time.time()-o['delivered_at'] <= int(os.getenv('RETURN_DAYS', '14'))*86400, 'Order is outside the return window.')
            line = next((l for l in o['lines'] if l['sku'] == data.get('sku')), None)
            require(line, 'Order item not found.', 404)
            quantity = integer(data.get('quantity'), 'return quantity', 1, 99)
            used = sum(r['quantity'] for r in o['returns'] if r['sku'] == line['sku'] and r['status'] != 'Rejected')
            require(quantity+used <= line['quantity'], 'Return quantity exceeds purchased quantity.')
            item = dict(id=uid(), sku=line['sku'], quantity=quantity, reason=text(data.get('reason'), 'return reason'), status='Requested', refund=0)
            o['returns'].append(item)
            event(s, o, 'Return requested')
            return item

    @api.get('/api/v1/admin/{resource}')
    def admin_list(resource: str, request: Request):
        with db.transaction() as (c, s):
            _, u = authorized(c, request, 'read')
            expire(s)
            require(resource in ('products', 'categories', 'collections', 'stock', 'orders', 'rules', 'promotions', 'audit', 'customers', 'staff', 'outbox'), 'Unknown resource.', 404)
            if resource in ('staff', 'outbox'):
                require(u['role'] == 'Owner', 'Owner permission required.', 403)
            if resource in ('customers', 'staff'):
                return {'items': [safe_user(row) for row in c.execute(select(users)).mappings()]}
            items = s[resource]
            if resource == 'outbox':
                items = [{k: v for k, v in i.items() if k != 'token'} for i in items]
            return {'items': items}

    @api.post('/api/v1/admin/{resource}')
    def admin_write(resource: str, data: dict, request: Request):
        permission = {'products': 'catalog', 'categories': 'catalog', 'collections': 'catalog', 'stock': 'stock', 'rules': 'settings', 'promotions': 'settings', 'staff': 'settings'}.get(resource)
        require(permission, 'Unknown resource.', 404)
        with db.transaction() as (c, s):
            _, u = authorized(c, request, permission, True)
            before = None
            if resource == 'products':
                key = data.get('id') or uid()
                previous = s['products'].get(key)
                before = json.loads(json.dumps(previous))
                slug = text(data.get('slug'), 'slug', 100)
                require(re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', slug), 'Use a lowercase URL slug.', 422)
                require(not any(p['slug'] == slug and p['id'] != key for p in s['products'].values()), 'Slug already exists.')
                require(data.get('category') in s['categories'], 'Choose a category.')
                require(data.get('status') in ('draft', 'published', 'archived'), 'Invalid product status.', 422)
                variants = data.get('variants', [])
                require(isinstance(variants, list) and 0 < len(variants) <= 200, 'Add between 1 and 200 variants.', 422)
                new_variants, seen, combinations = [], set(), set()
                other_skus = {v['sku'] for p in s['products'].values() if p['id'] != key for v in p['variants']}
                for v in variants:
                    require(isinstance(v, dict), 'Each variant must be an object.', 422)
                    sku = text(v.get('sku'), 'SKU', 100)
                    size, colour = text(v.get('size'), 'size', 20), text(v.get('colour'), 'colour', 40)
                    require(sku not in seen | other_skus and (size, colour) not in combinations, 'Duplicate SKU or size/colour combination.')
                    seen.add(sku)
                    combinations.add((size, colour))
                    new_variants.append(dict(sku=sku, size=size, colour=colour, active=bool(v.get('active', True))))
                    s['stock'].setdefault(sku, dict(on_hand=0, reserved=0, low_stock=3))
                require(not previous or all(v['sku'] in seen for v in previous['variants']), 'Deactivate existing variants instead of deleting them.')
                images = data.get('images', [])
                require(isinstance(images, list) and len(images) <= 12, 'Maximum 12 images.', 422)
                checked_images = []
                for img in images:
                    require(isinstance(img, dict), 'Each image must be an object.', 422)
                    url = text(img.get('url'), 'image URL', 1000)
                    require(url.startswith('https://') or url.startswith('/art/'), 'Use an HTTPS image URL or local art path.', 422)
                    checked_images.append(dict(url=url, alt=text(img.get('alt'), 'image description')))
                after = dict(id=key, slug=slug, name=text(data.get('name'), 'name', 180), description=text(data.get('description', ''), 'description', 3000, 0), price=integer(data.get('price'), 'price in paise', 1), category=data['category'], status=data['status'], variants=new_variants, images=checked_images, care=text(data.get('care', ''), 'care', 1000, 0), size_guide=text(data.get('size_guide', ''), 'size guide', 3000, 0), created=previous['created'] if previous else time.time())
            elif resource == 'categories':
                key = text(data.get('id') or data.get('slug'), 'category ID', 100)
                parent = data.get('parent_id') or None
                require(not parent or parent in s['categories'], 'Parent category not found.')
                seen = {key}
                cursor = parent
                while cursor:
                    require(cursor not in seen, 'Category hierarchy cannot contain a cycle.')
                    seen.add(cursor)
                    cursor = s['categories'][cursor]['parent_id']
                slug = text(data.get('slug'), 'category slug', 100)
                require(not any(v['slug'] == slug and k != key for k, v in s['categories'].items()), 'Category slug already exists.')
                after = dict(id=key, name=text(data.get('name'), 'category name'), slug=slug, parent_id=parent, published=bool(data.get('published')))
            elif resource == 'collections':
                key = text(data.get('id') or uid(), 'collection ID', 100)
                ids = data.get('product_ids', [])
                require(isinstance(ids, list) and all(p in s['products'] for p in ids), 'Unknown collection product.')
                after = dict(id=key, name=text(data.get('name'), 'collection name'), product_ids=ids)
            elif resource == 'stock':
                key = text(data.get('sku'), 'SKU', 100)
                require(key in s['stock'], 'Unknown SKU.', 404)
                before = s['stock'][key].copy()
                delta = integer(data.get('delta'), 'adjustment', -100000, 100000)
                reason = text(data.get('reason'), 'stock adjustment reason')
                after = {**before, 'on_hand': before['on_hand']+delta}
                require(after['on_hand'] >= after['reserved'], 'Adjustment would consume reserved stock.')
                audit(s, u, 'stock_reason', key, None, reason)
            elif resource == 'rules':
                key = text(data.get('pin'), 'PIN', 6, 6)
                require(re.fullmatch('[1-9][0-9]{5}', key), 'Invalid PIN.', 422)
                after = dict(pin=key, name=text(data.get('name'), 'region'), cod=bool(data.get('cod')), days=text(data.get('days', ''), 'delivery estimate', 100, 0))
                for field in ('shipping', 'cod_fee', 'cod_max', 'free_over', 'tax_bps'):
                    after[field] = integer(data.get(field, 0), field, 0, 10000 if field == 'tax_bps' else 100000000)
                if data.get('delete'):
                    before = s['rules'].pop(key, None)
                    audit(s, u, 'disable_pin', key, before)
                    return {'ok': True}
            elif resource == 'promotions':
                key = text(data.get('code'), 'coupon', 30).upper()
                after = dict(code=key, percent=integer(data.get('percent'), 'percentage', 1, 100), minimum=integer(data.get('minimum', 0), 'minimum'), limit=integer(data.get('limit', 0), 'usage limit'), active=bool(data.get('active')), start=integer(data.get('start', 0), 'start', 0, 9999999999), end=integer(data.get('end', 0), 'end', 0, 9999999999))
                require(not after['end'] or after['end'] >= after['start'], 'Invalid coupon dates.')
            else:
                key = text(data.get('id'), 'user ID', 100)
                require(data.get('role') in ROLES, 'Invalid role.', 422)
                target = c.execute(select(users).where(users.c.id == key)).mappings().first()
                require(target, 'Account not found.', 404)
                require(target['role'] != 'Owner', 'Owner accounts cannot be changed through this endpoint.')
                c.execute(users.update().where(users.c.id == key).values(role=data['role']))
                audit(s, u, 'role_changed', key, target['role'], data['role'])
                return {'ok': True}
            if before is None:
                before = s[resource].get(key)
            s[resource][key] = after
            audit(s, u, resource+'_updated', key, before, after)
            return after

    @api.post('/api/v1/admin/orders/{order_id}')
    def order_action(order_id: str, data: dict, request: Request):
        with db.transaction() as (c, s):
            action = data.get('action')
            _, u = authorized(c, request, 'returns' if action == 'return' else 'orders', True)
            expire(s)
            o = owned(s, u, order_id, True)
            before = json.loads(json.dumps(o))
            transitions = {'process': ('Confirmed', 'Processing'), 'pack': ('Processing', 'Packed'), 'ship': ('Packed', 'Shipped'), 'deliver': ('Shipped', 'Delivered')}
            if action in transitions:
                old, new = transitions[action]
                require(o['status'] == old and not o['reconciliation'], 'Invalid order transition.')
                if action == 'ship':
                    require(o['payment'] in ('Paid', 'COD due'), 'Payment is not ready for shipment.')
                    o['tracking'] = text(data.get('tracking'), 'tracking reference')
                    for l in o['lines']:
                        b = s['stock'][l['sku']]
                        b['on_hand'] -= l['quantity']
                        b['reserved'] -= l['quantity']
                    o.update(held=False, shipment='In transit')
                if action == 'deliver':
                    require(o['shipment'] in ('In transit', 'Out for delivery', 'Delivery failed'), 'Shipment cannot be delivered.')
                    o.update(shipment='Delivered', delivered_at=time.time())
                o['status'] = new
            elif action == 'shipment':
                states = {'In transit': ['Out for delivery', 'Delivery failed'], 'Out for delivery': ['Delivery failed'], 'Delivery failed': ['Out for delivery', 'RTO initiated'], 'RTO initiated': ['RTO in transit'], 'RTO in transit': ['Returned to origin']}
                new = data.get('status')
                require(new in states.get(o['shipment'], []), 'Invalid shipment transition.')
                o['shipment'] = new
            elif action == 'cancel':
                require(o['status'] in ('Pending payment', 'Confirmed', 'Processing', 'Packed'), 'Order cannot be cancelled after dispatch.')
                reason = text(data.get('reason'), 'cancellation reason')
                release(s, o)
                o.update(status='Cancelled', reconciliation=o['payment'] == 'Paid')
                event(s, o, 'Staff cancellation: '+reason)
            elif action == 'rto-inspect':
                require(o['shipment'] == 'Returned to origin' and not o.get('rto_inspected'), 'RTO is not ready for inspection.')
                text(data.get('reason'), 'inspection note')
                if data.get('restock'):
                    for l in o['lines']:
                        s['stock'][l['sku']]['on_hand'] += l['quantity']
                o.update(rto_inspected=True, status='Returned', reconciliation=o['payment'] == 'Paid')
            elif action == 'collect':
                require(o['method'] == 'COD' and o['status'] == 'Delivered' and o['collected'] == 0, 'COD collection cannot be recorded.')
                o.update(collected=o['total'], payment='Collected')
                o['collection_reference'] = text(data.get('reference'), 'collection reference')
            elif action == 'remit':
                require(o['collected'] > 0 and o['remitted'] == 0, 'No outstanding COD remittance.')
                o['remitted'] = o['collected']
                o['remittance_reference'] = text(data.get('reference'), 'remittance reference')
            elif action == 'refund':
                amount = integer(data.get('amount'), 'refund amount', 1)
                require(o['reconciliation'] and o['payment'] in ('Paid', 'Collected', 'Partially refunded'), 'No reconciliation refund due.')
                require(o['refund']+amount <= o['total'], 'Refund exceeds paid amount.')
                o['refund_reference'] = text(data.get('reference'), 'refund reference')
                o['refund'] += amount
                o['payment'] = 'Refunded' if o['refund'] == o['total'] else 'Partially refunded'
                o['reconciliation'] = o['refund'] != o['total']
            elif action == 'return':
                r = next((r for r in o['returns'] if r['id'] == data.get('return_id')), None)
                require(r, 'Return not found.', 404)
                new = data.get('status')
                require(new in {'Requested': ['Approved', 'Rejected'], 'Approved': ['Received'], 'Received': ['Closed']}.get(r['status'], []), 'Invalid return transition.')
                r['note'] = text(data.get('reason'), 'inspection or decision note')
                if new == 'Closed':
                    require(o['payment'] in ('Paid', 'Collected', 'Partially refunded'), 'Refund requires collected payment.')
                    line = next(l for l in o['lines'] if l['sku'] == r['sku'])
                    # Allocate net merchandise and tax proportionally; shipping is non-refundable.
                    max_refund = (line['price']*r['quantity']*(o['subtotal']-o['discount']+o['tax']))//o['subtotal']
                    amount = integer(data.get('amount'), 'refund amount', 0, max_refund)
                    require(o['refund']+amount <= o['total'], 'Refund exceeds collected funds.')
                    r['reference'] = text(data.get('reference'), 'refund or exchange reference')
                    r['refund'] = amount
                    o['refund'] += amount
                    if amount:
                        o['payment'] = 'Refunded' if o['refund'] == o['total'] else 'Partially refunded'
                    if data.get('restock'):
                        s['stock'][r['sku']]['on_hand'] += r['quantity']
                r['status'] = new
            else:
                raise HTTPException(422, 'Unknown order operation.')
            audit(s, u, action, order_id, before, o)
            event(s, o, 'Staff operation: '+action)
            return o

    api.mount('/assets', StaticFiles(directory=ROOT/'web'), name='assets')
    api.mount('/art', StaticFiles(directory=ROOT/'mock_store/art'), name='art')

    @api.get('/robots.txt', response_class=PlainTextResponse)
    def robots():
        return 'User-agent: *\nDisallow: /admin\nDisallow: /account\nDisallow: /checkout\n'

    @api.get('/sitemap.xml')
    def sitemap():
        import html
        origin = os.getenv('PUBLIC_ORIGIN', 'http://127.0.0.1:8000').rstrip('/')
        with db.transaction() as (_, s):
            paths = ['/', '/shop', '/policies'] + ['/products/'+p['slug'] for p in s['products'].values() if visible(s, p)]
        body = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+html.escape(origin+p)+'</loc></url>' for p in paths)+'</urlset>'
        return Response(body, media_type='application/xml')

    @api.get('/{path:path}', response_class=HTMLResponse, include_in_schema=False)
    def page(path: str):
        import html
        template = (ROOT/'web/index.html').read_text(encoding='utf-8')
        title, description, content = 'Thread & Form | Everyday clothing', 'Everyday essentials, thoughtfully selected.', ''
        with db.transaction() as (_, s):
            if path.startswith('products/'):
                p = next((p for p in s['products'].values() if p['slug'] == path.split('/')[-1] and visible(s, p)), None)
                require(p, 'Product not found.', 404)
                title, description = p['name']+' | Thread & Form', p['description']
                content = '<article class="wrap" itemscope itemtype="https://schema.org/Product"><h1 itemprop="name">'+html.escape(p['name'])+'</h1><p itemprop="description">'+html.escape(p['description'])+'</p><div itemprop="offers" itemscope itemtype="https://schema.org/Offer"><meta itemprop="priceCurrency" content="INR"><span itemprop="price">'+format(p['price']/100, '.2f')+'</span> INR</div></article>'
            elif path in ('', 'shop'):
                content = '<h1>Everyday essentials</h1>'+''.join('<a href="/products/'+html.escape(p['slug'], quote=True)+'">'+html.escape(p['name'])+'</a> ' for p in s['products'].values() if visible(s, p))
            elif path not in ('cart', 'checkout', 'account', 'orders', 'admin', 'policies', 'reset-password') and not path.startswith('orders/'):
                raise HTTPException(404, 'Page not found.')
        canonical = os.getenv('PUBLIC_ORIGIN', 'http://127.0.0.1:8000').rstrip('/')+'/'+path
        return template.replace('__TITLE__', html.escape(title)).replace('__DESCRIPTION__', html.escape(description, quote=True)).replace('__CONTENT__', content).replace('</head>', '<link rel="canonical" href="'+html.escape(canonical, quote=True)+'"></head>')

    return api


# Imported by Uvicorn. CLI setup creates the schema before production workers start.
app = create_app()
