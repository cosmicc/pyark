import subprocess
from functools import partial
from re import compile as rcompile
from re import sub

import asyncio
import globvars
import psutil
from loguru import logger as log
from modules.asyncdb import DB as db
from modules.redis import instancevar
from modules.timehelper import Now, elapsedSeconds, truncate_float
from typing import Union


def removerichtext(text: str) -> str:
    return sub("<.*?>", "", text)


def stripansi(stripstr: Union[str, list]) -> Union[str, list]:
    ansi_escape = rcompile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    if isinstance(stripstr, list):
        newlist = []
        for line in stripstr:
            if isinstance(line, bytes):
                line = line.decode()
            newlist.append(ansi_escape.sub("", line).strip())
        return newlist
    else:
        return ansi_escape.sub("", stripstr).strip()


def filterline(stripstr: str) -> str:
    return (
        stripansi(stripstr).replace("\n", "").replace("\r", "").replace('"', "").strip()
    )


def asynctimeit(func):
    async def wrapper(*args, **kwargs):
        asyncloop = asyncio.get_running_loop()
        astart_time = asyncloop.time()
        await func(*args, **kwargs)
        print(
            f"Execution times for [{func.__name__}]: Async: {asyncloop.time() - astart_time}"
        )

    return wrapper


async def asyncglobalbuffer(
    msg: str,
    inst: str = "ALERT",
    whosent: str = "ALERT",
    private: bool = False,
    broadcast: bool = False,
    db=db,
):
    await db.update(
        "INSERT INTO globalbuffer (server,name,message,timestamp,private,broadcast) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')"
        % (inst, whosent, msg, Now(), private, broadcast)
    )


@log.catch
async def gettotaldbconnections():
    """Return total number of database connections on postgres server

    Returns:
        INT: Description:  Total connections
    """
    data = await db.fetchone(f"SELECT count(*) FROM pg_stat_activity;")
    return data["count"]


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
    log.trace(f"cmd: {cmdstring}")


@log.catch
async def asyncserverscriptcmd(instance, command, wait=False, nice=5):
    """Send instance script command

    Arguments:
        instance {string} -- Instance name
        command {string} -- Script command to send

    Keyword Arguments:
        nice {number} -- Nice process level (default: {5})
    """
    cmdstring = f'/usr/bin/nice -n {nice} arkmanager rconcmd "ScriptCommand {command}" @{instance}'
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    if wait:
        proc = await asyncio.create_subprocess_shell(
            cmdstring, stdout=None, stderr=None
        )
        stdout, stderr = await proc.communicate()
        return stderr
    else:
        proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
        asyncio.create_task(proc)

    log.trace(f"cmd: {cmdstring}")


@log.catch
async def asyncserverchat(instance, message, nice=15):
    """Send instance global chat

    Arguments:
        instance {string} -- Instance name
        message {string} -- Chat message to send

    Keyword Arguments:
        nice {number} -- Nice process level (default: {5})
    """
    cmdstring = (
        f'/usr/bin/nice -n {nice} arkmanager rconcmd "ServerChat {message}" @{instance}'
    )
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.trace(f"cmd: {cmdstring}")


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
    log.trace(f"cmd: {cmdstring}")


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
    log.trace(f"""cmd: {repr(cmdstring)}""")


@log.catch
async def asyncservernotify(inst, message, nice=10):
    cmdstring = f"""/usr/bin/nice -n {nice} arkmanager notify "{message}" @{inst}"""
    proc = asyncio.create_subprocess_shell(cmdstring, stdout=None, stderr=None)
    asyncio.create_task(proc)
    log.trace(f"""cmd: {repr(cmdstring)}""")


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
    fullcmdlist = ["/usr/bin/nice", "-n", str(nice)] + cmdlist
    cmdstring = " ".join(fullcmdlist)
    if wait:
        proc = await asyncio.create_subprocess_shell(
            cmdstring, stdout=asyncio.subprocess.PIPE, stderr=None
        )
        stdout, stderr = await proc.communicate()
        return {"returncode": proc.returncode, "stdout": stdout}
    elif _wait:
        proc = await asyncio.create_subprocess_shell(
            cmdstring, stdout=None, stderr=None, shell=True
        )
        await proc.communicate()
    else:
        proc = asyncio.create_subprocess_shell(
            cmdstring, stdout=None, stderr=None, shell=True
        )
        asyncio.create_task(proc)


def serverneedsrestart():
    return globvars.server_needsrestart_file.is_file()


async def getserveruptime(elapsed=False):
    """Return server uptime in seconds or elapsed time string

    Args:
        elapsed (bool, [Optional]): Description: Return elapsed time string

    Returns:
        INT: Description:  Server uptime in seconds
        [STRING]: Description:  Server uptime in elapsed time string representation
    """
    if not isinstance(elapsed, bool):
        raise TypeError(f"Elapsed value must by type bool, not {type(elapsed)}")
    if elapsed:
        return elapsedSeconds(
            float(globvars.server_uptime_file.read_text().strip("\n").split(" ")[1])
        )
    else:
        return int(
            float(globvars.server_uptime_file.read_text().strip("\n").split(" ")[1])
        )


