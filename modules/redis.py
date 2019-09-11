import asyncio

import aredis
from loguru import logger as log

from configreader import redis_db, redis_host, redis_port


class RedisClass:

    def __init__(self, host=redis_host, port=redis_port, db=redis_db, max_idle_time=30, idle_check_interval=.1):
        self.db = db
        self.max_idle_time = max_idle_time
        self.idle_check_interval = idle_check_interval
        self.host = host
        self.port = port
        self.verified = False
        self.pool = aredis.ConnectionPool(host=self.host, port=self.port, db=self.db)
        self.redis = aredis.StrictRedis(connection_pool=self.pool)

    async def connect(self, hostname):
        while len(self.pool._available_connections) == 0 or not self.verified:
            self.hostname = hostname
            try:
                await self.redis.ping()
            except:
                self.verified = False
                log.warning('Failed verifying connection to Redis server, retrying...')
                await asyncio.sleep(10)
                await self.connect(hostname)

            else:
                self.verified = True
                log.debug(f'Connection verified to Redis server for [{self.hostname}]')

    async def wakeup(self):
        while len(self.pool._available_connections) == 0 or not self.verified:
            try:
                await self.redis.ping()
            except:
                self.verified = False
                log.warning('Failed verifying connection to Redis server, retrying...')
                await self.connect(self.hostname)
            else:
                self.verified = True

    async def disconnect(self):
        self.verified = False
        self.pool.disconnect()


Redis = RedisClass()
