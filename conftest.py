import sys
import asyncio
import psycopg2
import pytest
import aiohttp
from modules.asyncdb import asyncDB
from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_user

sys.path.append("/home/ark/pyark")


@pytest.fixture(scope="session")
async def testdb():
    proc = await asyncio.create_subprocess_shell(
        "createdb pyark_pytest; pg_dump pyark -s | psql pyark_pytest",
        stdout=asyncio.subprocess.PIPE,
        stderr=None,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError("Error creating pyark_pytest database")
    testdb = asyncDB(db="pyark_pytest")
    yield testdb
    await testdb.close()
    proc = await asyncio.create_subprocess_shell(
        "dropdb pyark_pytest", stdout=asyncio.subprocess.PIPE, stderr=None
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError("Error deleting pyark_pytest database")


@pytest.fixture(scope="session")
async def testsession():
    async with aiohttp.ClientSession() as session:
        yield session


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
"""
