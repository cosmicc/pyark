import asyncio

import aredis
from loguru import logger as log

from modules.configreader import redis_db, redis_host, redis_port


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
redis = Redis.redis


class instancevar:
    def __init__(self):
        pass

    async def set(self, instance, key, value):
        """Set an instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to set value to
            value {int, string} -- Value to set to key
        """
        await redis.hset(f'{instance}', key, value)

    async def remove(self, instance, key):
        """Remove an instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to remove
        """
        await redis.hdel(f'{instance}', key)

    async def get(self, instance, key):
        """Get an instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to get value from
        """
        return await redis.hget(f'{instance}', key)

    async def inc(self, instance, key):
        """Increment instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to increment value
        """
        return await redis.hincrby(f'{instance}', key, 1)

    async def dec(self, instance, key):
        """Decrement instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to decrement value
        """
        return await redis.hincrby(f'{instance}', key, -1)

    async def check(self, instance, key):
        """Check if instance variable exists

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to check
        """
        return await redis.hexists(f'{instance}', key)


class instancestate:
    def __init__(self):
        pass

    async def set(self, instance, state):
        """Set an instance state

        Arguments:
            instance {string} -- Instance name
            state {string} -- Instance state
        """
        await redis.sadd(f'{instance}-states', state)

    async def unset(self, instance, state):
        """Unset an instance state

        Arguments:
            instance {string} -- Instance name
            state {string} -- Instance state
        """
        await redis.srem(f'{instance}-states', state)

    async def check(self, instance, state):
        """Check an instance state

        Arguments:
            instance {string} -- Instance name
            state {string} -- Instance state
        """
        return redis.sismember(f'{instance}-states', state)
