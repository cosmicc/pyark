import asyncio
from functools import partial

from loguru import logger as log

from modules.asyncdb import DB as db
from modules.dbhelper import dbquery, dbupdate
from modules.players import getplayer
from modules.servertools import asyncserverrconcmd, asyncserverscriptcmd, filterline
from modules.redis import instancestate, instancevar
from modules.subprotocol import SubProtocol
from modules.timehelper import Now


@log.catch
async def asyncgetinstancelist():
    namelist = []
    names = await db.fetchall("SELECT * FROM instances")
    for name in names:
        namelist.append(name['name'])
    return namelist


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
    log.trace('running statusline completion task')
    if int(await instancevar.get(inst, 'missedrunning')) >= 3:
        await instancevar.set(inst, 'isrunning', 0)
    else:
        await instancevar.set(inst, 'isrunning', 1)
    if int(await instancevar.get(inst, 'missedlistening')) >= 3:
        await instancevar.set(inst, 'islistening', 0)
    else:
        await instancevar.set(inst, 'islistening', 1)
    if int(await instancevar.get(inst, 'missedonline')) >= 3:
        await instancevar.set(inst, 'isonline', 0)
    else:
        await instancevar.set(inst, 'isonline', 1)

    if int(await instancevar.get(inst, 'playersactive')) > 0 or int(await instancevar.get(inst, 'playersconnected')) > 0:
        await instancevar.set(inst, 'isrunning', 1)
        await instancevar.set(inst, 'islistening', 1)
        await instancevar.set(inst, 'isonline', 1)
    await db.update(f"""UPDATE instances SET serverpid = '{await instancevar.get(inst, "arkpid")}', isup = '{await instancevar.get(inst, "isonline")}', islistening = '{await instancevar.get(inst, "islistening")}', isrunning = '{await instancevar.get(inst, "isrunning")}' WHERE name = '{inst}'""")
    await db.update(f"""UPDATE instances SET hostname = '{await instancevar.get(inst, "arkname")}', steamlink = '{await instancevar.get(inst, "steamlink")}', arkserverslink = '{await instancevar.get(inst, "arkserverlink")}', connectingplayers = '{await instancevar.get(inst, "playersconnected")}', activeplayers = '{await instancevar.get(inst, "playersactive")}', arkbuild = '{await instancevar.get(inst, "arkbuild")}', arkversion = '{await instancevar.get(inst, "arkversion")}' WHERE name = '{inst}'""")


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
                await instancevar.inc(inst, 'missedlistening')

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
                await instancevar.set(inst, 'arkbuild', int(status_value))

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
        asyncio.create_task(statusexecute(inst))


async def asyncisinstanceenabled(inst):
    sen = await db.fetchone(f"SELECT enabled FROM instances WHERE name = '{inst}'")
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


def isinstancerunning(inst):
    dbdata = dbquery("SELECT isrunning FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if dbdata[0] == 1:
        return True
    else:
        return False


def isinstanceup(inst):
    dbdata = dbquery("SELECT isup FROM instances WHERE name = '%s'" % (inst,), fetch='one')
    if dbdata[0] == 1:
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


def homeablelist():
    dbdata = dbquery('SELECT name FROM instances WHERE homeable = true', fmt='list', single=True)
    return dbdata


async def asyncgetlastwipe(inst):
    insts = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    return int(insts['lastdinowipe'])


async def asyncgetlastvote(inst):
    insts = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    return int(insts['lastvote'])


async def asyncgetlastrestart(inst):
    insts = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    return int(insts['lastrestart'])


def getlastwipe(inst):
    dbdata = dbquery("SELECT lastdinowipe FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='string', fetch='one')
    if dbdata:
        return int(dbdata)
    else:
        return None


def getlastrestart(inst):
    dbdata = dbquery("SELECT lastrestart FROM instances WHERE name = '%s'" % (inst.lower(),), fetch='one', single=True)
    if dbdata:
        return int(dbdata[0])
    else:
        return None


def getlastrestartreason(inst):
    dbdata = dbquery("SELECT restartreason FROM instances WHERE name = '%s'" % (inst.lower(),), fetch='one', single=True)
    if dbdata:
        return dbdata[0]
    else:
        return None


def writechat(inst, whos, msg, tstamp):
    isindb = False
    if whos != 'ALERT' or whos != '*Admin':
        isindb = getplayer(whos)
    if whos == "ALERT" or isindb or whos == '*Admin':
        dbupdate("INSERT INTO chatbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
                 (inst, whos, msg, tstamp))


async def asyncwriteglobal(inst, whos, msg, db):
    if inst.lower() == 'all' or inst.lower() == 'alert':
        for instance in instancelist():
            await db.update(f"INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('{instance.lower()}', '{whos}', '{msg}', '{Now()}')")
    else:
        await db.update(f"INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('{instance.lower()}', '{whos}', '{msg}', '{Now()}')")


def writeglobal(inst, whos, msg):
    if inst.lower() == 'all' or inst.lower() == 'alert':
        for instance in instancelist():
            dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" %
                     (instance.lower(), whos, msg, Now()))
    else:
        dbupdate("INSERT INTO globalbuffer (server,name,message,timestamp) VALUES ('%s', '%s', '%s', '%s')" % (instance.lower(), whos, msg, Now()))


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
