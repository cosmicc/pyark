import asyncio
from functools import partial
from re import compile as rcompile

from loguru import logger as log
import globvars
from modules.asyncdb import DB as db
from modules.dbhelper import dbquery, dbupdate
from modules.subprotocol import SubProtocol
from modules.players import getplayer
from modules.servertools import asyncserverrconcmd, asyncserverscriptcmd
from modules.timehelper import Now


def stripansi(stripstr):
    ansi_escape = rcompile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return(ansi_escape.sub('', stripstr))


@log.catch
async def asyncgetinstancelist():
    namelist = []
    names = await db.fetchall("SELECT * FROM instances")
    for name in names:
        namelist.append(name['name'])
    return namelist


@log.catch
async def asyncwipeit(inst, dinos=True, eggs=False, mating=False, dams=False, bees=True):
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


async def asyncfinishstatus(inst):
    log.trace('running statusline completion task')
    if globvars.status_counts[inst]['running'] >= 3:
        isrunning = 0
        globvars.isrunning.discard(inst)
    else:
        isrunning = 1
        globvars.isrunning.add(inst)
    if globvars.status_counts[inst]['listening'] >= 3:
        globvars.islistening.discard(inst)
        islistening = 0
    else:
        islistening = 1
        globvars.islistening.add(inst)
    if globvars.status_counts[inst]['online'] >= 3:
        globvars.isonline.discard(inst)
        isonline = 0
    else:
        globvars.isonline.add(inst)
        isonline = 1
    if globvars.instplayers[inst]['active'] is not None:
        if int(globvars.instplayers[inst]['active']) > 0:
            globvars.isrunning.add(inst)
            globvars.islistening.add(inst)
            globvars.isonline.add(inst)
            isrunning = 1
            islistening = 1
            isonline = 1
        log.trace(f'pid: {globvars.instpids[inst]}, online: {isonline}, listening: {islistening}, running: {isrunning}, {inst}')
        await db.update(f"UPDATE instances SET serverpid = '{globvars.instpids[inst]}', isup = '{isonline}', islistening = '{islistening}', isrunning = '{isrunning}', arkbuild = '{globvars.instarkbuild[inst]}', arkversion = '{globvars.instarkversion[inst]}' WHERE name = '{inst}'")
        if globvars.instplayers[inst]['connecting'] is not None and globvars.instplayers[inst]['active'] is not None and globvars.instlinks[inst]['steam'] is not None and globvars.instlinks[inst]['arkservers'] is not None:
            await db.update(f"""UPDATE instances SET steamlink = '{globvars.instlinks[inst]["steam"]}', arkserverslink = '{globvars.instlinks[inst]["arkservers"]}', connectingplayers = '{globvars.instplayers[inst]['connecting']}', activeplayers = '{globvars.instplayers[inst]['active']}' WHERE name = '{inst}'""")
        return True


async def asyncprocessstatusline(inst, eline):
        line = eline.decode()
        print(repr(stripansi(line)))
        status_title = stripansi(line.split(':')[0]).strip()
        if not status_title.startswith('Running command'):
            status_value = stripansi(line.split(':')[1]).strip()
            if status_title == 'Server running':
                if status_value == 'Yes':
                    globvars.status_counts[inst]['running'] = 0
                elif status_value == 'No':
                    globvars.status_counts[inst]['running'] = globvars.status_counts[inst]['running'] + 1

            elif status_title == 'Server listening':
                if status_value == 'Yes':
                    globvars.status_counts[inst]['listening'] = 0
                elif status_value == 'No':
                    globvars.status_counts[inst]['listening'] = globvars.status_counts[inst]['listening'] + 1

            elif status_title == 'Server online':
                if status_value == 'Yes':
                    globvars.status_counts[inst]['online'] = 0
                elif status_value == 'No':
                    globvars.status_counts[inst]['online'] = globvars.status_counts[inst]['online'] + 1

            elif status_title == 'Server PID':
                globvars.instpids[inst] = int(status_value)

            elif (status_title == 'Players'):
                players = int(status_value.split('/')[0].strip())
                globvars.instplayers[inst]['connecting'] = int(players)

            elif (status_title == 'Active Players'):
                globvars.instplayers[inst]['active'] = int(status_value)

            elif (status_title == 'Server build ID'):
                globvars.instarkbuild[inst] = int(status_value)

            elif (status_title == 'Server version'):
                globvars.instarkversion[inst] = status_value

            elif (status_title == 'ARKServers link'):
                arkserverslink = stripansi(line.split('  ')[1]).strip()
                globvars.instlinks[inst]['arkservers'] = arkserverslink

            elif (status_title == 'Steam connect link'):
                steamlink = stripansi(line.split('  ')[1]).strip()
                globvars.instlinks[inst]['steam'] = steamlink


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


async def asyncisinstanceup(inst):
    dbdata = await db.fetchone(f"SELECT * FROM instances WHERE name = '{inst}'")
    if dbdata['isup'] == 1:
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
