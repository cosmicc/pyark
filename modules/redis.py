import asyncio

import aredis
from loguru import logger as log

from modules.configreader import redis_db, redis_host, redis_port


class RedisClass:
    def __init__(self, host: str =redis_host, port: int=redis_port, db: str=redis_db, max_idle_time: int=30, idle_check_interval: float=.1):
        self.db = db
        self.max_idle_time: int = max_idle_time
        self.idle_check_interval: float = idle_check_interval
        self.host: str = host
        self.port: int = port
        self.verified: bool = False
        self.pool = aredis.ConnectionPool(host=self.host, port=self.port, db=self.db)
        self.redis = aredis.StrictRedis(connection_pool=self.pool)

    async def connect(self, hostname: str):
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


class globalvar():
    @staticmethod
    async def set(key, value: str):
        """Set a global variable

        Arguments:
            key {string} -- Key to set value to
            value {int, string} -- Value to set to key
        """
        await redis.set(key, value)

    @staticmethod
    async def remove(key: str):
        """Remove a global variable

        Arguments:
            key {string} -- Key to remove
        """
        await redis.delete(key)

    @staticmethod
    async def getstring(key: str) -> str:
        """Get a global variable as a string

        Arguments:
            key {string} -- Key to get value from
        """
        return (await redis.get(key)).decode()

    @staticmethod
    async def getint(key: str) -> int:
        """Get a global variable as int

        Arguments:
            key {string} -- Key to get value from
        """
        return int((await redis.get(key)).decode())

    @staticmethod
    async def getfloat(key: str) -> float:
        """Get a global variable as float

        Arguments:
            key {string} -- Key to get value from
        """
        return float((await redis.get(key)).decode())

    @staticmethod
    async def getbool(key: str) -> bool:
        """Get a global variable as bool

        Arguments:
            key {string} -- Key to get value from
        """
        return bool((await redis.get(key)).decode())

    @staticmethod
    async def getlist(key: str) -> list:
        """Get a global variable as list

        Arguments:
            key {string} -- Key to get value from
        """
        reclist = await redis.smembers(key)
        resplist = []
        for inst in reclist:
            resplist.append(inst.decode())
        return resplist

    @staticmethod
    async def gettuple(key: str) -> tuple:
        """Get a global variable as tuple

        Arguments:
            key {string} -- Key to get value from
        """
        reclist = await redis.smembers(key)
        resplist = ()
        for inst in reclist:
            resplist = resplist + (inst.decode(),)
        return resplist

    @staticmethod
    async def checklist(key: str, value: str) -> bool:
        """Check a global list for a value

        Arguments:
            key {string} -- Key to get value from
            value {string} -- Value to check in list
        """
        return await redis.sismember(key, value)

    @staticmethod
    async def addlist(key: str, value: str) -> int:
        """Add a value to a global list

        Arguments:
            key {string} -- Key to add value
            value {string} -- Value to add to list
        """
        return await redis.sadd(key, value)

    @staticmethod
    async def remlist(key: str, value: str) -> int:
        """Remove a value from a global list

        Arguments:
            key {string} -- Key to remove value
            value {string} -- Value to remove from list
        """
        return await redis.srem(key, value)

    @staticmethod
    async def inc(instance: str, key: str):
        """Increment a global variable

        Arguments:
            key {string} -- Key to increment value
        """
        await redis.incr(key)

    @staticmethod
    async def dec(instance: str, key: str):
        """Decrement a global variable

        Arguments:
            key {string} -- Key to decrement value
        """
        await redis.decr(key)


class instancevar:
    @staticmethod
    async def set(instance: str, key: str, value: str):
        """Set an instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to set value to
            value {int, string} -- Value to set to key
        """
        await redis.hset(f'{instance}', key, value)

    @staticmethod
    async def mset(instance: str, kvdict: dict):
        """Set multiple instance variable

        Arguments:
            instance {string} -- Instance Name
            kvdict {dict} -- Dict of key/values to set
        """
        await redis.hmset(f'{instance}', kvdict)

    @staticmethod
    async def remove(instance: str, key: str):
        """Remove an instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to remove
        """
        await redis.hdel(f'{instance}', key)

    @staticmethod
    async def getstring(instance: str, key: str) -> str:
        """Get an instance variable as string

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to get value from
        """
        return (await redis.hget(f'{instance}', key)).decode()

    @staticmethod
    async def getint(instance: str, key: str) -> int:
        """Get an instance variable as int

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to get value from
        """
        return int((await redis.hget(f'{instance}', key)).decode())

    @staticmethod
    async def getbool(instance: str, key: str) -> bool:
        """Get an instance variable as bool

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to get value from
        """
        return bool((await redis.hget(f'{instance}', key)).decode())

    @staticmethod
    async def getfloat(instance: str, key: str) -> float:
        """Get an instance variable as float

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to get value from
        """
        return float((await redis.hget(f'{instance}', key)).decode())

    @staticmethod
    async def getall(instance: str) -> dict:
        """Get all instance variables

        Arguments:
            instance {string} -- Instance Name
        """
        return (await redis.hgetall(f'{instance}'))

    @staticmethod
    async def inc(instance: str, key: str):
        """Increment instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to increment value
        """
        await redis.hincrby(f'{instance}', key, 1)

    @staticmethod
    async def dec(instance: str, key: str):
        """Decrement instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to decrement value
        """
        await redis.hincrby(f'{instance}', key, -1)

    @staticmethod
    async def check(instance: str, key: str) -> bool:
        """Check if instance variable exists

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to check
        """
        return await redis.hexists(f'{instance}', key)


class instancestate:
    @staticmethod
    async def set(instance: str, *args: str):
        """Set an instance state

        Arguments:
            instance {string} -- Instance name
            *args {string} -- Instance state(s) to set
        """
        await redis.sadd(f'{instance}-states', *args)

    @staticmethod
    async def unset(instance: str, *args: str):
        """Unset an instance state

        Arguments:
            instance {string} -- Instance name
            *args {string} -- Instance state(s) to unset
        """
        await redis.srem(f'{instance}-states', *args)

    @staticmethod
    async def check(instance: str, state) -> bool:
        """Check an instance state

        Arguments:
            instance {string} -- Instance name
            state {string} -- Instance state
        """
        return await redis.sismember(f'{instance}-states', state)

    @staticmethod
    async def getlist(instance: str) -> list:
        """List of instance states

        Arguments:
            instance {string} -- Instance name
        """
        return await redis.smembers(f'{instance}-states')

