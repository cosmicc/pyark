import sys

import psycopg2

import pytest
from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_statsdb, psql_user

sys.path.append('/home/ark/pyark')


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
