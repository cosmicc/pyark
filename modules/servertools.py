import asyncio
import subprocess
from functools import partial
from os.path import isfile
from re import compile as rcompile
from re import sub
import psutil
from loguru import logger as log

import globvars
from modules.asyncdb import DB as db
from modules.timehelper import Now, elapsedTime
from modules.redis import instancevar


def stripansi(stripstr):
    ansi_escape = rcompile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return(ansi_escape.sub('', stripstr).strip())


def filterline(stripstr):
    return(stripansi(stripstr).replace('\n', '').replace('\r', '').replace('"', '').strip())


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
async def asyncserverrconcmd(instance, command, nice=5):
    """Send instance rcon command

    Arguments:
        instance {string} -- Instance name
        command {string} -- Rcon command to send

    Keyword Arguments:
        nice {number} -- Nice process level (default: {5})
    """
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "{command}" @{instance}'
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f'cmd: {cmdstring}')


@log.catch
async def asyncserverscriptcmd(instance, command, nice=5):
    """Send instance script command

    Arguments:
        instance {string} -- Instance name
        command {string} -- Script command to send

    Keyword Arguments:
        nice {number} -- Nice process level (default: {5})
    """
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "ScriptCommand {command}" @{instance}'
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f'cmd: {cmdstring}')


@log.catch
async def asyncserverchat(instance, message, nice=15):
    """Send instance global chat

    Arguments:
        instance {string} -- Instance name
        message {string} -- Chat message to send

    Keyword Arguments:
        nice {number} -- Nice process level (default: {5})
    """
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "ServerChat {message}" @{instance}'
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f'cmd: {cmdstring}')


@log.catch
async def asyncserverchatto(instance, steamid, message, nice=15):
    """Send instance rcon command

    Arguments:
        instance {string} -- Instance name
        steamid {string} -- SteamID of the player to send message to
        message {string} -- Privatr message to send to player

    Keyword Arguments:
        nice {number} -- Nice process level (default: {5})
    """
    cmdstring = f"""/usr/bin/nice -n {nice} arkmanager rconcmd 'ServerChatTo "{steamid}" {message}' @{instance}"""
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f'cmd: {cmdstring}')


@log.catch
async def asyncserverbcast(instance, broadcast, nice=10):
    """Send instance broadcast

    Arguments:
        instance {string} -- Instance name
        broadcast {string} -- Broadcast to send

    Keyword Arguments:
        nice {number} -- Nice process level (default: {5})
    """
    cmdstring = f"""/usr/bin/nice -n {nice} arkmanager rconcmd 'Broadcast {broadcast}' @{instance}"""
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f"""cmd: {repr(cmdstring)}""")


@log.catch
async def asyncservernotify(inst, message, nice=10):
    cmdstring = f"""/usr/bin/nice -n {nice} arkmanager notify "{message}" @{inst}"""
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.debug(f"""cmd: {repr(cmdstring)}""")


@log.catch
async def asyncserverexec(cmdlist, nice=19, wait=False, _wait=False):
    """Server execute command

    Arguments:
        cmdlist {list} -- Command split into list

    Keyword Arguments:
        nice {number} -- Process nice level (default: {19})
        wait {bool} -- Wait and return response (default: {False})
        _wait {bool} -- Wait until ended (default: {False})
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
    return sub('<.*?>', '', text)


@log.catch
def serverneedsrestart():
    if isfile('/run/reboot-required'):
        return True
    else:
        return False


def issharedmounted():
    return globvars.sharepath.is_mount()


def float_trunc_1dec(num):
    try:
        tnum = num // 0.1 / 10
    except:
        return False
    else:
        return tnum


async def getinstpid(inst):
    try:
        return globvars.instpidfiles[inst].read_text()
    except FileNotFoundError:
        await instancevar.set(inst, 'isrunning', 0)
        await instancevar.set(inst, 'islistening', 0)
        await instancevar.set(inst, 'isonline', 0)
        return None


async def getopenfiles():
    result = await asyncserverexec(['sysctl', 'fs.file-nr'], nice=19, wait=True)
    newresult = result['stdout'].decode('utf-8').strip().split(' ')[2].split('\t')
    return (newresult[0], newresult[2])


async def getserveruptime():
    return elapsedTime(Now(), psutil.boot_time())


async def getcpuload():
    rawcpuload = psutil.getloadavg()
    numcores = psutil.cpu_count()
    cpufreq = psutil.cpu_freq()[0] / 1000
    load1 = (rawcpuload[0] / numcores) * 100
    load5 = (rawcpuload[1] / numcores) * 100
    load15 = (rawcpuload[2] / numcores) * 100
    return (numcores, float_trunc_1dec(cpufreq), float_trunc_1dec(load1), float_trunc_1dec(load5), float_trunc_1dec(load15))


async def getservermem():
    process = await asyncserverexec(['free', '-m'], nice=19, wait=True)
    lines = process['stdout'].decode().split('\n')
    memvalues = lines[1].strip().split()
    swapvalues = lines[2].strip().split()
    memfree = memvalues[3]
    memavailable = memvalues[6]
    swapused = swapvalues[2]
    return (memfree, memavailable, swapused)


async def _procstats(inst):
    log.trace(f'Running process instances stats for {inst}')
    instpid = await getinstpid(inst)
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
    for inst in instances:
        asyncio.create_task(_procstats(inst))
    return True


async def processserverstats(instances):
    log.trace('Running process server stats')
    serveruptime = await getserveruptime()
    servermem = await getservermem()
    serverload = await getcpuload()
    openfiles = await getopenfiles()
    for inst in instances:
        await db.update(f"UPDATE instances SET openfiles = '{openfiles[0]}', cpucores = '{serverload[0]}', cpufreq = '{serverload[1]}', cpuload1 = '{serverload[2]}', cpuload5 = '{serverload[3]}', cpuload15 = '{serverload[4]}', svrmemfree = '{servermem[0]}', svrmemavail = '{servermem[1]}', svrswapused = '{servermem[2]}', serveruptime = '{serveruptime}' WHERE name = '{inst}'")


"""
@log.catch
def setarknice(inst):
    instpid = await getinstpid(inst)
    if instpid is not None:
        proc = psutil.Process(getinstpid)
        if proc.nice() != -10:
            log.debug(f'Setting priority for ark server instance [{inst}]')
            proc.nice(-10)
"""


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
