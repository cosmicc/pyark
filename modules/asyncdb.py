import asyncio
from datetime import datetime

import asyncpg
from loguru import logger as log

from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_user


class asyncDB:
    def __init__(self):
        log.trace(f'Starting async db connection engine')
        self.querytypes = ('tuple', 'dict', 'count', 'list', 'record')
        self.databases = ('pyark', 'py', 'stats', 'st', 'gamelog', 'gl')
        self.dbpyark = ('pyark', 'py')
        self.dbstats = ('stats', 'st')
        self.dbgamelog = ('gamelog', 'gl')
        self.cpool = None
        self.connecting = False

    async def connect(self, process=__file__, min=1, max=10, timeout=300):
        self.process = process
        self.min = min
        self.max = max
        self.timeout = timeout
        self.connecting = True
        try:
            self.cpool = await asyncpg.create_pool(min_size=self.min, max_size=self.max, max_inactive_connection_lifetime=float(self.timeout), database=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        except:
            log.critical('Error connecting to database server.. waiting to reconnect')
            await asyncio.sleep(5)
            await self.connect()
        else:
            log.debug(f'Database connection pool initilized for [{self.process}] (min:{self.min}, max:{self.max}, timeout:{self.timeout})')
            self.connecting = False
        # self.player_by_id = self.dbconn.prepare("""SELECT * FROM players WHERE steamid = '$1'""")

    async def close(self):
        if self.cpool is not None:
            await self.cpool.close()
        log.debug(f'Database connection pool closed for [{self.process}]')

    async def _aquire(self):
        while self.connecting and self.cpool is None:
            await asyncio.sleep(.1)
        if not self.connecting and self.cpool is None:
            self.connecting = True
            log.trace('Database is not connected. connecting...')
            await self.connect()
        try:
            con = await self.cpool.acquire(timeout=30)
        except:
            log.exception('Error aquiring a db pool connection, retrying..')
            await asyncio.sleep(1)
        else:
            return con

    async def _release(self, connection):
        try:
            await self.cpool.release(connection)
        except:
            log.exception('Error releasing db pool connection')
            return False
        else:
            return True

    async def testvars(self, query, result, db):
        if not isinstance(query, str):
            raise TypeError('Query is not type string')
        if db not in self.databases:
            raise ValueError(f'Invalid database [{db}]')
        if result not in self.querytypes:
            raise ValueError(f'Invalid result type [{result}]')

    async def fetchall(self, query, result='record', db='pyark'):
        await self.testvars(query, result, db)
        return await self._query(query, 'all', result, db)

    async def fetchone(self, query, result='record', db='pyark'):
        await self.testvars(query, result, db)
        return await self._query(query, 'one', result, db)

    async def _query(self, query, fetch, fmt, db):
        try:
            con = await self._aquire()
            if fetch == 'one':
                dbdata = await con.fetchrow(query)
            elif fetch == 'all' or fmt == "count":
                dbdata = await con.fetch(query)
            # log.trace(f'Executing DB [{db}] query {query}')
        except:
            log.exception(f'Error in database query {query} in {db}')
            return None
        finally:
            await self._release(con)
        if dbdata is not None:
            # log.trace(f'Retrieved DB [{db}] result {dbdata}')
            if fmt == 'record':
                return dbdata
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
        else:
            return None

    async def _execute(self, query, db):
        con = await self._aquire()
        if db in self.dbgamelog:
            sql = "INSERT INTO gamelog (instance, loglevel, logline) VALUES ($1, $2, $3)"
            try:
                await con.execute(sql, query[0].lower(), query[1].upper(), query[2])
            except:
                log.exception(f'Exception in db stat update {query}')
                return False
            finally:
                await self._release(con)
        else:
            try:
                await con.execute(query)
            except:
                log.exception(f'Exception in db update {query}')
                return False
            finally:
                await self._release(con)
        return True

    async def update(self, query, db='pyark'):
        if db not in self.databases:
            raise ValueError(f'Invalid database [{db}]')
        # if (db not in self.dbgamelog and not isinstance(query, str)) or (db in self.dbgamelog and not isinstance(query, list)):
        #    raise TypeError(f'Query type is invalid [{type(query)}]')
        # log.trace(f'Executing DB [{db}] update {query}')
        return await self._execute(query, db)

    async def statsupdate(self, inst, value):
        await self.update(f"INSERT INTO {inst.lower()}_stats (date, value) VALUES ('{datetime.now().replace(microsecond=0)}', {value})")


DB = asyncDB()
