import asyncio
from re import compile as rcompile
from sys import exit
import globvars
from loguru import logger as log
from modules.asyncdb import DB as db
from modules.dbhelper import dbquery, dbupdate
from modules.players import getplayer
from modules.servertools import asyncserverrconcmd, asyncserverscriptcmd, serverexec, asyncserverexec
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


async def processstatusline(inst, statuslines):
        players = None
        serverbuild = None
        activeplayers = None
        steamlink = None
        arkserverslink = None
        serverversion = None
        serverpid = 0
        isrunning = 0
        islistening = 0
        isonline = 0
        for line in statuslines:
            status_title = stripansi(line.split(':')[0]).strip()
            if (status_title == 'Server running'):
                if stripansi(line.split(':')[1]).strip() == 'Yes':
                    globvars.isrunning.add(inst)
                    isrunning = 1
                elif stripansi(line.split(':')[1]).strip() == 'No':
                    globvars.isrunning.discard(inst)
                    globvars.islistening.discard(inst)
                    globvars.isonline.discard(inst)
                    isrunning = 0
            if (status_title == 'Server PID'):
                serverpid = stripansi(line.split(':')[1]).strip()
            if (status_title == 'Server listening'):
                if (stripansi(line.split(':')[1]).strip() == 'Yes'):
                    globvars.islistening.add(inst)
                    islistening = 1
                elif (stripansi(line.split(':')[1]).strip() == 'No'):
                    globvars.islistening.discard(inst)
                    globvars.isonline.discard(inst)
                    islistening = 0
            if (status_title == 'Server online'):
                if (stripansi(line.split(':')[1]).strip() == 'Yes'):
                    globvars.isonline.add(inst)
                    isonline = 1
                elif (stripansi(line.split(':')[1]).strip() == 'No'):
                    globvars.isonline.discard(inst)
                    isonline = 0
            if (status_title == 'Players'):
                players = int(stripansi(line.split(':')[1]).strip().split('/')[0].strip())
            if (status_title == 'Active Players'):
                activeplayers = int(stripansi(line.split(':')[1]).strip())
            if (status_title == 'Server build ID'):
                serverbuild = stripansi(line.split(':')[1]).strip()
            if (status_title == 'Server version'):
                serverversion = stripansi(line.split(':')[1]).strip()
            if (status_title == 'ARKServers link'):
                arkserverslink = stripansi(line.split('  ')[1]).strip()
            if (status_title == 'Steam connect link'):
                steamlink = stripansi(line.split('  ')[1]).strip()
        if int(activeplayers) > 0:
            isrunning = 1
            isonline = 1
        log.trace(f'pid: {serverpid}, online: {isonline}, listening: {islistening}, running: {isrunning}, {inst}')
        await db.update(f"UPDATE instances SET serverpid = '{int(serverpid)}', isup = '{int(isonline)}', islistening = '{int(islistening)}', isrunning = '{int(isrunning)}', arkbuild = '{int(serverbuild)}', arkversion = '{serverversion}' WHERE name = '{inst}'")
        if players is not None and activeplayers is not None and steamlink is not None and arkserverslink is not None:
            await db.update(f"UPDATE instances SET steamlink = '{steamlink}', arkserverslink = '{arkserverslink}', connectingplayers = '{int(players)}', activeplayers = '{int(activeplayers)}' WHERE name = '{inst}'")
        return True


async def runstatus(inst):
        result = await asyncserverexec(['arkmanager', 'status', f'@{inst}'], wait=True)
        statuslines = result['stdout'].decode('utf-8').split('\n')
        await processstatusline(inst, statuslines)
        globvars.taskworkers.remove(f'{inst}-status')
        return True


async def asyncgetinststatus(instances):
    for inst in instances:
        if f'{inst}-status' not in globvars.taskworkers:
            globvars.taskworkers.add(f'{inst}-status')
            asyncio.create_task(runstatus(inst))
    return True


def getinststatus(inst):
    rawrun = serverexec(['arkmanager', 'status', f'@{inst}'], nice=15)
    rawrun2 = rawrun['stdout'].decode('utf-8').split('\n')
    serverrunning = 0
    serveronline = 0
    players = None
    serverlistening = 0
    serverbuild = None
    activeplayers = None
    steamlink = None
    arkserverslink = None
    serverversion = None
    serverpid = 0
    for ea in rawrun2:
        sttitle = stripansi(ea.split(':')[0]).strip()
        if (sttitle == 'Server running'):
            if (stripansi(ea.split(':')[1]).strip() == 'Yes'):
                serverrunning = 1
            elif (stripansi(ea.split(':')[1]).strip() == 'No'):
                serverrunning = 0
                serveronline = 0
                serverlistening = 0
        if (sttitle == 'Server PID'):
            serverpid = stripansi(ea.split(':')[1]).strip()
        if (sttitle == 'Server listening'):
            if (stripansi(ea.split(':')[1]).strip() == 'Yes'):
                serverlistening = 1
            elif (stripansi(ea.split(':')[1]).strip() == 'No'):
                serveronline = 0
        if (sttitle == 'Server online'):
            if (stripansi(ea.split(':')[1]).strip() == 'Yes'):
                serveronline = 1
            elif (stripansi(ea.split(':')[1]).strip() == 'No'):
                serveronline = 0
        if (sttitle == 'Players'):
            players = int(stripansi(ea.split(':')[1]).strip().split('/')[0].strip())
        if (sttitle == 'Active Players'):
            activeplayers = int(stripansi(ea.split(':')[1]).strip())
        if (sttitle == 'Server build ID'):
            serverbuild = stripansi(ea.split(':')[1]).strip()
        if (sttitle == 'Server version'):
            serverversion = stripansi(ea.split(':')[1]).strip()
        if (sttitle == 'ARKServers link'):
            arkserverslink = stripansi(ea.split('  ')[1]).strip()
        if (sttitle == 'Steam connect link'):
            steamlink = stripansi(ea.split('  ')[1]).strip()
    try:
        log.trace(f'pid: {serverpid}, online: {serveronline}, listening: {serverlistening}, running: {serverrunning}, {inst}')
        dbupdate("UPDATE instances SET serverpid = '%s', isonline = '%s', islistening = '%s', isrunning = '%s' WHERE name = '%s'" % (int(serverpid), int(serveronline), int(serverlistening), int(serverrunning), inst))
    except:
        log.exception('Error writing up stats to database')
    if players is not None and activeplayers is not None and serverbuild is not None and serverversion is not None and steamlink is not None and arkserverslink is not None:
            try:
                dbupdate("UPDATE instances SET arkbuild = '%s', arkversion = '%s', steamlink = '%s', arkserverslink = '%s', connectingplayers = '%s', activeplayers = '%s' WHERE name = '%s'" % (int(serverbuild), serverversion, steamlink, arkserverslink, int(players), int(activeplayers), inst))
            except:
                log.exception('Error writing extra stats to database')
    return serverrunning, serverlistening, serveronline


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



if __name__ == '__main__':
    exit()
