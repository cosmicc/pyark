from modules.configreader import psql_host, psql_port, psql_user, psql_pw, psql_db, psql_statsdb, hstname
from loguru import logger as log
import asyncio
import uvloop
import asyncpg
from threading import Thread
import time


class asyncDB():
    def __init__(self):
        log.trace('starting async db engine')

    async def connect(self):
        self.dbeventloop = asyncio.get_running_loop()
        self.pydbconn = await asyncpg.connect(database='pyark', user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        self.gldbconn = await asyncpg.connect(database='gamelog', user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        log.debug('Connections established to database server')

    async def disconnect(self):
        await self.pydbconn.close()
        await self.gldbconn.close()
        log.debug('Database connections closed')

    async def pyquery(self, query, fetch, fmt):
        try:
            if fetch == 'one':
                dbdata = await self.pydbconn.fetchrow(query)
            elif fetch == 'all' or fmt == "count":
                dbdata = await self.pydbconn.fetch(query)
        except:
            log.exception(f'Error in {db} database query {query}')
            return None
        if dbdata is not None:
            if fmt == 'count':
                return len(dbdata)
            elif fmt == 'tuple':
                return tuple(dbdata)
            elif fmt == 'dict' and fetch == 'one':
                return dict(dbdata)
            elif fmt == 'dict' and fetch == 'all':
                return dbdata
            elif fmt == 'list':
                return list(tuple(dbdata))
            elif fmt == 'string':
                pass
                # return dbstringformat(dbdata)
        else:
            return None

    async def pyupdate(self, query):
        try:
            await self.pydbconn.execute(query)
        except:
            log.exception(f'Error in Database update {query}')
            return False
        return True

    async def glupdate(self, query):
        try:
            sql = "INSERT INTO gamelog (instance, loglevel, logline) VALUES ($1, $2, $3)"
            await self.gldbconn.execute(sql, query[0].lower(), query[1].upper(), query[2])
        except:
            log.exception(f'Error in Database update {query}')
            return False
        return True


@log.catch
async def start():
    global db
    db = asyncDB()
    await db.connect()


@log.catch
async def stop():
    await db.disconnect()


@log.catch
def dbeventthread():
    log.debug(f'Starting database connection thread for {hstname}')
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    dbeventloop = asyncio.new_event_loop()
    dbeventloop.create_task(start())
    dbeventloop.run_forever()


def pyark():
    el = Thread(target=dbeventthread, daemon=True)
    el.start()
    time.sleep(5)


@log.catch
async def asyncdbupdate(query, db='sqldb', fetch='all', fmt='tuple', single=False):
    asyncio.create_task(llasyncdbupdate(query, db))
    return True


@log.catch
async def asyncdbquery(query, fmt, fetch, db='sqldb', single=False):
    data = asyncio.create_task(llasyncdbquery(query, db, fetch, fmt, single))
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
            if fetch == 'one':
                dbdata = await conn.fetchrow(query)
            elif fetch == 'all' or fmt == "count":
                dbdata = await conn.fetch(query)
            await conn.close()
        except:
            log.exception(f'Error in {db} database query {query}')
            await conn.close()
            return None
        if dbdata is not None:
            if fmt == 'count':
                return len(dbdata)
            elif fmt == 'tuple':
                return tuple(dbdata)
            elif fmt == 'dict' and fetch == 'one':
                return dict(dbdata)
            elif fmt == 'dict' and fetch == 'all':
                return dbdata
            elif fmt == 'list':
                return list(tuple(dbdata))
            elif fmt == 'string':
                pass
                # return dbstringformat(dbdata)
        else:
            return None



@log.catch
async def asyncglupdate(inst, ptype, text):
    query = (inst, ptype, text)
    asyncio.create_task(llasyncdbupdate(query, 'gamelog'))
    return True


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
            else:
                await conn.execute(query)
            await conn.close()
        except:
            log.exception(f'Error in Database update {query}')
            await conn.close()
            return False
        await conn.close()
        return True
