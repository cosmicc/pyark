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


class globalvar:
    def __init__():
        pass

    async def set(key, value):
        """Set a global variable

        Arguments:
            key {string} -- Key to set value to
            value {int, string} -- Value to set to key
        """
        await redis.set(key, value)

    async def remove(key):
        """Remove a global variable

        Arguments:
            key {string} -- Key to remove
        """
        await redis.delete(key)

    async def getstring(key):
        """Get a global variable as a string

        Arguments:
            key {string} -- Key to get value from
        """
        return (await redis.get(key)).decode()

    async def getint(key):
        """Get a global variable as int

        Arguments:
            key {string} -- Key to get value from
        """
        return int((await redis.get(key)).decode())

    async def getfloat(key):
        """Get a global variable as float

        Arguments:
            key {string} -- Key to get value from
        """
        return float((await redis.get(key)).decode())

    async def getbool(key):
        """Get a global variable as bool

        Arguments:
            key {string} -- Key to get value from
        """
        return bool((await redis.get(key)).decode())

    async def getlist(key):
        """Get a global variable as list

        Arguments:
            key {string} -- Key to get value from
        """
        reclist = await redis.smembers(key)
        resplist = []
        for inst in reclist:
            resplist.append(inst.decode())
        return resplist

    async def gettuple(key):
        """Get a global variable as tuple

        Arguments:
            key {string} -- Key to get value from
        """
        reclist = await redis.smembers(key)
        resplist = ()
        for inst in reclist:
            resplist = resplist + (inst.decode(),)
        return resplist

    async def checklist(key, value):
        """Check a global list for a value

        Arguments:
            key {string} -- Key to get value from
            value {string} -- Value to check in list
        """
        return await redis.sismember(key, value)

    async def addlist(key, value):
        """Add a value to a global list

        Arguments:
            key {string} -- Key to add value
            value {string} -- Value to add to list
        """
        return await redis.sadd(key, value)

    async def remlist(key, value):
        """Remove a value from a global list

        Arguments:
            key {string} -- Key to remove value
            value {string} -- Value to remove from list
        """
        return await redis.srem(key, value)

    async def inc(instance, key):
        """Increment a global variable

        Arguments:
            key {string} -- Key to increment value
        """
        await redis.incr(key)

    async def dec(instance, key):
        """Decrement a global variable

        Arguments:
            key {string} -- Key to decrement value
        """
        await redis.decr(key)


class instancevar:
    def __init__():
        pass

    async def set(instance, key, value):
        """Set an instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to set value to
            value {int, string} -- Value to set to key
        """
        await redis.hset(f'{instance}', key, value)

    async def mset(instance, kvdict):
        """Set multiple instance variable

        Arguments:
            instance {string} -- Instance Name
            kvdict {dict} -- Dict of key/values to set
        """
        await redis.hmset(f'{instance}', kvdict)

    async def remove(instance, key):
        """Remove an instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to remove
        """
        await redis.hdel(f'{instance}', key)

    async def getstring(instance, key):
        """Get an instance variable as string

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to get value from
        """
        return (await redis.hget(f'{instance}', key)).decode()

    async def getint(instance, key):
        """Get an instance variable as int

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to get value from
        """
        return int((await redis.hget(f'{instance}', key)).decode())

    async def getbool(instance, key):
        """Get an instance variable as bool

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to get value from
        """
        return bool((await redis.hget(f'{instance}', key)).decode())

    async def getfloat(instance, key):
        """Get an instance variable as float

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to get value from
        """
        return float((await redis.hget(f'{instance}', key)).decode())

    async def getall(instance):
        """Get all instance variables

        Arguments:
            instance {string} -- Instance Name
        """
        return (await redis.hgetall(f'{instance}'))

    async def inc(instance, key):
        """Increment instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to increment value
        """
        await redis.hincrby(f'{instance}', key, 1)

    async def dec(instance, key):
        """Decrement instance variable

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to decrement value
        """
        await redis.hincrby(f'{instance}', key, -1)

    async def check(instance, key):
        """Check if instance variable exists

        Arguments:
            instance {string} -- Instance Name
            key {string} -- Key to check
        """
        return await redis.hexists(f'{instance}', key)


class instancestate:
    def __init__():
        pass

    async def set(instance, *args):
        """Set an instance state

        Arguments:
            instance {string} -- Instance name
            *args {string} -- Instance state(s) to set
        """
        await redis.sadd(f'{instance}-states', *args)

    async def unset(instance, *args):
        """Unset an instance state

        Arguments:
            instance {string} -- Instance name
            *args {string} -- Instance state(s) to unset
        """
        await redis.srem(f'{instance}-states', *args)

    async def check(instance, state):
        """Check an instance state

        Arguments:
            instance {string} -- Instance name
            state {string} -- Instance state
        """
        return await redis.sismember(f'{instance}-states', state)

    async def getlist(instance):
        """List of instance states

        Arguments:
            instance {string} -- Instance name
        """
        return await redis.smembers(f'{instance}-states')

