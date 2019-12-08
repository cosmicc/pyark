#!/usr/bin/env python3.7

import psycopg2
from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_user


def dbquery(query):
    conn = psycopg2.connect(dbname=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
    c = conn.cursor()
    resp = c.fetchall(query)
    c.close()
    conn.close()
    return resp


def dbupdate(query):
    conn = psycopg2.connect(dbname=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
    c = conn.cursor()
    c.execute(query)
    conn.commit()
    c.close()
    conn.close()


lottotable = dbquery("select * from lottteryinfo")

print(lottotable)
