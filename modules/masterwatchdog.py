from ping3 import ping
from modules.redis import redis
from typing import Optional
from loguru import logger as log


async def pinghost(host: str) -> Optional[float]:
    return ping(host, unit='ms', timeout=2)


async def checkhosts():
    instances = await redis.smembers('allhostips')
    for instance in iter(instances):
        resp = pinghost(instance.decode())
        if resp:
            if resp > 5:
                log.warning('High internal ping times to [{instance.decode()}]')
        else:
            log.warning('No reponse from host [{instance.decode()}]')