async def getidlepercent():
    """Return server idle time in percentage from uptime

    Returns:
        FLOAT: Description: Idle time percentage
    """
    uptimedata = globvars.server_uptime_file.read_text().strip("\n").split(" ")
    try:
        uptime = float(uptimedata[1])
        idletime = float(uptimedata[0])
    except (ValueError, IndexError):
        log.error("Invalid idle time percent retrieved from server")
    return truncate_float((idletime / uptime) * 100, 1)


async def getinstpid(inst: str) -> Union[str, None]:
    try:
        return globvars.instpidfiles[inst].read_text()
    except FileNotFoundError:
        await instancevar.set(inst, "isrunning", 0)
        await instancevar.set(inst, "islistening", 0)
        await instancevar.set(inst, "isonline", 0)
        return None


async def getopenfiles():
    """Return current number of open files on server

    Returns:
        TUPLE (INT, INT): Description: (openfiles, filelimit)
    """
    result = await asyncserverexec(["sysctl", "fs.file-nr"], nice=19, wait=True)
    newresult = result["stdout"].decode("utf-8").strip().split(" ")[2].split("\t")
    if len(newresult) < 2:
        log.error("Invalid open files retrieved from server")
    try:
        openfiles = int(newresult[0])
        filelimit = int(newresult[2])
    except ValueError:
        log.error("Invalid open files retrieved from server")
    return (openfiles, filelimit)


async def getcpuload():
    """Return tuple of cpu information

    Returns:
        TUPLE (INT, FLOAT, FLOAT, FLOAT, FLOAT): Description:
        (numcores, cpufreq, 1minload, 5minload, 15minload)
    """
    rawcpuload = psutil.getloadavg()
    numcores = psutil.cpu_count()
    try:
        numcores = int(numcores)
        cpufreq = psutil.cpu_freq()[0] / 1000
        load1 = (rawcpuload[0] / numcores) * 100
        load5 = (rawcpuload[1] / numcores) * 100
        load15 = (rawcpuload[2] / numcores) * 100
    except ValueError:
        log.error("Invalid cpu statistics retrieved from server")

    return (
        numcores,
        truncate_float(cpufreq, 1),
        truncate_float(load1, 1),
        truncate_float(load5, 1),
        truncate_float(load15, 1),
    )


async def getservermem():
    """Return tuple of memory statistics in kilobytes

    Returns:
        TUPLE (INT, INT, INT): Description: (memfree, memavailable, swapused)
    """
    process = await asyncserverexec(["free", "-m"], nice=19, wait=True)
    lines = process["stdout"].decode().split("\n")
    if len(lines) < 2:
        log.error("Invalid memory statistics retrieved from server")
        return (0, 0, 0)
    memvalues = lines[1].strip().split()
    swapvalues = lines[2].strip().split()
    if len(memvalues) < 6 or len(swapvalues) < 2:
        log.error("Invalid memory statistics retrieved from server")
        return (0, 0, 0)
    try:
        memfree = int(memvalues[3])
        memavailable = int(memvalues[6])
        swapused = int(swapvalues[2])
    except ValueError:
        log.error("Invalid memory statistics retrieved from server")
        return (0, 0, 0)
    else:
        return (int(memfree), int(memavailable), int(swapused))


async def _procstats(inst):
    log.trace(f"Running process instances stats for {inst}")
    instpid = await getinstpid(inst)
    if instpid == "CHANGEME":  # CHANGE ME
        arkprocess = psutil.Process(int(instpid))
        loop = asyncio.get_running_loop()
        arkcpu = await loop.run_in_executor(
            None, partial(arkprocess.cpu_percent, interval=5)
        )
        rawsts = await asyncserverexec(
            ["ps", "-p", f"{instpid}", "-o", "rss,vsz"], nice=19, wait=True
        )
        instrss, instvsz = rawsts["stdout"].decode("utf-8").split("\n")[1].split(" ")
        instrss = int(instrss) / 1000000 // 0.01 / 100
        instvsz = int(instvsz) / 1000000 // 0.01 / 100
        await db.update(
            f"UPDATE instances SET actmem = '{instrss}', totmem = '{instvsz}', serverpid = '{instpid}', arkcpu = '{arkcpu}' WHERE name = '{inst}'"
        )


async def processinststats(instances):
    for inst in instances:
        asyncio.create_task(_procstats(inst))
    return True


async def processserverstats(instances):
    log.trace("Running process server stats")
    serveruptime = await getserveruptime()
    servermem = await getservermem()
    serverload = await getcpuload()
    openfiles = await getopenfiles()
    for inst in instances:
        await db.update(
            f"UPDATE instances SET openfiles = '{openfiles[0]}', cpucores = '{serverload[0]}', cpufreq = '{serverload[1]}', cpuload1 = '{serverload[2]}', cpuload5 = '{serverload[3]}', cpuload15 = '{serverload[4]}', svrmemfree = '{servermem[0]}', svrmemavail = '{servermem[1]}', svrswapused = '{servermem[2]}', serveruptime = '{serveruptime}' WHERE name = '{inst}'"
        )


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
        fullcmdlist = ["/usr/bin/nice", "-n", str(nice)] + cmdlist
    if null:
        sproc = subprocess.run(
            fullcmdlist,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        return sproc.returncode
    else:
        sproc = subprocess.run(
            fullcmdlist, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False
        )
        return sproc
