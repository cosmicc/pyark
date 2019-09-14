import asyncio
import logging
import signal
import time
import warnings

import uvloop
from loguru import logger as log

from modules.redis import instancestate, instancevar, Redis

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
                pass


async def asyncmain():
    asyncloop = asyncio.get_running_loop()
    asyncloop.set_exception_handler(async_exception_handler)
    inst = 'ragnarok'

    print(await redis.smembers('ragnarok-leaving'))

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    log.debug(f'Waiting for {len(tasks)} async tasks to finish')
    await asyncio.gather(*tasks, return_exceptions=True)
    log.debug('All async tasks have finished')


def main():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    warnings.simplefilter('always', ResourceWarning)
    asyncio.run(asyncmain(), debug=True)  # Async branch to main loop


main()
