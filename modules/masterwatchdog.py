from ping3 import ping
from modules.redis import redis
from typing import Optional


async def pinghost(host: str) -> Optional[float]:
    return ping(host, unit='ms', timeout=2)


async def checkhosts(instance):
    instances = await redis.smembers('allhostips')
    for instance in iter(instances):
        print(instance)
