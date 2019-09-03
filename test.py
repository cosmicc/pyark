import asyncio

import uvloop
from loguru import logger as log

from modules.asyncdb import DB as db


@log.catch
async def gettotaldbconnections():
    result = await db.fetchone(f'SELECT count(*) FROM pg_stat_activity;')
    return int(result['count'])


async def looper():
    while True:
        connections = await gettotaldbconnections()
        print(connections)
        await asyncio.sleep(30)


def loop():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(looper())
    log.debug(f'Shutting down thread')
    asyncio.run(db.close())


loop()
