"""Summary

Attributes:
    redis (TYPE): Description
"""
import asyncio
import subprocess
from functools import partial
from os.path import isfile
from re import compile as rcompile
from re import sub
from modules.redis import Redis
import psutil
from loguru import logger as log

import globvars
from modules.asyncdb import DB as db
from modules.timehelper import Now, elapsedTime

redis = Redis.redis


class instvar:

    """Summary
    """

    def __init__(self):
        """Summary
        """
        pass

    async def set(self, inst, var, value):
        """Summary

        Args:
            inst (TYPE): Description
            var (TYPE): Description
            value (TYPE): Description
        """
        await redis.hset(f'{inst}', var, value)

    async def remove(self, inst, var):
        """Summary

        Args:
            inst (TYPE): Description
            var (TYPE): Description
        """
        await redis.hdel(f'{inst}', var)

    async def get(self, inst, var):
        """Summary

        Args:
            inst (TYPE): Description
            var (TYPE): Description

        Returns:
            TYPE: Description
        """
        return await redis.hget(f'{inst}', var)

    async def inc(self, inst, var):
        """Summary

        Args:
            inst (TYPE): Description
            var (TYPE): Description

        Returns:
            TYPE: Description
        """
        return await redis.hincrby(f'{inst}', var, 1)

    async def dec(self, inst, var):
        """Summary

        Args:
            inst (TYPE): Description
            var (TYPE): Description

        Returns:
            TYPE: Description
        """
        return await redis.hincrby(f'{inst}', var, -1)

    async def check(self, inst, var):
        """Summary

        Args:
            inst (TYPE): Description
            var (TYPE): Description

        Returns:
            TYPE: Description
        """
        return await redis.hexists(f'{inst}', var)


class inststate:

    """Summary
    """

    def __init__(self):
        """Summary
        """
        pass

    async def set(self, inst, state):
        """Summary

        Args:
            inst (TYPE): Description
            state (TYPE): Description
        """
        await redis.sadd(f'{inst}-states', state)

    async def unset(self, inst, state):
        """Summary

        Args:
            inst (TYPE): Description
            state (TYPE): Description
        """
        await redis.srem(f'{inst}-states', state)

    async def check(self, inst, state):
        """Summary

        Args:
            inst (TYPE): Description
            state (TYPE): Description

        Returns:
            TYPE: Description
        """
        return redis.sismember(f'{inst}-states', state)


def stripansi(stripstr):
    """[summary]
    Strip ANSI characters from a string
    [description]

    Arguments:
        stripstr (TYPE): Description
        stripstr {[string]} -- [string to reomove ANSI codes from]

    Returns:
        TYPE: Description
    """
    ansi_escape = rcompile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return(ansi_escape.sub('', stripstr).strip())


def filterline(stripstr):
    """Summary

    Args:
        stripstr (TYPE): Description

    Returns:
        TYPE: Description
    """
    return(stripansi(stripstr).replace('\n', '').replace('\r', '').replace('"', '').strip())


def asynctimeit(func):
    """Summary

    Args:
        func (TYPE): Description

    Returns:
        TYPE: Description
    """
    async def wrapper(*args, **kwargs):
        """Summary

        Args:
            *args: Description
            **kwargs: Description
        """
        asyncloop = asyncio.get_running_loop()
        astart_time = asyncloop.time()
        await func(*args, **kwargs)
        print(f'Execution times for [{func.__name__}]: Async: {asyncloop.time() - astart_time}')
    return wrapper


@log.catch
async def gettotaldbconnections():
    """Summary

    Returns:
        TYPE: Description
    """
    return await db.fetchone(f'SELECT count(*) FROM pg_stat_activity;')


@log.catch
async def asyncserverrconcmd(inst, command, nice=5):
    """Summary

    Args:
        inst (TYPE): Description
        command (TYPE): Description
        nice (int, optional): Description
    """
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "{command}" @{inst}'
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f'cmd: {cmdstring}')


