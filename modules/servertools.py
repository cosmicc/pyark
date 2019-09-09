import asyncio
import subprocess
from os.path import isfile
from re import sub
from time import time

from loguru import logger as log
from psutil import Process

from modules.asyncdb import DB as db


def asynctimeit(func):
    async def wrapper(*args, **kwargs):
        asyncloop = asyncio.get_running_loop()
        astart_time = asyncloop.time()
        await func(*args, **kwargs)
        print(f'Execution times for [{func.__name__}]: Async: {asyncloop.time() - astart_time}')
    return wrapper


@log.catch
async def gettotaldbconnections():
    return await db.fetchone(f'SELECT count(*) FROM pg_stat_activity;')


@log.catch
async def asyncserverrconcmd(inst, command, nice=5):
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "{command}" @{inst}'
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    log.debug(f'cmd: {cmdstring}')
    asyncio.create_task(proc)
    return True


@log.catch
async def asyncserverscriptcmd(inst, command, nice=5):
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "ScriptCommand {command}" @{inst}'
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f'cmd: {cmdstring}')
    return True


@log.catch
async def asyncserverchat(inst, message, nice=15):
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "ServerChat {message}" @{inst}'
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f'cmd: {cmdstring}')
    return True


@log.catch
async def asyncserverchatto(inst, steamid, message, nice=15):
    cmdstring = f"""/usr/bin/nice -n {nice} arkmanager rconcmd 'ServerChatTo "{steamid}" {message}' @{inst}"""
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f'cmd: {cmdstring}')
    return True


@log.catch
async def asyncserverbcast(inst, bcast, nice=10):
    cmdstring = f"""/usr/bin/nice -n {nice} arkmanager rconcmd 'Broadcast {bcast}' @{inst}"""
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f"""cmd: {repr(cmdstring)}""")
    return True


@log.catch
async def asyncservernotify(inst, message, nice=10):
    cmdstring = f"""/usr/bin/nice -n {nice} arkmanager notify "{message}" @{inst}"""
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f"""cmd: {repr(cmdstring)}""")
    return True


@log.catch
async def asyncserverexec(cmdlist, nice=19, wait=False):
    fullcmdlist = ['/usr/bin/nice', '-n', str(nice)] + cmdlist
    cmdstring = ' '.join(fullcmdlist)
    if wait:
        proc = await asyncio.create_subprocess_shell(cmdstring, stdout=asyncio.subprocess.PIPE, stderr=None)
        stdout, stderr = await proc.communicate()
        return {'returncode': proc.returncode, 'stdout': stdout}
    else:
        proc = await asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
        log.trace(f'cmd: [{cmdstring}]')
        return True


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
