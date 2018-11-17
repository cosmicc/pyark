from modules.configreader import psql_host, psql_port, psql_user, psql_pw, psql_statsdb
from datetime import datetime, timedelta
import psycopg2
import pandas as pd

# conn = psycopg2.connect(dbname=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)

# df = pd.read_sql("SELECT * FROM extinction WHERE date > '{}' ORDER BY date DESC".format(datetime.now() - timedelta(days=30)), conn, parse_dates=['date'], index_col='date')


def lastweekavg():
    conn = psycopg2.connect(dbname=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
    df = pd.read_sql("SELECT * FROM ragnarok WHERE date > '{}' ORDER BY date DESC".format(datetime.now() - timedelta(days=8)), conn, parse_dates=['date'], index_col='date')
    conn.close()
    df = df.tz_localize(tz='UTC')
    df = df.tz_convert(tz='US/Eastern')
    newdf = df.resample('D').mean()
    datelist = []
    for each in newdf.index:
        datelist.append(each.strftime('%a'))
    return (datelist, newdf.values.round(1).tolist())


conn = psycopg2.connect(dbname=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
avglist = []
for each in ['island', 'ragnarok', 'volcano', 'extinction']:
    slist = []
    navglist = []
    dlist = []
    c = conn.cursor()
    print(each)
    c.execute("SELECT * FROM {} WHERE date > '{}' ORDER BY date DESC LIMIT 3".format(each, datetime.now() - timedelta(days=8)))
    nlist = c.fetchall()
    for y in nlist:
        slist.append(y[1])
        dlist.append(y[0])
    if avglist == []:
        avglist = slist
    else:
        navglist = [sum(pair) for pair in zip(slist, avglist)]
        avglist = navglist
print(list(zip(dlist, avglist)))
c.close()
conn.close()


