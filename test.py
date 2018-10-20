import sqlite3
from datetime import datetime
from configreader import statsdb


def checkiftableexists(inst):
    conn = sqlite3.connect(statsdb)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS %s (date TEXT, value INTEGER)' % (inst,))
    conn.commit()
    c.close()
    conn.close()


def checkifinstexistsOLD(inst):
    conn = sqlite3.connect(statsdb)
    c = conn.cursor()
    c.execute('PRAGMA table_info({})'.format('online'))
    alldata = c.fetchall()
    c.close()
    conn.close()
    tot = 0
    for f in alldata:
        if f[1] == inst:
            tot += 1
    if tot == 0:
        conn = sqlite3.connect(statsdb)
        c = conn.cursor()
        c.execute('ALTER TABLE online ADD COLUMN %s TEXT' % (inst,))
        conn.commit()
        c.close()
        conn.close()


def addvalue(inst, value):
    now = datetime.now()
    ldate = now.strftime("%y-%m-%d,")
    print(ldate)
    conn = sqlite3.connect(statsdb)
    c = conn.cursor()
    c.execute('INSERT INTO %s (date, value) VALUES (%s, %s)' % (inst, ldate, value))
    conn.commit()
    c.close()
    conn.close()


checkiftableexists('ragnarok')
addvalue('ragnarok', 3)
conn = sqlite3.connect(statsdb)
c = conn.cursor()
c.execute('SELECT * FROM ragnarok')
alldata = c.fetchall()
c.close()
conn.close()
print(alldata)



