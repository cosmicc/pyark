from functools import partial

import asyncio
import redis as _Redis
from loguru import logger as log
from modules.asyncdb import DB as db
from modules.configreader import redis_host, redis_port
from modules.dbhelper import dbquery, dbupdate
from modules.players import getplayer
from modules.redis import instancestate, instancevar, globalvar
from modules.servertools import asyncserverrconcmd, asyncserverscriptcmd, filterline
from modules.subprotocol import SubProtocol
from modules.timehelper import Now


@log.catch
async def asyncgetinstancelist():
    """Return a tuple of all instance names

    Returns:
        TUPLE: Description: Tuple of instance names
    """
    return await globalvar.gettuple('allinstances')


@log.catch
async def asyncwipeit(inst, dinos=True, eggs=False, mating=False, dams=False, bees=True):
    await instancestate.set(inst, 'wiping')
    if mating:
        log.debug(f'Shutting down dino mating on {inst}...')
        await asyncserverscriptcmd(inst, 'MatingOff_DS')
        await asyncio.sleep(10)
        log.debug(f'Clearing all unclaimed dinos on [{inst.title()}]...')
        await asyncserverscriptcmd(inst, 'DestroyUnclaimed_DS')
        await asyncio.sleep(10)
    if eggs:
        log.debug(f'Clearing all wild wyvern eggs on [{inst.title()}]...')
        await asyncserverrconcmd(inst, 'destroyall DroppedItemGeneric_FertilizedEgg_NoPhysicsWyvern_C')
        await asyncio.sleep(10)
        log.debug(f'Clearing all wild Deinonychus eggs on [{inst.title()}]...')
        await asyncserverrconcmd(inst, 'destroyall DroppedItemGeneric_FertilizedEgg_NoPhysicsDeinonychus_C')
        await asyncio.sleep(10)
        log.debug(f'Clearing all wild drake eggs on [{inst.title()}]...')
        await asyncserverrconcmd(inst, 'destroyall DroppedItemGeneric_FertilizedEgg_RockDrake_NoPhysics_C')
        await asyncio.sleep(10)
    if bees:
        log.debug(f'Clearing all beehives on [{inst.title()}]...')
        await asyncserverrconcmd(inst, 'destroyall BeeHive_C')
        await asyncio.sleep(3)
    if dams:
        log.debug(f'Clearing all beaver dams on [{inst.title()}]...')
        await asyncserverrconcmd(inst, 'destroyall BeaverDam_C')
        await asyncio.sleep(10)
    if dinos:
        log.debug(f'Clearing all wild dinos on [{inst.title()}]...')
        await db.update(f"UPDATE instances SET lastdinowipe = '{int(Now())}' WHERE name = '{inst}'")
        await asyncserverrconcmd(inst, 'DestroyWildDinos')
        await asyncio.sleep(5)
        log.log('WIPE', f'All wild dinos have been wiped from [{inst.title()}]')
    await instancestate.unset(inst, 'wiping')


@log.catch
async def asyncfinishstatus(inst):
    await instancestate.unset(inst, 'statuscheck')
    log.trace('running statusline completion task')
    if await instancevar.getint(inst, 'missedrunning') >= 3:
        await instancevar.mset(inst, {'isrunning': 0, 'playersactive': 0, 'playersconnected': 0, 'isonline': 0, 'islistening': 0})
    else:
        await instancevar.set(inst, 'isrunning', 1)
    if await instancevar.getint(inst, 'missedlistening') >= 3:
        await instancevar.set(inst, 'islistening', 0)
    else:
        await instancevar.set(inst, 'islistening', 1)
    if await instancevar.getint(inst, 'missedonline') >= 3:
        await instancevar.set(inst, 'isonline', 0)
    else:
        await instancevar.set(inst, 'isonline', 1)

    if await instancevar.getint(inst, 'playersactive') > 0 or await instancevar.getint(inst, 'playersconnected') > 0:
        await instancevar.mset(inst, {'isrunning': 1, 'islistening': 1, 'isonline': 1})
    await db.update(f"""UPDATE instances SET serverpid = '{await instancevar.getint(inst, "arkpid")}', isup = '{await instancevar.getint(inst, "isonline")}', islistening = '{await instancevar.getint(inst, "islistening")}', isrunning = '{await instancevar.getint(inst, "isrunning")}' WHERE name = '{inst}'""")
    await db.update(f"""UPDATE instances SET hostname = '{await instancevar.getstring(inst, "arkname")}', steamlink = '{await instancevar.getstring(inst, "steamlink")}', arkserverslink = '{await instancevar.getstring(inst, "arkserverlink")}', connectingplayers = '{await instancevar.getint(inst, "playersconnected")}', activeplayers = '{await instancevar.getint(inst, "playersactive")}', arkbuild = '{await instancevar.getint(inst, "arkbuild")}', arkversion = '{await instancevar.getstring(inst, "arkversion")}' WHERE name = '{inst}'""")


