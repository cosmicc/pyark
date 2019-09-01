import asyncio

import asyncpg
from loguru import logger as log
from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_statsdb, psql_user


class asyncDB:
    def __init__(self):
        log.trace('Starting async db connection engine')
        self.loop = asyncio.get_running_loop()
        self.querytypes = ('tuple', 'dict', 'count', 'list', 'record')
        self.databases = ('pyark', 'py', 'stats', 'st', 'gamelog', 'gl')
        self.dbpyark = ('pyark', 'py')
        self.dbstats = ('stats', 'st')
        self.dbgamelog = ('gamelog', 'gl')
        self.dbconn = None

    async def _connect(self, db):
        if db not in self.databases:
            raise SyntaxError
        self.dbeventloop = asyncio.get_running_loop()
        if db in self.dbpyark:
            self.dbconn = await asyncpg.connect(database=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
            log.debug('Connection established to database')
            self.player_by_id = self.pydbconn.prepare("""SELECT * FROM players WHERE steamid = '$1'""")

    async def close(self):
        if self.dbconn is not None:
            await self.dbconn.close()
        log.debug('Database connections closed')

    async def check_if_connected(self, db):
        if db in self.dbpyark:
            if self.dbconn is None:
                await self._connect('pyark')

    # async def query(self, query, fmt='one', fetch='record', db='pyark'):
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
        await self.check_if_connected(db)
        try:
            if fetch == 'one':
                dbdata = await self.dbconn.fetchrow(query)
                log.debug(f'Executing DB [{db}] query {query}')
            elif fetch == 'all' or fmt == "count":
                dbdata = await self.dbconn.fetch(query)
                log.debug(f'Executing DB [{db}] query {query}')
        except:
            log.exception(f'Error in database query {query} in {db}')
            return None
        if dbdata is not None:
            log.debug(f'Retrieved DB [{db}] result {dbdata}')
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

    async def update(self, query, db='pyark'):
        if db not in self.databases:
            raise ValueError(f'Invalid database [{db}]')
        #if (db not in self.dbgamelog and not isinstance(query, str)) or (db in self.dbgamelog and not isinstance(query, list)):
        #    raise TypeError(f'Query type is invalid [{type(query)}]')
        await self.check_if_connected(db)
        try:
            if db in self.dbpyark:
                log.debug
                await asyncio.create_task(self.dbconn.execute(query))
                log.debug(f'Executing DB [{db}] update {query}')
            elif db in self.dbstats:
                await asyncio.create_task(self.dbconn.execute(query))
                log.debug(f'Executing DB [{db}] update {query}')
            elif db in self.dbgamelog:
                sql = "INSERT INTO gamelog (instance, loglevel, logline) VALUES ($1, $2, $3)"
                await asyncio.create_task(self.dbconn.execute(sql, query[0].lower(), query[1].upper(), query[2]))
                log.debug(f'Executing DB [{db}] update {query}')
        except:
            log.exception(f'Exception in db update {query} in {db}')
            return False
        else:
            return True