@log.catch
async def asyncserverscriptcmd(inst, command, nice=5):
    """Summary

    Args:
        inst (TYPE): Description
        command (TYPE): Description
        nice (int, optional): Description
    """
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "ScriptCommand {command}" @{inst}'
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f'cmd: {cmdstring}')


@log.catch
async def asyncserverchat(inst, message, nice=15):
    """Summary

    Args:
        inst (TYPE): Description
        message (TYPE): Description
        nice (int, optional): Description
    """
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "ServerChat {message}" @{inst}'
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f'cmd: {cmdstring}')


@log.catch
async def asyncserverchatto(inst, steamid, message, nice=15):
    """Summary

    Args:
        inst (TYPE): Description
        steamid (TYPE): Description
        message (TYPE): Description
        nice (int, optional): Description
    """
    cmdstring = f"""/usr/bin/nice -n {nice} arkmanager rconcmd 'ServerChatTo "{steamid}" {message}' @{inst}"""
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f'cmd: {cmdstring}')


@log.catch
async def asyncserverbcast(inst, bcast, nice=10):
    """Summary

    Args:
        inst (TYPE): Description
        bcast (TYPE): Description
        nice (int, optional): Description
    """
    cmdstring = f"""/usr/bin/nice -n {nice} arkmanager rconcmd 'Broadcast {bcast}' @{inst}"""
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f"""cmd: {repr(cmdstring)}""")


@log.catch
async def asyncservernotify(inst, message, nice=10):
    """Summary

    Args:
        inst (TYPE): Description
        message (TYPE): Description
        nice (int, optional): Description
    """
    cmdstring = f"""/usr/bin/nice -n {nice} arkmanager notify "{message}" @{inst}"""
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f"""cmd: {repr(cmdstring)}""")


@log.catch
async def asyncserverexec(cmdlist, nice=19, wait=False, _wait=False):
    """Summary

    Args:
        cmdlist (TYPE): Description
        nice (int, optional): Description
        wait (bool, optional): Description
        _wait (bool, optional): Description

    Returns:
        TYPE: Description
    """
    fullcmdlist = ['/usr/bin/nice', '-n', str(nice)] + cmdlist
    cmdstring = ' '.join(fullcmdlist)
    if wait:
        proc = await asyncio.create_subprocess_shell(cmdstring, stdout=asyncio.subprocess.PIPE, stderr=None)
        stdout, stderr = await proc.communicate()
        return {'returncode': proc.returncode, 'stdout': stdout}
    elif _wait:
        proc = await asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
        await proc.communicate()
    else:
        await asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)


def removerichtext(text):
    """Summary

    Args:
        text (TYPE): Description

    Returns:
        TYPE: Description
    """
    return sub('<.*?>', '', text)


@log.catch
def serverneedsrestart():
    """Summary

    Returns:
        TYPE: Description
    """
    if isfile('/run/reboot-required'):
        return True
    else:
        return False


def issharedmounted():
    """Summary

    Returns:
        TYPE: Description
    """
    return globvars.sharepath.is_mount()


def float_trunc_1dec(num):
    """Summary

    Args:
        num (TYPE): Description

    Returns:
        TYPE: Description
    """
    try:
        tnum = num // 0.1 / 10
    except:
        return False
    else:
        return tnum


def getinstpid(inst):
    """Summary

    Args:
        inst (TYPE): Description

    Returns:
        TYPE: Description
    """
    try:
        return globvars.instpidfiles[inst].read_text()
    except FileNotFoundError:
        redis.hset(inst, 'isrunning', 0)
        redis.hset(inst, 'islistening', 0)
        redis.hset(inst, 'isonline', 0)
        return None


async def getopenfiles():
    """Summary

    Returns:
        TYPE: Description
    """
    result = await asyncserverexec(['sysctl', 'fs.file-nr'], nice=19, wait=True)
    newresult = result['stdout'].decode('utf-8').strip().split(' ')[2].split('\t')
    return (newresult[0], newresult[2])


