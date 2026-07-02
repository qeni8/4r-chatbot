from collections.abc import Iterator
from contextlib import contextmanager

from psycopg import Connection
from psycopg_pool import ConnectionPool

from app.config import settings

pool = ConnectionPool(settings.database_url, min_size=1, max_size=10, open=False)


@contextmanager
def get_conn() -> Iterator[Connection]:
    with pool.connection() as conn:
        yield conn
