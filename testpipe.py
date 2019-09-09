import asyncio
import uvloop
import signal
import warnings
import logging
from modules.callbackclasses import DFProtocol
from functools import partial

from loguru import logger as log

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


async def runcmd(*args):
    asyncloop = asyncio.get_running_loop()
    cmd_done = asyncio.Future(loop=asyncloop)
    factory = partial(DFProtocol, cmd_done)
    proc = asyncloop.subprocess_exec(factory, *args, stdin=None, stderr=None)
    try:
        log.info('launching process')
        transport, protocol = await proc
        log.info('waiting for process to complete')
        await cmd_done
    finally:
        transport.close()
    log.success(cmd_done.result())


async def asyncmain():
    asyncloop = asyncio.get_running_loop()
    asyncloop.set_exception_handler(async_exception_handler)
    # while not main_stop_event:
    asyncio.create_task(runcmd('arkmanager', 'status', '@ragnarok'))
    #await asyncio.sleep(2)
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    log.debug(f'Waiting for {len(tasks)} async tasks to finish')
    await asyncio.gather(*tasks, return_exceptions=True)
    log.debug('All async tasks have finished')


def main():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    warnings.simplefilter('always', ResourceWarning)
    asyncio.run(asyncmain(), debug=True)  # Async branch to main loop


main()