@log.catch
async def asyncprocessstatusline(inst, eline):
    line = filterline(eline.decode())
    status_title = line.split(':', 1)[0]
    if not status_title.startswith('Running command'):
        status_value = line.split(':', 1)[1].strip()
        if status_title == 'Server running':
            if status_value == 'Yes':
                await instancevar.set(inst, 'missedrunning', 0)
            elif status_value == 'No':
                await instancevar.inc(inst, 'missedrunning')

        elif status_title == 'Server listening':
            if status_value == 'Yes':
                await instancevar.set(inst, 'missedlistening', 0)
                await instancestate.unset(inst, 'restarting')
            elif status_value == 'No':
                await instancevar.inc(inst, 'missedlistening')

        elif status_title == 'Server online':
            if status_value == 'Yes':
                await instancevar.set(inst, 'missedonline', 0)
                await instancestate.unset(inst, 'restarting')
            elif status_value == 'No':
                await instancevar.inc(inst, 'missedonline')

        elif (status_title == 'Server version'):
            if status_value:
                await instancevar.set(inst, 'arkversion', status_value)

        elif status_title == 'Server PID':
            if status_value:
                await instancevar.set(inst, 'arkpid', int(status_value))

        elif (status_title == 'Server Name'):
            servername = status_value.split('Players', 1)[0]
            connecting = status_value.split(' / ')[0].split('Players:')[1]
            active = status_value.split('Active Players:')[1]
            if servername:
                await instancevar.set(inst, 'arkname', servername)
            if connecting:
                await instancevar.set(inst, 'playersconnected', int(connecting))
            if active:
                await instancevar.set(inst, 'playersactive', int(active))

        elif (status_title == 'Server build ID'):
            if status_value:
                try:
                    await instancevar.set(inst, 'arkbuild', int(status_value))
                except ValueError:
                    await instancevar.set(inst, 'arkbuild', int(status_value.split(' ', 1)[0]))
                    await instancevar.set(inst, 'arkversion', status_value.split(':')[1].strip())

        elif (status_title == 'ARKServers link'):
            if status_value:
                await instancevar.set(inst, 'arkserverlink', status_value)

        elif (status_title == 'Steam connect link'):
            if status_value:
                await instancevar.set(inst, 'steamlink', status_value)


async def statusexecute(inst):
    asyncloop = asyncio.get_running_loop()
    cmd_done = asyncio.Future(loop=asyncloop)
    factory = partial(SubProtocol, cmd_done, inst, parsetask=asyncprocessstatusline, finishtask=asyncfinishstatus)
    proc = asyncloop.subprocess_exec(factory, 'arkmanager', 'status', f'@{inst}', stdin=None, stderr=None)
    try:
        transport, protocol = await proc
        await cmd_done
    finally:
        transport.close()


async def statuscheck(instances):
    for inst in instances:
        if not await instancestate.check(inst, 'statuscheck'):
            await instancestate.set(inst, 'statuscheck')
            asyncio.create_task(statusexecute(inst))


async def asyncisinstanceenabled(instance):
    """Return if instance is enabled

    Args:
        instance (STRING): Description: Instance name to check

    Returns:
        BOOL:
    """
    if not isinstance(instance, str):
        raise TypeError(f'Instance name must be type str, not {type(instance)}')
    sen = await db.fetchone(f"SELECT enabled FROM instances WHERE name = '{instance}'")
    return sen[0]


