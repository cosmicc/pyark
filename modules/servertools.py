import subprocess
from psutil import Process
from loguru import logger as log
from re import sub
from os.path import isfile
import asyncio


@log.catch
async def asyncserverchat(inst, message, nice=15):
    asyncloop = asyncio.get_running_loop()
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "ServerChat {message}" @{inst}'
    log.debug(f'cmd: {cmdstring}')
    proc = asyncio.create_subprocess_shell(cmdstring, loop=asyncloop)
    asyncio.create_task(proc)
    return True


@log.catch
async def asyncserverchatto(inst, steamid, message, nice=15):
    asyncloop = asyncio.get_running_loop()
    cmdstring = f"""/usr/bin/nice -n {nice} arkmanager rconcmd 'ServerChatTo "{steamid}" {message}' @{inst}"""
    proc = asyncio.create_subprocess_shell(cmdstring, loop=asyncloop)
    asyncio.create_task(proc)
    return True


@log.catch
async def asyncserverbcast(inst, message, nice=10):
    asyncloop = asyncio.get_running_loop()
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "ServerBroadcast {message}" @{inst}'
    proc = asyncio.create_subprocess_shell(cmdstring, loop=asyncloop)
    asyncio.create_task(proc)
    return True


@log.catch
async def asyncserverexec(cmdlist, nice):
    asyncloop = asyncio.get_running_loop()
    fullcmdlist = ['/usr/bin/nice', '-n', str(nice)] + cmdlist
    cmdstring = ' '.join(fullcmdlist)
    # cmdstring = quote(' '.join(fullcmdlist)).strip("'")
    log.debug(f'server rcon cmd executing [{cmdstring}]')
    proc = asyncio.create_subprocess_shell(cmdstring, loop=asyncloop)
    await asyncio.wait_for(proc, timeout=10, loop=asyncloop)
    log.debug(f'server rcon process completed [{cmdstring}]')
    return 0


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
