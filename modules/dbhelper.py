from configreader import psql_host, psql_port, psql_user, psql_pw, psql_db, psql_statsdb
import logging
import socket
from sys import exit
from timehelper import Now
import psycopg2

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def formatdbdata(data, table, qtype='tuple', db='sqldb', single=False, case='normal'):
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
                    if case == 'normal':
                        pstring = '%s' % (each[0])
                    elif case == 'title':
                        pstring = '%s' % (each[0].title())
                    elif case == 'capitalize':
                        pstring = '%s' % (each[0].capitalize())
                else:
                    if case == 'normal':
                        pstring = '%s' % (each)
                    elif case == 'title':
                        pstring = '%s' % (each.title())
                    elif case == 'capitalize':
                        pstring = '%s' % (each.capitalize())
            else:
                if single:
                    if case == 'normal':
                        pstring = pstring + ', %s' % (each[0])
                    elif case == 'title':
                        pstring = pstring + ', %s' % (each[0].title())
                    elif case == 'capitalize':
                        pstring = pstring + ', %s' % (each[0].capitalize())
                else:
                    if case == 'normal':
                        pstring = pstring + ', %s' % (each)
                    elif case == 'title':
                        pstring = pstring + ', %s' % (each.title())
                    elif case == 'capitalize':
                        pstring = pstring + ', %s' % (each.capitalize())
        return pstring
    elif qtype == 'list':
        plist = []
        for each in data:
            if single:
                if case == 'normal':
                    plist.append(each[0])
                elif case == 'title':
                    plist.append(each[0].title())
                elif case == 'capitalize':
                    plist.append(each[0].capitalize())
            else:
                plist.append(each)
        return plist
    elif qtype == 'dict':
        clmndata = db_getcolumns(table)
        clmnn = []
        for eclmn in clmndata:
            clmnn.append(eclmn[0])
        itern = 0
        if type(data) is tuple:
            nlist = {}
            nlist = dict(zip(clmnn, data))
            itern += 1
        else:
            nlist = []
            for eeach in data:
                itern += 1
                nlist.append(dict(zip(clmnn, eeach)))
        return nlist


def dbquery(query, db='sqldb', fetch='all', fmt='tuple', single=False):
    try:
        if db == 'sqldb':
            conn = psycopg2.connect(dbname=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        elif db == 'statsdb':
            conn = psycopg2.connect(dbname=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
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
            conn = psycopg2.connect(dbname=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        elif db == 'statsdb':
            conn = psycopg2.connect(dbname=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        c = conn.cursor()
    except:
        log.error(f'Error in database init: {db} - {query}')
        c.close()
        conn.close()
        return False
    else:
        try:
            c.execute(query)
            conn.commit()
        except:
            log.error(f'Error in Database update {query}')
            c.close()
            conn.close()
            return False
        c.close()
        conn.close()
        return True


def db_getcolumns(table):
    dbdata = dbquery("SELECT column_name, ordinal_position FROM information_schema.columns WHERE table_schema = 'public' and table_name = '%s'" % (table,))
    nt = ''
    for each in dbdata:
        nt = nt + f'{each[0]}[{each[1]-1}], '
    return nt


def db_gettables(db, fmt='tuple'):
    dbdata = dbquery("SELECT table_schema || '.' || table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')")
    return formatdbdata(dbdata, '', qtype=fmt)


def db_getall(table, fmt='tuple', fetch='all'):
    dbdata = dbquery("SELECT * FROM %s" % (table,), fetch=fetch)
    return formatdbdata(dbdata, table, qtype=fmt)


def db_getvalue(select, table, fmt='tuple', fetch='one'):
    dbdata = dbquery("SELECT %s FROM %s" % (select, table), fetch=fetch)
    return formatdbdata(dbdata, table, qtype=fmt, single=True)


def getplayer(steamid):
    dbdata = dbquery("SELECT * FROM players WHERE steamid = '%s'" % (steamid,), fetch='one')
    return dbdata


def getplayerlastseen(steamid='', playername=''):
    if playername != '':
        dbdata = dbquery("SELECT lastseen FROM players WHERE playername = '%s'" % (playername.lower(),), fetch='one', fmt='string')
    elif steamid != '':
        dbdata = dbquery("SELECT lastseen FROM players WHERE steamid = '%s'" % (steamid,), fetch='one', fmt='string')
    else:
        raise ValueError
        return None
    if dbdata:
        return int(dbdata)
    else:
        return None


def getplayerlastserver(steamid='', playername=''):
    if playername != '':
        dbdata = dbquery("SELECT server FROM players WHERE playername = '%s'" % (playername.lower(),), fetch='one', fmt='string')
    elif steamid != '':
        dbdata = dbquery("SELECT lastseen FROM players WHERE steamid = '%s'" % (steamid,), fetch='one', fmt='string')
    else:
        raise ValueError
        return None
    return dbdata


def getplayersonline(inst, fmt='tuple', case='normal'):
    if inst == 'all':
        dbdata = dbquery("SELECT playername FROM players WHERE lastseen > '%s'" % (Now() - 40))
    else:
        dbdata = dbquery("SELECT playername FROM players WHERE lastseen > '%s' AND server = '%s'" % (Now() - 40, inst.lower()))
    return formatdbdata(dbdata, 'players', qtype=fmt, case=case, single=True)


def getlastplayersonline(inst, fmt='tuple', last=5, case='normal'):
    if inst == 'all':
        dbdata = dbquery("SELECT playername FROM players WHERE lastseen < %s ORDER BY lastseen DESC LIMIT %s" % (Now() - 60, last))
    else:
        dbdata = dbquery("SELECT playername FROM players WHERE server = '%s' AND lastseen < %s ORDER BY lastseen DESC LIMIT %s" % (inst.lower(), Now() - 60, last))
    return formatdbdata(dbdata, 'players', qtype=fmt, case=case, single=True)


def isplayerlinked(discordid='', steamid=''):
    islinked = dbquery("SELECT * FROM players WHERE discordid = '%s'" % (duser.lower(),))
    if islinked:
        return True
    else:
        return False



def instancelist():
    dbdata = dbquery('SELECT name FROM instances', fmt='list', single=True)
    return dbdata


def getlastwipe(inst):
    dbdata = dbquery("SELECT lastdinowipe FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='string', fetch='one')
    if dbdata:
        return int(dbdata)
    else:
        return None


def getlastrestart(inst):
    dbdata = dbquery("SELECT lastrestart FROM instances WHERE name = '%s'" % (inst.lower(),), fetch='one', single=True)
    if dbdata:
        return int(dbdata[0])
    else:
        return None


def sendservermessage(inst, whos, msg):  # old writeglobal()
    dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
             (inst.lower(), whos, msg, Now()))


if __name__ == '__main__':
    exit()
