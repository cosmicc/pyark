from ping3 import ping
from modules.redis import redis
from typing import Optional
from loguru import logger as log
from modules.timehelper import truncate_float


async def pinghost(host: str) -> Optional[float]:
    return ping(host, unit='ms', timeout=2)


async def checkhosts():
    instances = await redis.smembers('allhostips')
    for instance in iter(instances):
        resp = pinghost(instance.decode())
        if resp:
            log.debug(f'Ping response from {instance.decode()}: {truncate_float(resp, 2)}ms')
            if resp > 5:
                log.warning(f'High internal ping times to [{instance.decode()}]')
        else:
            log.warning(f'No reponse from host [{instance.decode()}]')
