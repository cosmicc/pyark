import subprocess
from psutil import Process
from loguru import logger as log
from re import sub
from os.path import isfile
import asyncio
from shlex import quote


@log.catch
async def asyncserverexec(cmdlist, nice=19):
    fullcmdlist = ['/usr/bin/nice', '-n', str(nice)] + cmdlist
    cmdstring = quote(' '.join(fullcmdlist))
    log.debug(f'server rcon cmd executing {cmdstring}')
    proc = await asyncio.create_subprocess_shell(cmdstring)
    await proc.wait()
    log.debug(f'server rcon process completed {cmdlist}')


@log.catch
def rconexecuterloop():
    global arconloop
    log.debug(f'starting the rcon executer thread')
    arconloop = asyncio.new_event_loop()
    arconloop.run_forever()


def removerichtext(text):
    return sub('<.*?>', '', text)


@log.catch
def serverneedsrestart():
    if isfile('/run/reboot-required'):
        return True
    else:
        return False


@log.catch
def getinstpid(inst):
    pidfile = f'/home/ark/ARK/ShooterGame/Saved/.arkserver-{inst}.pid'
    file = open(pidfile, 'r')
    arkpid = file.read()
    file.close()
    return int(arkpid)


@log.catch
def setarknice(inst):
    proc = Process(getinstpid(inst))
    if proc.nice() != -10:
        log.debug(f'Setting priority for ark server instance [{inst}]')
        proc.nice(-10)


@log.catch
def serverexec(cmdlist, nice=10, null=False):
    if type(cmdlist) is not list:
        raise TypeError
    else:
        fullcmdlist = ['/usr/bin/nice', '-n', str(nice)] + cmdlist
    if null:
        sproc = subprocess.run(fullcmdlist, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
        return sproc.returncode
    else:
        sproc = subprocess.run(fullcmdlist, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        return sproc
