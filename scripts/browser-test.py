"""Run browser acceptance against an isolated PostgreSQL schema and isolated servers."""
import os
import secrets
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from sqlalchemy import create_engine,text,select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from uyaras.db import Base
from uyaras.models import Inventory,User
from uyaras.manage import seed
from uyaras.security import hash_password

root=Path(__file__).resolve().parents[1]
schema='browser_'+secrets.token_hex(8)
url=os.environ['UYARAS_DATABASE_URL'];admin=create_engine(url)
with admin.begin() as c:c.execute(text('CREATE SCHEMA '+schema))
engine=create_engine(make_url(url).update_query_dict({'options':'-csearch_path='+schema}))
Base.metadata.create_all(engine)
password=secrets.token_urlsafe(20)
with Session(engine) as db,db.begin():
    seed(db);db.flush()
    for stock in db.scalars(select(Inventory)):stock.on_hand=10
    db.add(User(email='owner@uyaras.test',name='Test owner',password=hash_password(password),role='Owner'))
env={**os.environ,'UYARAS_DATABASE_URL':engine.url.render_as_string(hide_password=False),'PUBLIC_ORIGIN':'http://localhost:3002','BACKEND_URL':'http://127.0.0.1:8005','APP_ENV':'development','NEXT_TELEMETRY_DISABLED':'1','UYARAS_TEST_PASSWORD':password}
flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
processes=[];logs=[]
try:
    for name,command,cwd in [('browser-api',[sys.executable,'-m','uvicorn','uyaras.main:create_app','--factory','--host','127.0.0.1','--port','8005','--no-access-log'],root),('browser-next',['node',str(root/'frontend/node_modules/next/dist/bin/next'),'dev','--hostname','127.0.0.1','--port','3002'],root/'frontend')]:
        log=(root/'tmp'/f'{name}.log').open('w');logs.append(log)
        processes.append(subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=log,creationflags=flags))
    for address in ['http://127.0.0.1:8005/health','http://localhost:3002']:
        for attempt in range(90):
            try:
                with urllib.request.urlopen(address,timeout=5) as r:
                    if r.status==200:break
            except Exception:time.sleep(1)
        else:raise RuntimeError('Browser test server did not start: '+address)
    # Compile route modules before timing interactive journeys against the dev server.
    for path in ['/products','/products/everyday-crew','/account','/cart','/checkout','/orders','/admin']:
        with urllib.request.urlopen('http://localhost:3002'+path,timeout=120) as response:
            response.read()
    result=subprocess.run(['node',str(root/'node_modules/@playwright/test/cli.js'),'test','-c','playwright.uyaras.config.cjs',*sys.argv[1:]],cwd=root,env=env,creationflags=flags)
    code=result.returncode
finally:
    for p in processes:
        if os.name=='nt':subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
        else:p.terminate()
    for p in processes:p.wait(timeout=15)
    for log in logs:log.close()
    engine.dispose()
    with admin.begin() as c:c.execute(text('DROP SCHEMA '+schema+' CASCADE'))
    admin.dispose()
sys.exit(code)
