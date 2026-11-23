import os
from functools import lru_cache

from .catalog import PUBLIC_CATEGORIES


class DatabaseUnavailable(Exception):
    pass


@lru_cache(maxsize=1)
def engine():
    from sqlalchemy import create_engine

    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql+psycopg://"):
        raise DatabaseUnavailable()
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3})


class PostgresCatalog:
    def _read(self, statement, params=None):
        from sqlalchemy import text
        from sqlalchemy.exc import SQLAlchemyError

        try:
            with engine().connect() as conn:
                return list(conn.execute(text(statement), params or {}).mappings())
        except SQLAlchemyError as exc:
            raise DatabaseUnavailable() from exc

    def ready(self):
        rows = self._read("SELECT version_num FROM alembic_version")
        return [row["version_num"] for row in rows] == ["0001"]

    def categories(self, page, page_size):
        return self._read(PUBLIC_CATEGORIES, {"limit": page_size, "offset": (page-1)*page_size})
