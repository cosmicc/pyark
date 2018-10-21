import sqlite3, socket, logging
from time import time, sleep
from configreader import statsdb, sqldb

statinst = ['ragnarok', 'island', 'volcano']

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def checkiftableexists(inst):
    conn = sqlite3.connect(statsdb)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS %s (date INTEGER, value INTEGER)' % (inst,))
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
    ldate = int(time())
    conn = sqlite3.connect(statsdb)
    c = conn.cursor()
    c.execute('INSERT INTO %s (date, value) VALUES (%s, %s)' % (inst, ldate, value))
    conn.commit()
    c.close()
    conn.close()


def flushold(tinst):
    aweek = int(time()) - 2592000
    conn = sqlite3.connect(statsdb)
    c = conn.cursor()
    c.execute('DELETE FROM %s WHERE date < %s' % (tinst, aweek))
    conn.commit()
    c.close()
    conn.close()


def howmanyon(inst):
    conn1 = sqlite3.connect(sqldb)
    c1 = conn1.cursor()
    c1.execute('SELECT * from players')
    allplayers = c1.fetchall()
    c1.close()
    conn1.close()
    pcnt = 0
    now = time()
    for row in allplayers:
        diff_time = float(now) - float(row[2])
        total_min = diff_time / 60
        minutes = int(total_min % 60)
        hours = int(total_min / 60)
        days = int(hours / 24)
        if minutes <= 1 and hours < 1 and days < 1 and row[3] == inst:
            pcnt += 1
    return pcnt


def oscollect():
    log.debug(f'starting online stats collector for instances {statinst}')
    while True:
        try:
            for each in statinst:
                checkiftableexists(each)
                flushold(each)
                addvalue(each, howmanyon(each))
        except:
            log.critical('Critical Error in Online Stat Collector!', exc_info=True)
        sleep(300)
