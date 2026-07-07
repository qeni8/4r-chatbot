import pytest

from app.db import pool


@pytest.fixture(scope="session", autouse=True)
def _db_pool():
    pool.open()
    yield
    pool.close()
