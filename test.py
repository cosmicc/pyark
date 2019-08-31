
import asyncio
from loguru import logger as log
import uvloop
from modules.servertools import serverexec


async def asyncprint(line):
    log.success(line)


async def looper():
    while True:
        log.info('looping')
        try:
            cmdpipe = serverexec(['arkmanager', 'rconcmd', 'listplayers', f'@coliseum'], nice=5, null=False)
            b = cmdpipe.stdout.decode("utf-8")
            for line in iter(b.splitlines()):
                asyncio.create_task(asyncprint(line))
            await asyncio.sleep(5)
        except:
            log.exception(f'Exception in checkcommands loop')


def main():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(looper())


main()
