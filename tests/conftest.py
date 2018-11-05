import psycopg2
import pytest
import sys
sys.path.append('/home/ark/pyark')
from modules.configreader import psql_host, psql_port, psql_user, psql_pw, psql_db, psql_statsdb


@pytest.fixture(scope='module')
def conn():
    conn = psycopg2.connect(dbname=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
    yield conn
    conn.close()


@pytest.fixture(scope='module')
def cursor(conn):
    cursor = conn.cursor()
    yield cursor
    conn.rollback()
