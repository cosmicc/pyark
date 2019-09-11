import asyncio
import logging
import signal
import time
import warnings

import uvloop
from loguru import logger as log

from modules.redis import Redis

redis = Redis.redis
main_stop_event = False

logging.basicConfig(level=logging.DEBUG)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logging.getLogger('').addHandler(console)


def async_exception_handler(loop, context):
    exception = context.get('exception')
    message = context.get('message')
    try:
        raise exception
    except:
        log.exception(message)
    # if isinstance(exception, ZeroDivisionError):
    #    pass


def signal_handler(signal, frame):
    global main_stop_event
    log.info(f'Termination signal [{signal}] recieved. Exiting.')
    main_stop_event = True


signal.signal(signal.SIGTERM, signal_handler)  # Graceful Shutdown
signal.signal(signal.SIGHUP, signal_handler)  # Reload/Restart
signal.signal(signal.SIGINT, signal_handler)  # Hard Exit
signal.signal(signal.SIGQUIT, signal_handler)  # Hard Exit

progresssymbol = ('|', '/', '-', '\\')
progressposition = 0


async def progressbar():
    global progressposition
    print(f'\033[1D{progresssymbol[progressposition]}', end='', flush=True)
    progressposition += 1
    if progressposition == 4:
        progressposition = 0


async def checkforrediscommands(pubsub):
    response = await pubsub.get_message(timeout=0.01)
    if response is not None:
        if response['type'] == 'message':
            log.info(f'Recieved Command: {response["data"].decode()}')
            if response['data'].decode() == 'update':
                await 


async def asyncmain():
    asyncloop = asyncio.get_running_loop()
    asyncloop.set_exception_handler(async_exception_handler)
    await Redis.connect(__name__)
    inst = 'ragnarok'
    pubsub = redis.pubsub()
    await pubsub.subscribe([f'{inst}-commands'])
    while not main_stop_event:
        await checkforrediscommands(pubsub)
        await progressbar()
        await asyncio.sleep(.05)
    #redispool.make_connection()
    '''
    await redis.hset(inst, 'isrunning', 1)
    val = await redis.hget(inst, 'isrunning')
    while not main_stop_event:
    print(redispool._available_connections)
        print(redispool._in_use_connections)
        print(val)
        conn = redispool._available_connections[0]
        print(conn.last_active_at)
        await asyncio.sleep(3)
        print(conn.last_active_at)
        print(time.time() - conn.last_active_at)
        # we can see that the idle connection is removed from available conn list
        print(redispool._available_connections)
        print(redispool._in_use_connections)
        #await progressbar()
        await asyncio.sleep(3)
    '''    
    pubsub.close()
    await Redis.disconnect()
    print(asyncio.all_tasks())
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    log.debug(f'Waiting for {len(tasks)} async tasks to finish')
    await asyncio.gather(*tasks, return_exceptions=True)
    log.debug('All async tasks have finished')


def main():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    warnings.simplefilter('always', ResourceWarning)
    asyncio.run(asyncmain(), debug=True)  # Async branch to main loop


main()