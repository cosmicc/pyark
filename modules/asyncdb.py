import asyncio

import asyncpg
from loguru import logger as log
from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_user


class asyncDB:
    def __init__(self):
        log.trace('Starting async db connection engine')
        self.loop = asyncio.get_running_loop()
        self.querytypes = ('tuple', 'dict', 'count', 'list', 'record')
        self.databases = ('pyark', 'py', 'stats', 'st', 'gamelog', 'gl')
        self.dbpyark = ('pyark', 'py')
        self.dbstats = ('stats', 'st')
        self.dbgamelog = ('gamelog', 'gl')
        self.cpool = None

    async def _connect(self):
        self.dbeventloop = asyncio.get_running_loop()
        self.cpool = await asyncpg.create_pool(min_size=2, max_size=10, max_inactive_connection_lifetime=120.0, database=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        log.debug('Database connection pool initilized')
        # self.player_by_id = self.dbconn.prepare("""SELECT * FROM players WHERE steamid = '$1'""")

    async def close(self):
        if self.cpool is not None:
            await self.cpool.close()
        log.debug('Database connections closed')

    async def check_if_connected(self):
        if self.cpool is None:
            log.trace('Database is not connected. connecting...')
            await self._connect()

    async def _aquire(self):
        try:
            con = await self.cpool.acquire()
        except:
            log.error('Error aquiring db pool connection')
        else:
            return con

    async def _release(self, connection):
        try:
            await self.cpool.release(connection)
        except:
            log.error('Error releasing db pool connection')
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
        await self.check_if_connected()
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

    async def _execute(self, query):
        con = await self._acquire()
        try:
            await con.execute(query)
        except:
            log.exception(f'Exception in db update {query}')
        finally:
            await self._release(con)

    async def update(self, query, db='pyark'):
        if db not in self.databases:
            raise ValueError(f'Invalid database [{db}]')
        # if (db not in self.dbgamelog and not isinstance(query, str)) or (db in self.dbgamelog and not isinstance(query, list)):
        #    raise TypeError(f'Query type is invalid [{type(query)}]')
        await self.check_if_connected()
        if db in self.dbpyark:
            await asyncio.create_task(self._execute(query))
        elif db in self.dbstats:
            await asyncio.create_task(self._execute(query))
        elif db in self.dbgamelog:
            sql = "INSERT INTO gamelog (instance, loglevel, logline) VALUES ($1, $2, $3)"
            await asyncio.create_task(self._execute(sql, query[0].lower(), query[1].upper(), query[2]))
        # log.trace(f'Executing DB [{db}] update {query}')
        return True
