from modules.configreader import psql_host, psql_port, psql_user, psql_pw, psql_db, psql_statsdb
from datetime import datetime
from loguru import logger as log
import psycopg2
import asyncpg
from time import sleep
import asyncio


@log.catch
async def asyncdbquery(query, db='sqldb', fetch='all', fmt='tuple', single=False):
    asyncloop = asyncio.get_running_loop()
    data = asyncloop.create_task(llasyncdbquery(query, db, fetch, fmt, single))
    return await data


@log.catch
async def llasyncdbquery(query, db, fetch, fmt, single):
    try:
        if db == 'sqldb':
            conn = await asyncpg.connect(database=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        elif db == 'statsdb':
            conn = await asyncpg.connect(database=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
    except:
        log.critical('ERROR CONNECTING TO DATABASE SERVER')
        await conn.close()
        asyncio.sleep(60)
        return None
    else:
        try:
            if fetch == 'all':
                dbdata = await conn.fetchall()
            elif fetch == 'one':
                dbdata = await conn.fetchrow()
        except:
            log.error(f'Error in {db} database query {query}')
            await conn.close()
            return None
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


@log.catch
async def asyncdbupdate(query, db='sqldb', fetch='all', fmt='tuple', single=False):
    asyncloop = asyncio.get_running_loop()
    data = asyncloop.create_task(llasyncdbupdate(query, db))
    return await data


@log.catch
async def asyncglupdate(inst, ptype, text):
    asyncloop = asyncio.get_running_loop()
    query = (inst, ptype, text)
    data = asyncloop.create_task(llasyncdbupdate(query, 'gamelog'))
    return await data


@log.catch
async def llasyncdbupdate(query, db):
    try:
        if db == 'sqldb':
            conn = await asyncpg.connect(database=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        elif db == 'statsdb':
            conn = await asyncpg.connect(database=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        elif db == 'gamelog':
            conn = await asyncpg.connect(database='gamelog', user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
    except:
        log.exception('ERROR CONNECTING TO DATABASE SERVER')
        await conn.close()
        asyncio.sleep(60)
        return False
    else:
        try:
            if db == 'gamelog':
                sql = "INSERT INTO gamelog (instance, loglevel, logline) VALUES ($1, $2, $3)"
                await conn.execute(sql, query[0].lower(), query[1].upper(), query[2])
                log.debug(f'gamelog line added async')
            else:
                await conn.execute(query)
        except:
            log.exception(f'Error in Database update {query}')
            await conn.close()
            return False
        await conn.close()
        return True


@log.catch
def glupdate(inst, ptype, text):
    try:
        conn = psycopg2.connect(dbname='gamelog', user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        c = conn.cursor()
    except psycopg2.OperationalError:
        log.critical('ERROR CONNECTING TO DATABASE SERVER')
        sleep(60)
        c.close()
        conn.close()
        return False
    except:
        log.error(f'Error in database init: gamelogdb - {text}')
        c.close()
        conn.close()
        return False
    else:
        sql = "insert into gamelog (instance, loglevel, logline) values (%s, %s, %s)"
        c.execute(sql, (inst.lower(), ptype.upper(), text))
        conn.commit()
        return True
        c.close()
        conn.close()


def cleanstring(name):
    return name.replace('"', '').replace("'", "").replace("(", "").replace(")", "")


@log.catch
def formatdbdata(data, table, qtype='tuple', db='sqldb', single=False, case='normal'):
    if data is not None:
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
            clmndata = db_getcolumns(table, raw=True)
            itern = 0
            if type(data) is tuple:
                nlist = {}
                nlist = dict(zip(clmndata, data))
                itern += 1
            else:
                nlist = []
                for eeach in data:
                    itern += 1
                    nlist.append(dict(zip(clmndata, eeach)))
            return nlist
    else:
        return None


@log.catch
def dbquery(query, db='sqldb', fetch='all', fmt='tuple', single=False):
    try:
        if db == 'sqldb':
            conn = psycopg2.connect(dbname=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        elif db == 'statsdb':
            conn = psycopg2.connect(dbname=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        c = conn.cursor()
        c.execute(query)
    except psycopg2.OperationalError:
        log.critical('ERROR CONNECTING TO DATABASE SERVER')
        sleep(60)
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


@log.catch
def statsupdate(inst, value):
    conn = psycopg2.connect(dbname=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
    c = conn.cursor()
    c.execute("INSERT INTO %s (date, value) VALUES ('%s', '%s')" % (inst.lower(), datetime.now().replace(microsecond=0), value))
    conn.commit()
    c.close()
    conn.close()


@log.catch
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


@log.catch
def db_getcolumns(table, raw=False):
    dbdata = dbquery("SELECT column_name, ordinal_position, data_type  FROM information_schema.columns WHERE table_schema = 'public' and table_name = '%s'" % (table,))
    nt = ''
    ntl = []
    for each in dbdata:
        if not raw:
            nt = nt + f'{each[1]-1} {each[0]} ({each[2]})\n'
        elif raw:
            ntl.append(each[0])
    if not raw:
        return nt
    elif raw:
        return ntl


@log.catch
def db_gettables(db, fmt='tuple'):
    dbdata = dbquery("SELECT table_schema || '.' || table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')")
    return formatdbdata(dbdata, '', qtype=fmt)


@log.catch
def db_getall(table, fmt='tuple', fetch='all'):
    dbdata = dbquery("SELECT * FROM %s" % (table,), fetch=fetch)
    return formatdbdata(dbdata, table, qtype=fmt)


@log.catch
def db_getvalue(select, table, fmt='tuple', fetch='one'):
    dbdata = dbquery("SELECT %s FROM %s" % (select, table), fetch=fetch)
    return formatdbdata(dbdata, table, qtype=fmt, single=True)
