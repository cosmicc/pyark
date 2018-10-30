import logging, sqlite3, time, socket
from configreader import sqldb, statsdb

hstname = socket.gethostname()
log = logging.getLogger(name=hstname)


def dbquery(query, sdb='sqldb', fetch='all'):
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
            return dbdata
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


def numberliststring(qtype, data):
    pcnt = 0
    pstring = ''
    plist = []
    for each in data:
        pcnt += 1
        if pstring == '':
            pstring = '%s' % (each[0].title())
            plist.append(each[0].title())
        else:
            pstring = pstring + ', %s' % (each[0].title())
            plist.append(each[0].title())
    if qtype == 'number':
        return pcnt
    elif qtype == 'string':
        return pstring
    elif qtype == 'list':
        return plist


def getplayersonline(inst, qtype):
    if inst == 'all':
        dbdata = dbquery('SELECT playername FROM players WHERE lastseen > %s' % (time.time() - 40))
    else:
        dbdata = dbquery('SELECT playername FROM players WHERE lastseen > %s AND server == "%s"' % (time.time() - 40, inst))
    return numberliststring(qtype, dbdata)


def getinstances(qtype):
    dbdata = dbquery('SELECT name FROM instances')
    return numberliststring(qtype, dbdata)


def lastplayersonline(inst, qtype):
    pass


def sendservermessage(inst, whos, msg, ):  # old writeglobal()
    conn = sqlite3.connect(sqldb)
    c = conn.cursor()
    c.execute('INSERT INTO globalbuffer (server,name,message,timestamp) VALUES (?, ?, ?, ?)',
              (inst, whos, msg, time.time()))
    conn.commit()
    c.close()
    conn.close()


if __name__ == '__main__':
    # print(dbquery('SELECT playername FROM players WHERE lastseen > %s' % (time.time() - 40)))
    print(getinstances(qtype='list'))
