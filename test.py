
import asyncio
import signal
import threading
import time
from sys import exit

import uvloop
from loguru import logger as log
from modules.asyncdb import asyncDB


def sig_handler(signal, frame):
    log.info(f'Termination signal {signal} recieved. Exiting.')
    stop_event.set()
    print(threads)
    for thread in threads:
        thread.join
    exit(0)


signal.signal(signal.SIGTERM, sig_handler)
signal.signal(signal.SIGHUP, sig_handler)
signal.signal(signal.SIGINT, sig_handler)
signal.signal(signal.SIGQUIT, sig_handler)


async def unmore(db, line):
    return await db.pyquery(line, 'dict', 'one')


async def looper(db):
    await db.pyconnect()
    try:
        log.info('looping')
        result = await unmore(db, 'SELECT * from instances')
        print(result)
        await asyncio.sleep(5)
    except:
        log.exception(f'Exception in checkcommands loop')
        await asyncio.sleep(30)


def threadloop(stop_event):
    db = asyncDB()
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    while not stop_event.is_set():
        asyncio.run(looper(db))
    log.debug(f'Shutting down thread')
    asyncio.run(db.close())


def main():
    global stop_event
    global threads
    threads = []
    stop_event = threading.Event()
    t = threading.Thread(target=threadloop, args=(stop_event,))
    threads.append(t)
    t.start()
    while True:
        time.sleep(5)


main()
