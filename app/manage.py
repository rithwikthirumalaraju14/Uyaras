"""Local setup, owner provisioning, reservations and notification delivery."""
import argparse
import getpass
import json
import os
import smtplib
import ssl
import time
from email.message import EmailMessage

from sqlalchemy import select

from .store import Store, users


def work(store):
    from .commerce import expire
    with store.transaction() as (_, state):
        expire(state)
        now = time.time()
        state['quotes'] = {k: q for k, q in state['quotes'].items() if q['expires'] > now}
        for n in state['outbox']:
            if n.get('kind') == 'password_reset' and n['created'] < now-1800 and n['status'] != 'sent':
                n['status'] = 'expired'
                n.pop('token', None)
        pending = [dict(n) for n in state['outbox'] if n['status'] == 'pending' or (n['status'] == 'sending' and n.get('lease', 0) < now)]
        for n in state['outbox']:
            if any(p['id'] == n['id'] for p in pending):
                n.update(status='sending', lease=now+120)
    for notice in pending:
        if not os.getenv('SMTP_HOST'):
            with store.transaction() as (_, state):
                next(n for n in state['outbox'] if n['id'] == notice['id'])['status'] = 'pending'
            continue
        try:
            with store.engine.connect() as conn:
                user = conn.execute(select(users).where(users.c.id == notice['user_id'])).mappings().one()
            mail = EmailMessage()
            mail['From'] = os.environ['SMTP_FROM']
            mail['To'] = user['email']
            mail['Message-ID'] = '<'+notice['id']+'@commerce.local>'
            if notice.get('kind') == 'password_reset':
                mail['Subject'] = 'Reset your store password'
                mail.set_content('Open this recovery link within 30 minutes: '+os.environ['PUBLIC_ORIGIN']+'/reset-password?token='+notice['token'])
            else:
                mail['Subject'] = 'Order update: '+notice['order_id']
                mail.set_content(notice['message']+'\n\nView your order: '+os.environ['PUBLIC_ORIGIN']+'/orders/'+notice['order_id'])
            with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.getenv('SMTP_PORT', '587')), timeout=20) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if os.getenv('SMTP_USER'):
                    smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
                smtp.send_message(mail)
            with store.transaction() as (_, state):
                record = next(n for n in state['outbox'] if n['id'] == notice['id'])
                record.update(status='sent', sent=time.time())
                record.pop('token', None)
        except Exception as exc:
            with store.transaction() as (_, state):
                record = next(n for n in state['outbox'] if n['id'] == notice['id'])
                record.update(status='pending', last_error=type(exc).__name__, attempts=record.get('attempts', 0)+1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['init', 'seed', 'owner', 'worker', 'recovery-token'])
    parser.add_argument('--email')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    store = Store()
    if args.command == 'init':
        print('Commerce database initialized.')
    elif args.command == 'seed':
        if os.getenv('PAYMENT_MODE', 'sandbox') != 'sandbox':
            parser.error('Sample data can only be seeded in sandbox mode.')
        store.seed()
        print('Sample catalog ready. Test PINs: 500001 and 520001. No owner password was created.')
    elif args.command == 'owner':
        email = args.email or input('Owner email: ').strip()
        password = getpass.getpass('Choose owner password (12+ characters): ')
        if password != getpass.getpass('Repeat password: '):
            parser.error('Passwords do not match.')
        store.owner(email, password)
        print('Owner created. Sign in through the Account page.')
    elif args.command == 'recovery-token':
        if os.getenv('PAYMENT_MODE', 'sandbox') != 'sandbox' or not args.email:
            parser.error('This local-only helper requires sandbox mode and --email.')
        with store.transaction() as (conn, state):
            user = conn.execute(select(users).where(users.c.email == args.email.lower())).mappings().one_or_none()
            messages = [n for n in state['outbox'] if user and n['user_id'] == user['id'] and n.get('kind') == 'password_reset' and n.get('token')]
            print(messages[-1]['token'] if messages else 'No pending recovery request.')
    else:
        while True:
            work(store)
            if args.once:
                break
            time.sleep(30)


if __name__ == '__main__':
    main()
