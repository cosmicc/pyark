#!/usr/bin/env python3.7

import psycopg2
from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_user


def dbquery(query):
    conn = psycopg2.connect(dbname=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
    c = conn.cursor()
    c.execute(query)
    resp = c.fetchall()
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


lottotable = dbquery("select * from lotteryinfo")

players = {}

for entry in lottotable:
    if entry[6] in players:
        p = players[entry[6]]
        newpoints = p[0] + entry[1]
        newwins = p[1] + 1
        players.update({entry[6]: [newpoints, newwins]})
    else:
        if entry[6] != 'None' and entry[6] != 'Incomplete':
            players.update({entry[6]: [entry[1], 1]})

for each, val in players.items():
        print(f'{each} - {val}')
        dbupdate(f"UPDATE players set lottowins = {val[1]}, lotterywinnings = {val[0]} where playername = '{each}'")
