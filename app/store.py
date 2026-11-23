"""Durable shared store with a database-wide checkout transaction.

SQLite serializes writers with BEGIN IMMEDIATE; PostgreSQL locks the singleton
aggregate row. This intentionally favors correctness over write throughput for
the initial single-warehouse store. Identity and session data are separate.
"""
import copy
import hashlib
import json
import os
import re
import secrets
import time
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Column, Float, MetaData, String, Table, Text, create_engine, select, update

ROOT = Path(__file__).resolve().parents[1]
metadata = MetaData()
state_table = Table('commerce_state', metadata, Column('id', String, primary_key=True), Column('body', Text, nullable=False))
users = Table('commerce_user', metadata, Column('id', String, primary_key=True), Column('email', String, unique=True, nullable=False), Column('password', Text, nullable=False), Column('name', String, nullable=False), Column('role', String, nullable=False))
sessions = Table('commerce_session', metadata, Column('id', String, primary_key=True), Column('user_id', String), Column('csrf', String, nullable=False), Column('expires', Float, nullable=False))
resets = Table('commerce_reset', metadata, Column('id', String, primary_key=True), Column('user_id', String, nullable=False), Column('expires', Float, nullable=False))


def uid():
    return secrets.token_hex(16)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


def password_matches(password, encoded):
    return secrets.compare_digest(password_hash(password, encoded.split(':')[0]), encoded)


def initial_state():
    return dict(products={}, categories={}, collections={}, stock={}, carts={}, addresses={}, orders={}, quotes={}, rules={}, promotions={}, audit=[], inbox={}, outbox=[], requests={})


class Store:
    def __init__(self, url=None):
        self.url = url or os.getenv('COMMERCE_DATABASE_URL', 'sqlite:///commerce.sqlite3')
        self.engine = create_engine(self.url, connect_args={'check_same_thread': False, 'timeout': 30} if self.url.startswith('sqlite') else {}, pool_pre_ping=True)
        metadata.create_all(self.engine)
        # Initialization happens before workers start in the documented launcher.
        with self.engine.begin() as c:
            if c.execute(select(state_table.c.id)).first() is None:
                c.execute(state_table.insert().values(id='store', body=json.dumps(initial_state())))

    @contextmanager
    def transaction(self):
        with self.engine.connect() as c:
            if self.url.startswith('sqlite'):
                c.exec_driver_sql('BEGIN IMMEDIATE')
            else:
                c.begin()
            try:
                row = c.execute(select(state_table.c.body).where(state_table.c.id == 'store').with_for_update()).scalar_one()
                state = json.loads(row)
                yield c, state
                c.execute(update(state_table).where(state_table.c.id == 'store').values(body=json.dumps(state)))
                c.commit()
            except BaseException:
                c.rollback()
                raise

    def seed(self):
        with self.transaction() as (_, s):
            if s['products']:
                return
            source = json.loads((ROOT / 'mock_store/catalog.json').read_text(encoding='utf-8'))
            for name in ['Men', 'Women']:
                s['categories'][name.lower()] = dict(id=name.lower(), name=name, slug=name.lower(), parent_id=None, published=True)
            for p in source['products']:
                slug = p['name'].lower().replace(' ', '-')
                variants = []
                for colour, _ in p['colours']:
                    for size in source['sizes']:
                        sku = f"{p['id']}-{colour}-{size}".upper()
                        variants.append(dict(sku=sku, size=size, colour=colour, active=True))
                        s['stock'][sku] = dict(on_hand=10, reserved=0, low_stock=3)
                s['products'][p['id']] = dict(id=p['id'], slug=slug, name=p['name'], description=p['note'], price=p['example_price']*100, category=p['audience'].lower(), status='published', variants=variants, images=[dict(url=f"/art/{p['id']}-{c.lower()}.webp", alt=f"{p['name']} in {c}") for c, _ in p['colours']], care='Sample content: wash cold with similar colours.', size_guide='Sample chest measurements: S 96 cm, M 102 cm, L 108 cm, XL 114 cm.', created=time.time())
            s['rules']['500001'] = dict(pin='500001', name='Hyderabad test coverage', shipping=4000, cod=True, cod_fee=2000, cod_max=500000, free_over=149900, tax_bps=0, days='3–5 business days (test)')
            s['rules']['520001'] = dict(pin='520001', name='Vijayawada test coverage', shipping=4000, cod=False, cod_fee=0, cod_max=0, free_over=149900, tax_bps=0, days='3–5 business days (test)')
            s['promotions']['WELCOME10'] = dict(code='WELCOME10', percent=10, minimum=0, limit=100, active=True, start=0, end=0)

    def owner(self, email, password, name='Store owner'):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise ValueError('Enter a valid owner email address.')
        if len(password) < 12:
            raise ValueError('Owner password must contain at least 12 characters.')
        with self.transaction() as (c, s):
            if c.execute(select(users).where(users.c.email == email.lower())).first():
                raise ValueError('This email already exists; no account was changed.')
            user_id = uid()
            c.execute(users.insert().values(id=user_id, email=email.lower(), password=password_hash(password), name=name, role='Owner'))
            s['audit'].append(dict(at=time.time(), actor='setup', action='owner_created', target=user_id))
