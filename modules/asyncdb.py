import asyncio

import asyncpg
from loguru import logger as log
from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_statsdb, psql_user


class asyncDB:
    def __init__(self):
        log.trace('Starting async db engine')
        self.querytypes = ['tuple', 'dict', 'count', 'list']
        self.databases = ['pyark', 'py', 'stats', 'st', 'gamelog', 'gl']

    async def _connect(self, db):
        if db not in self.databases:
            raise SyntaxError
        self.dbeventloop = asyncio.get_running_loop()
        if db == 'py' or db == 'pyark':
            self.pydbconn = await asyncpg.connect(database=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
            log.debug('Connection established to pyarkdb')
        elif db == 'st' or db == 'stats':
            self.stdbconn = await asyncpg.connect(database=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
            log.debug('Connection established to statsdb')
        elif db == 'gl' or db == 'gamelog':
            self.gldbconn = await asyncpg.connect(database='gamelog', user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
            log.debug('Connection established to gamelogdb')

    async def close(self):
        if 'self.pydbconn' in locals():
            await self.pydbconn.close()
        if 'self.gldbconn' in locals():
            await self.gldbconn.close()
        if 'self.stbconn' in locals():
            await self.stdbconn.close()
        log.debug('Database connections closed')

    async def query(self, query, fmt, fetch, single=True, db='pyark'):
        if fetch != 'one' or fetch != 'all' or fmt not in self.querytypes or db not in self.databases or not isinstance(query, str):
            raise SyntaxError
        if 'self.pydbconn' in locals():
            await self._connect('pyark')
        if 'self.stdbconn' in locals():
            await self._connect('stats')
        if 'self.gldbconn' in locals():
            await self._connect('gamelog')
        try:
            if fetch == 'one':
                dbdata = await self.pydbconn.fetchrow(query)
            elif fetch == 'all' or fmt == "count":
                dbdata = await self.pydbconn.fetch(query)
        except:
            log.exception(f'Error in database query {query} in {db}')
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
        else:
            return None

    async def update(self, query, db='pyark'):
        if db not in self.databases or (db != 'gamelog' or db != 'gl' and not isinstance(query, str)) or (db == 'gamelog' or db == 'gl' and not isinstance(query, list)):
            raise SyntaxError
        try:
            if 'self.pydbconn' in locals():
                await self._connect('pyark')
            if 'self.stdbconn' in locals():
                await self._connect('stats')
            if 'self.gldbconn' in locals():
                await self._connect('gamelog')
            if db == 'py' or db == 'pyark':
                await asyncio.create_task(self.pydbconn.execute(query))
            elif db == 'st' or db == 'stats':
                await asyncio.create_task(self.pydbconn.execute(query))
            elif db == 'gl' or db == 'gamelog':
                sql = "INSERT INTO gamelog (instance, loglevel, logline) VALUES ($1, $2, $3)"
                await asyncio.create_task(self.gldbconn.execute(sql, query[0].lower(), query[1].upper(), query[2]))
        except:
            log.exception(f'Exception in db update {query} in {db}')
            return False
        else:
            return True
