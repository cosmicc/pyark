from configreader import sqldb, statsdb
import logging
import socket
import sqlite3
import time

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def formatdbdata(data, table, qtype='tuple', sdb='sqldb', single=False):
    if qtype == 'tuple':
        return data
    elif qtype == 'count':
        pcnt = 0
        for each in data:
            pcnt += 1
        return pcnt
    elif qtype == 'string':
        pstring = ''
        for each in data:
            if pstring == '':
                if single:
                    pstring = '%s' % (each[0])
                else:
                    pstring = '%s' % (each)
            else:
                if single:
                    pstring = pstring + ', %s' % (each[0])
                else:
                    pstring = pstring + ', %s' % (each)
        return pstring
    elif qtype == 'list':
        plist = []
        for each in data:
            if single:
                plist.append(each[0])
            else:
                plist.append(each)
        return plist
    elif qtype == 'dict':
        clmndata = dbquery('PRAGMA table_info("%s")' % (table,))
        clmnn = []
        for eclmn in clmndata:
            clmnn.append(eclmn[1])
        nlist = []
        itern = 0
        for edata in data:
            nlist.append(dict(zip(clmnn, edata)))
            itern += 1
        return nlist


def dbquery(query, sdb='sqldb', fetch='all', fmt='tuple', single=False):
    try:
        if sdb == 'sqldb':
            conn = sqlite3.connect(sqldb)
        elif sdb == 'statsdb':
            conn = sqlite3.connect(statsdb)
        c = conn.cursor()
        c.execute(query)
    except:
        log.error(f'Error in database init: {sdb} - {query} - {fetch}')
        c.close()
        conn.close()
    else:
        try:
            if fetch == 'all':
                dbdata = c.fetchall()
            elif fetch == 'one':
                dbdata = c.fetchone()
        except:
            log.error(f'Error in {sdb} database query {query}')
        c.close()
        conn.close()
        if dbdata is not None:
            if fmt == 'tuple':
                return dbdata
            else:
                a = (query.split('FROM'))
                if len(a) > 1:
                    b = a[1].split(' ')
                    table = b[1]
                return formatdbdata(dbdata, table, qtype=fmt, sdb=sdb, single=single)
        else:
            return None


def dbupdate(query, sdb='sqldb'):
    try:
        if sdb == 'sqldb':
            conn = sqlite3.connect(sqldb)
        elif sdb == 'statsdb':
            conn = sqlite3.connect(statsdb)
        c = conn.cursor()
    except:
        log.error(f'Error in database init: {sdb} - {query}')
        c.close()
        conn.close()
    else:
        try:
            c.execute(query)
            conn.commit()
        except:
            log.error(f'Error in Database update {query}')
        c.close()
        conn.close()


def gettablevalue(select, table, qtype='tuple'):
    dbdata = dbquery('SELECT %s FROM "%s"' % (select, table))
    return formatdbdata(dbdata, table, qtype)


def getplayersonline(inst, qtype='tuple'):
    if inst == 'all':
        dbdata = dbquery('SELECT playername FROM players WHERE lastseen > "%s"' % (time.time() - 40))
    else:
        dbdata = dbquery('SELECT playername FROM players WHERE lastseen > "%s" AND server == "%s"' % (time.time() - 40, inst))
    return formatdbdata(dbdata, 'players', qtype)


def getlastplayersonline(inst, qtype):
    if inst == 'all':
        dbdata = dbquery('SELECT playername FROM players ORDER BY lastseen LIMIT 5' % (time.time() - 40))
    else:
        dbdata = dbquery('SELECT playername FROM players ORDER BY lastseen AND server == "%s" LIMIT 5' % (time.time() - 40, inst))
    return formatdbdata(dbdata, 'players', qtype)


def getallinstancenames():
    return dbquery('SELECT name FROM instances', fmt='list', single=True)


def sendservermessage(inst, whos, msg):  # old writeglobal()
    dbupdate('INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ("%s", "%s", "%s", "%s")' %
             (inst, whos, msg, time.time()))


if __name__ == '__main__':
    # print(dbquery('SELECT playername FROM players WHERE lastseen > %s' % (time.time() - 40)))
    # print(dbquery("SELECT * FROM instances", fmt='list', single=False))
    print(getallinstancenames())

