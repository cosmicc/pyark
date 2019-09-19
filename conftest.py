import sys

import psycopg2
import pytest
from modules.asyncdb import asyncDB
from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_user

sys.path.append('/home/ark/pyark')

db = asyncDB()


@pytest.fixture(scope="function")
async def db():
    await db.connect(min=1, max=10, timeout=30)
    yield db
    await db.close()


"""
@pytest.fixture()
async def asyncdb_cursor(conn):
    cursor = await conn.cursor()
    yield cursor
    await conn.rollback()
"""


@pytest.fixture(scope='module')
def conn():
    conn = psycopg2.connect(dbname=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
    yield conn
    conn.close()


@pytest.fixture()
def cursor(conn):
    cursor = conn.cursor()
    yield cursor
    conn.rollback()
