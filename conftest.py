import sys

import psycopg2

import pytest
from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_user
from modules.asyncdb import asyncDB

sys.path.append('/home/ark/pyark')

db = asyncDB()


@pytest.fixture(score="module")
async def asyncdb():
    await db.connect(min=1, max=1, timeout=30)
    conn = await db._aquire()
    yield conn
    await db._release(conn)


@pytest.fixture()
async def asyncdb_cursor(conn):
    cursor = await conn.cursor()
    yield cursor
    await conn.rollback()


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
