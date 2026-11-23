import os
import time
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session


def uid():
    return uuid.uuid4().hex


def now():
    return int(time.time())


class Base(DeclarativeBase):
    pass


def engine_for(url=None):
    url = url or os.environ.get("UYARAS_DATABASE_URL")
    if not url or not url.startswith("postgresql"):
        raise RuntimeError(
            "UYARAS_DATABASE_URL must be a PostgreSQL connection URL. Run start.ps1."
        )
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


def session(request):
    with Session(request.app.state.engine, expire_on_commit=False) as db:
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
