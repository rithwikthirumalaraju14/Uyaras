"""Session-isolated, transaction-backed demo. External providers never receive requests."""
import hashlib
import json
import os
import secrets
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response

from .main import catalog

router = APIRouter()
ROOT = Path(__file__).parent


def connection():
    conn = sqlite3.connect(os.environ.get('STUDIO_DEMO_DB', 'studio-demo.sqlite3'), timeout=8)
    conn.execute('CREATE TABLE IF NOT EXISTS rehearsal (session_hash TEXT PRIMARY KEY, state TEXT NOT NULL)')
    return conn


def key(token):
    return hashlib.sha256(token.encode()).hexdigest()


def engine(**payload):
    proc = subprocess.run(['node', str(ROOT / 'runner.cjs')], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=5, check=True)
    data = json.loads(proc.stdout)
    if 'error' in data:
        raise HTTPException(409, data['error'])
    return data


def view(state):
    # The persona picker is explicit in demo mode. Show all aliases, only the
    # selected shopper's private address book and orders in shopper mode.
    projected = {**state, 'requests': {}}
    if state['role'] == 'Shopper':
        owner = state['customer']
        projected['profiles'] = {k: p if k == owner else {'name': p['name'], 'addresses': []}
                                 for k, p in state['profiles'].items()}
        projected['orders'] = [o for o in state['orders'] if o['customer'] == owner]
        projected['events'] = []
        projected['bags'] = {owner or 'guest': state['bags'].get(owner or 'guest', {})}
    return projected


@router.get('/mock/session')
def session(request: Request, response: Response):
    token = request.cookies.get('studio_demo', '')
    with closing(connection()) as conn, conn:
        row = conn.execute('SELECT state FROM rehearsal WHERE session_hash=?',(key(token),)).fetchone() if token else None
        if row:
            state = json.loads(row[0])
        else:
            token = secrets.token_urlsafe(32)
            state = engine(catalog=catalog())['state']
            conn.execute('INSERT INTO rehearsal VALUES (?,?)',(key(token),json.dumps(state)))
            response.set_cookie('studio_demo', token, httponly=True, samesite='strict',
                                secure=request.url.scheme=='https')
    response.headers['Cache-Control'] = 'no-store'
    return view(state)


@router.post('/mock/action')
def action(payload: dict, request: Request, response: Response):
    if request.headers.get('X-Studio-Demo') != '1':
        raise HTTPException(403, 'Missing demo request header.')
    token = request.cookies.get('studio_demo')
    if not token:
        raise HTTPException(401,'Open a demo session first.')
    with closing(connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT state FROM rehearsal WHERE session_hash=?',(key(token),)).fetchone()
        if not row:
            raise HTTPException(401,'Open a demo session first.')
        result = engine(state=json.loads(row[0]),action=payload)
        conn.execute('UPDATE rehearsal SET state=? WHERE session_hash=?',(json.dumps(result['state']),key(token)))
    response.headers['Cache-Control'] = 'no-store'
    return {'state':view(result['state']), 'result':result['result']}


@router.post('/mock/provider/payment-event')
async def mock_payment_event(request: Request):
    """Optional sandbox adapter for replaying signed provider fixtures."""
    import hmac
    secret = os.environ.get('STUDIO_MOCK_WEBHOOK_SECRET')
    if not secret:
        raise HTTPException(503, 'Mock callback adapter is disabled.')
    raw = await request.body()
    expected = hmac.digest(secret.encode(), raw, 'sha256').hex()
    if not hmac.compare_digest(request.headers.get('X-Mock-Signature',''), expected):
        raise HTTPException(401, 'Invalid mock event signature.')
    try:
        data = json.loads(raw)
        target = data['order_id']
        event_id = data['event_id']
        amount = data['amount']
        currency = data['currency']
        if not isinstance(target,str) or not isinstance(event_id,str):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise HTTPException(422, 'Invalid mock event.')
    with closing(connection()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        # Each rehearsal owns a tiny private ledger. A real provider needs a
        # dedicated indexed transaction table before production deployment.
        for session_hash, encoded in conn.execute('SELECT session_hash,state FROM rehearsal'):
            state = json.loads(encoded)
            order = next((o for o in state['orders'] if o['id']==target), None)
            if order is None:
                continue
            if order['method'] != 'Prepaid':
                raise HTTPException(409, 'Only prepaid attempts accept provider events.')
            role, customer = state['role'], state['customer']
            state.update(role='Shopper',customer=order['customer'])
            updated = engine(state=state, action={'type':'receipt','id':target,
                             'event':event_id,'amount':amount,'currency':currency})['state']
            updated.update(role=role,customer=customer)
            conn.execute('UPDATE rehearsal SET state=? WHERE session_hash=?',
                         (json.dumps(updated),session_hash))
            return {'accepted':True}
    raise HTTPException(404, 'Demo order not found.')
