from configreader import sqldb, statsdb
import logging
import socket
import sqlite3
from sys import exit
from timehelper import Now

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def formatdbdata(data, table, qtype='tuple', db='sqldb', single=False):
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


def dbquery(query, db='sqldb', fetch='all', fmt='tuple', single=False):
    try:
        if db == 'sqldb':
            conn = sqlite3.connect(sqldb)
        elif db == 'statsdb':
            conn = sqlite3.connect(statsdb)
        c = conn.cursor()
        c.execute(query)
    except:
        log.error(f'Error in database init: {db} - {query} - {fetch}')
        c.close()
        conn.close()
    else:
        try:
            if fetch == 'all':
                dbdata = c.fetchall()
            elif fetch == 'one':
                dbdata = c.fetchone()
        except:
            log.error(f'Error in {db} database query {query}')
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
                return formatdbdata(dbdata, table, qtype=fmt, db=db, single=single)
        else:
            return None


def dbupdate(query, db='sqldb'):
    try:
        if db == 'sqldb':
            conn = sqlite3.connect(sqldb)
        elif db == 'statsdb':
            conn = sqlite3.connect(statsdb)
        c = conn.cursor()
    except:
        log.error(f'Error in database init: {db} - {query}')
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


def db_getcolumns(table, fmt='tuple'):
    dbdata = dbquery("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' and table_name = '%s'" % (table,))
    return formatdbdata(dbdata, table, qtype=fmt)


def db_gettables(db, fmt='tuple'):
    dbdata = dbquery("SELECT table_schema || '.' || table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')")
    return formatdbdata(dbdata, qtype=fmt)


def db_getall(table, fmt='tuple', fetch='all'):
    dbdata = dbquery("SELECT * FROM '%s'" % (table,), fetch=fetch)
    return formatdbdata(dbdata, table, qtype=fmt)


def db_getvalue(select, table, fmt='tuple', fetch='one'):
    dbdata = dbquery("SELECT %s FROM '%s'" % (select, table), fetch=fetch)
    return formatdbdata(dbdata, table, qtype=fmt, single=True)


def getplayersonline(inst, fmt='tuple'):
    if inst == 'all':
        dbdata = dbquery("SELECT playername FROM players WHERE lastseen > '%s'" % (Now() - 40))
    else:
        dbdata = dbquery("SELECT playername FROM players WHERE lastseen > '%s' AND server == '%s'" % (Now() - 40, inst))
    return formatdbdata(dbdata, 'players', qtype=fmt)


def getlastplayersonline(inst, fmt='tuple', last=5):
    if inst == 'all':
        dbdata = dbquery("SELECT playername FROM players ORDER BY lastseen LIMIT '%s'" % (last,))
    else:
        dbdata = dbquery("SELECT playername FROM players ORDER BY lastseen AND server == '%s' LIMIT '%s'" % (inst, last))
    return formatdbdata(dbdata, 'players', qtype=fmt)


def sendservermessage(inst, whos, msg):  # old writeglobal()
    dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
             (inst, whos, msg, Now()))


if __name__ == '__main__':
    exit()