async def getserveruptime():
    """Summary

    Returns:
        TYPE: Description
    """
    return elapsedTime(Now(), psutil.boot_time())


async def getcpuload():
    """Summary

    Returns:
        TYPE: Description
    """
    rawcpuload = psutil.getloadavg()
    numcores = psutil.cpu_count()
    cpufreq = psutil.cpu_freq()[0] / 1000
    load1 = (rawcpuload[0] / numcores) * 100
    load5 = (rawcpuload[1] / numcores) * 100
    load15 = (rawcpuload[2] / numcores) * 100
    return (numcores, float_trunc_1dec(cpufreq), float_trunc_1dec(load1), float_trunc_1dec(load5), float_trunc_1dec(load15))


async def getservermem():
    """Summary

    Returns:
        TYPE: Description
    """
    process = await asyncserverexec(['free', '-m'], nice=19, wait=True)
    lines = process['stdout'].decode().split('\n')
    memvalues = lines[1].strip().split()
    swapvalues = lines[2].strip().split()
    memfree = memvalues[3]
    memavailable = memvalues[6]
    swapused = swapvalues[2]
    return (memfree, memavailable, swapused)


async def _procstats(inst):
    """Summary

    Args:
        inst (TYPE): Description
    """
    log.trace(f'Running process instances stats for {inst}')
    instpid = getinstpid(inst)
    if instpid == "CHANGEME":  # CHANGE ME
        arkprocess = psutil.Process(int(instpid))
        loop = asyncio.get_running_loop()
        arkcpu = await loop.run_in_executor(None, partial(arkprocess.cpu_percent, interval=5))
        rawsts = await asyncserverexec(['ps', '-p', f'{instpid}', '-o', 'rss,vsz'], nice=19, wait=True)
        instrss, instvsz = rawsts['stdout'].decode('utf-8').split('\n')[1].split(' ')
        instrss = int(instrss) / 1000000 // 0.01 / 100
        instvsz = int(instvsz) / 1000000 // 0.01 / 100
        await db.update(f"UPDATE instances SET actmem = '{instrss}', totmem = '{instvsz}', serverpid = '{instpid}', arkcpu = '{arkcpu}' WHERE name = '{inst}'")


async def processinststats(instances):
    """Summary

    Args:
        instances (TYPE): Description

    Returns:
        TYPE: Description
    """
    for inst in instances:
        asyncio.create_task(_procstats(inst))
    return True


async def processserverstats(instances):
    """Summary

    Args:
        instances (TYPE): Description
    """
    log.trace('Running process server stats')
    serveruptime = await getserveruptime()
    servermem = await getservermem()
    serverload = await getcpuload()
    openfiles = await getopenfiles()
    for inst in instances:
        await db.update(f"UPDATE instances SET openfiles = '{openfiles[0]}', cpucores = '{serverload[0]}', cpufreq = '{serverload[1]}', cpuload1 = '{serverload[2]}', cpuload5 = '{serverload[3]}', cpuload15 = '{serverload[4]}', svrmemfree = '{servermem[0]}', svrmemavail = '{servermem[1]}', svrswapused = '{servermem[2]}', serveruptime = '{serveruptime}' WHERE name = '{inst}'")


@log.catch
def setarknice(inst):
    """Summary

    Args:
        inst (TYPE): Description
    """
    instpid = getinstpid(inst)
    if instpid is not None:
        proc = psutil.Process(getinstpid)
        if proc.nice() != -10:
            log.debug(f'Setting priority for ark server instance [{inst}]')
            proc.nice(-10)


@log.catch
def serverexec(cmdlist, nice=10, null=False):
    """
    [Summary]

    Args:
        cmdlist (TYPE): [Description]
        nice (int, [Optional]): [Description]
        null (bool, [Optional]): [Description]

    Returns:
        TYPE: [Description]

    Raises:
        TypeError: [Description]
    """
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