def isinstanceenabled(inst):
    sen = dbquery("SELECT enabled FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    return sen[0]


def enableinstance(inst):
    dbupdate("UPDATE instances SET enabled = True WHERE name = '%s'" % (inst,))


def disableinstance(inst):
    dbupdate("UPDATE instances SET enabled = False WHERE name = '%s'" % (inst,))


def iscurrentconfig(inst):
    gcfg = dbquery("SELECT pendingcfg FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    dbdata = dbquery("SELECT cfgver FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if dbdata[0] == gcfg[0]:
        return True
    else:
        return False


def isinrestart(inst):
    dbdata = dbquery("SELECT needsrestart FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if dbdata[0] == 'True':
        return True
    else:
        return False


def isinstanceonline(instance):
    """Return if an instance is online or not

    Args:
        instance (STRING): Description: Instance name to check

    Returns:
        BOOL:
    """
    if not isinstance(instance, str):
        raise TypeError(f'Instance value must be type str, not {type(instance)}')
    redis = _Redis.Redis(host=redis_host, port=redis_port, db=0)
    online = redis.hget(instance, 'isonline').decode()
    if online == '1':
        return True
    else:
        return False


def getlastcrash(inst):
    dbdata = dbquery("SELECT lastcrash FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if dbdata[0] is not None:
        return dbdata[0]
    else:
        return 'Never'


def instancelist():
    dbdata = dbquery('SELECT name FROM instances ORDER BY name', fmt='list', single=True)
    return dbdata


async def asynchomeablelist():
    dbdata = db.fetchall('SELECT name FROM instances WHERE homeable = true')
    return dbdata


async def asyncgetlastwipe(instance):
    """Return instance last wild dino wipe time epoch

    Args:
        instance (STRING): Description: Instance name

    Returns:
        INT
    """
    if not isinstance(instance, str):
        raise TypeError(f'Instance value must be type str, not {type(instance)}')
    inst = await db.fetchone(f"SELECT * FROM instances WHERE name = '{instance}'")
    return int(inst['lastdinowipe'])


async def asyncgetlastvote(instance):
    """Return instance last wild wipe vote time epoch

    Args:
        instance (STRING): Description: Instance name

    Returns:
        INT
    """
    if not isinstance(instance, str):
        raise TypeError(f'Instance value must be type str, not {type(instance)}')
    insts = await db.fetchone(f"SELECT * FROM instances WHERE name = '{instance}'")
    return int(insts['lastvote'])


async def asyncgetlastrestart(instance):
    """Return insatnce last restart time epoch

    Args:
        instance (STRING): Description:

    Returns:
        INT
    """
    if not isinstance(instance, str):
        raise TypeError(f'Instance value must be type str, not {type(instance)}')
    insts = await db.fetchone(f"SELECT * FROM instances WHERE name = '{instance}'")
    return int(insts['lastrestart'])


async def asyncgetlastrestartreason(instance):
    """Return instance last restart reason

    Args:
        instance (STRING): Description: Instance name

    Returns:
        STRING
    """
    if not isinstance(instance, str):
        raise TypeError(f'Instance value must be type str, not {type(instance)}')
    dbdata = await db.fetchone(f"SELECT restartreason FROM instances WHERE name = '{instance.lower()}'")
    if dbdata:
        return dbdata['restartreason']
    else:
        return None


def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT' or whos != '*Admin':
        isindb = getplayer(whos)
    if whos == "ALERT" or isindb or whos == '*Admin':
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
                 (inst, whos, msg, tstamp))


async def asyncwriteglobal(instance, player, message, db=db):
    """Write to globalbuffer

    Args:
        instance (STRING): Description: Instance name
        player (STRING): Description: Player name
        message (STRING): Description: Meaage to send
    """
    if instance.lower() == 'all' or instance.lower() == 'alert':
        for inst in await asyncgetinstancelist():
            await db.update(f"INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('{inst.lower()}', '{player}', '{message}', '{Now()}')")
    else:
        await db.update(f"INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('{inst.lower()}', '{player}', '{message}', '{Now()}')")


async def asyncglobalbuffer(msg, inst='ALERT', whosent='ALERT', private=False, broadcast=False, db=db):
    await db.update("INSERT INTO globalbuffer (server,name,message,timestamp,private,broadcast) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" % (inst, whosent, msg, Now(), private, broadcast))


def serverchat(msg, inst='ALERT', whosent='ALERT', private=False, broadcast=False):
    dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp,private,broadcast) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" %
             (inst, whosent, msg, Now(), private, broadcast))


def restartinstance(server, cancel=False):
    if not cancel:
        dbupdate("UPDATE instances SET needsrestart = 'True', restartreason = 'admin restart' WHERE name = '%s'" % (server, ))
    else:
        dbupdate("UPDATE instances SET needsrestart = 'False' WHERE name = '%s'" % (server, ))


def getlog(inst, whichlog, lines=20):
    if whichlog == 'chat':
        clogfile = f'/home/ark/shared/logs/{inst}/chatlog/chat.log'
    elif whichlog == 'game':
        clogfile = f'/home/ark/shared/logs/{inst}/gamelog/game.log'
    num_lines = sum(1 for line in open(clogfile))
    cloglist = []
    with open(clogfile, 'r') as filehandle:
        cline = 1
        for line in filehandle:
            if cline > num_lines - lines:
                alist = {}
                alist['dtime'] = line.split(' [')[0]
                alist['pname'] = line[line.find("[") + 1:line.find("]")]
                alist['msg'] = line.split(']: ')[1].strip('\n')
                cloglist.append(alist)
            cline += 1
    return cloglist
