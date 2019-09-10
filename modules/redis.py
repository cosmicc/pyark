import asyncio

import aredis
from loguru import logger as log


class RedisClass:

    def __init__(self, host='172.31.250.115', port=16379, db=0, max_idle_time=5, idle_check_interval=.1):
        self.db = db
        self.max_idle_time = 3
        self.idle_check_interval = 0.1
        self.host = host
        self.port = port
        self.verified = False
        self.pool = aredis.ConnectionPool(host='172.31.250.115', port=port, db=db, max_idle_time=max_idle_time, idle_check_interval=idle_check_interval)
        self.redis = aredis.StrictRedis(connection_pool=self.pool)

    async def connect(self, hostname):
        while len(self.pool._available_connections) == 0 or not self.verified:
            self.hostname = hostname
            try:
                await self.redis.ping()
            except:
                self.verified = False
                log.debug('Failed verifying connection to Redis server, retrying...')
                await self.connect(hostname)

            else:
                self.verified = True
                log.debug(f'Connection established to Redis server for [{self.hostname}]')

    async def wakeup(self):
        while len(self.pool._available_connections) == 0 or not self.verified:
            try:
                await self.redis.ping()
            except:
                self.verified = False
                log.debug('Failed verifying connection to Redis server, retrying...')
                await self.connect(self.hostname)
            else:
                self.verified = True


Redis = RedisClass()
