import asyncio

import asyncpg
from loguru import logger as log
from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_statsdb, psql_user


class asyncDB:
    def __init__(self):
        log.debug('Starting async db engine')
        self.querytypes = ['tuple', 'dict', 'count', 'list']
        self.databases = ['pyark', 'py', 'stats', 'st', 'gamelog', 'gl']
        self.dbpyark = ['pyark', 'py']
        self.dbstats = ['stats', 'st']
        self.dbgamelog = ['gamelog', 'gl']

    async def _connect(self, db):
        if db not in self.databases:
            raise SyntaxError
        self.dbeventloop = asyncio.get_running_loop()
        if db in self.dbpyark:
            self.pydbconn = await asyncpg.connect(database=psql_db, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
            log.debug('Connection established to pyarkdb')
        elif db in self.dbstats:
            self.stdbconn = await asyncpg.connect(database=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
            log.debug('Connection established to statsdb')
        elif db in self.dbgamelog:
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

    async def check_if_connected(self, db):
        if db in self.dbpyark:
            if 'self.pydbconn' not in locals():
                await self._connect('pyark')
        elif db in self.dbstats:
            if 'self.stdbconn' not in locals():
                await self._connect('stats')
        elif db in self.glgamelog:
            if 'self.gldbconn' not in locals():
                await self._connect('gamelog')

    async def query(self, query, fmt, fetch, single=True, db='pyark'):
        if not isinstance(query, str):
            raise TypeError('Query is not type string')
        if db not in self.databases:
            raise ValueError('Invalid database')
        if fmt not in self.querytypes:
            raise ValueError('Invalid fmt type')
        if fetch != 'one' and fetch != 'all':
            raise ValueError('Invalid fetch type')
        await self.check_if_connected(db)
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
        if db not in self.databases:
            raise ValueError('Invalid database')
        if (db != 'gamelog' or db != 'gl' and not isinstance(query, str)) or (db == 'gamelog' or db == 'gl' and not isinstance(query, list)):
            raise TypeError('Query type is invalid')
        await self.check_if_connected(db)
        try:
            if 'self.pydbconn' not in locals():
                await self._connect('pyark')
            if 'self.stdbconn' not in locals():
                await self._connect('stats')
            if 'self.gldbconn' not in locals():
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
